"""
Módulo de validação e normalização dos dados extraídos.

Usa Pydantic v2 para garantir que os dados extraídos respeitem
um schema bem definido antes de serem serializados ou enviados
via API.

Também realiza:
- Deduplicação de cláusulas idênticas
- Normalização de valores monetários e datas
- Cálculo de scores de confiabilidade
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils import setup_logger

logger = setup_logger(__name__)


class IdentificacaoSchema(BaseModel):
    """Identificação básica do edital."""

    modalidade: Optional[str] = Field(None, description="Modalidade da licitação")
    numero_edital: Optional[str] = Field(None, description="Número do edital")
    numero_processo: Optional[str] = Field(None, description="Número do processo administrativo")
    objeto: Optional[str] = Field(None, description="Objeto da licitação")
    orgao: Optional[str] = Field(None, description="Órgão promotor")


class ClausulaSchema(BaseModel):
    """Cláusula extraída do edital."""

    category: str = Field(..., description="Categoria da cláusula")
    text: str = Field(..., description="Texto da cláusula")
    context: str = Field("", description="Contexto da cláusula (sentenças adjacentes)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadados estruturados")

    @field_validator("text", "context")
    @classmethod
    def strip_text(cls, v: str) -> str:
        """Remove espaços em branco nas pontas."""
        return v.strip() if v else ""


class EditalSchema(BaseModel):
    """Schema completo do edital validado."""

    identificacao: IdentificacaoSchema = Field(default_factory=IdentificacaoSchema)
    prazos: list[ClausulaSchema] = Field(default_factory=list)
    multas: list[ClausulaSchema] = Field(default_factory=list)
    exigencias_tecnicas: list[ClausulaSchema] = Field(default_factory=list)
    documentacoes: list[ClausulaSchema] = Field(default_factory=list)
    criterios_habilitacao: list[ClausulaSchema] = Field(default_factory=list)
    cronograma: list[ClausulaSchema] = Field(default_factory=list)
    valores: list[ClausulaSchema] = Field(default_factory=list)
    garantias: list[ClausulaSchema] = Field(default_factory=list)
    entidades_nomeadas: dict[str, list[str]] = Field(default_factory=dict)
    estatisticas: dict[str, Any] = Field(default_factory=dict)
    score_confiabilidade: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Score 0-1 indicando confiabilidade da extração",
    )


class DataValidator:
    """
    Valida e normaliza os dados extraídos pelo EditalExtractor.

    Realiza:
    - Validação de schema via Pydantic
    - Deduplicação por hash do texto
    - Cálculo de score de confiabilidade baseado em cobertura
    """

    def __init__(self, raw_data: dict[str, Any]):
        """
        Args:
            raw_data: Dicionário retornado por EditalData.to_dict().
        """
        self.raw_data = raw_data

    def validate(self) -> EditalSchema:
        """
        Executa o pipeline de validação completo.

        Returns:
            EditalSchema validado e enriquecido.
        """
        logger.info("Iniciando validação dos dados extraídos")

        # Deduplicação por categoria
        dedup_data = self._deduplicate(self.raw_data)

        # Cálculo de score
        dedup_data["score_confiabilidade"] = self._compute_confidence_score(dedup_data)

        try:
            schema = EditalSchema(**dedup_data)
            logger.info(
                f"Validação concluída. Score de confiabilidade: "
                f"{schema.score_confiabilidade:.2f}"
            )
            return schema
        except Exception as e:
            logger.exception(f"Erro durante validação: {e}")
            raise

    def _deduplicate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Remove cláusulas duplicadas dentro de cada categoria.

        A deduplicação considera o texto completo normalizado (lowercased,
        sem espaços extras) como chave.

        Args:
            data: Dicionário com listas de cláusulas.

        Returns:
            Dicionário com listas deduplicadas.
        """
        categorias = [
            "prazos", "multas", "exigencias_tecnicas", "documentacoes",
            "criterios_habilitacao", "cronograma", "valores", "garantias",
        ]

        result = dict(data)  # Cópia rasa

        for categoria in categorias:
            clauses = data.get(categoria, [])
            seen: set[str] = set()
            unique: list[dict[str, Any]] = []

            for clause in clauses:
                # Normaliza para comparação
                key = " ".join(clause.get("text", "").lower().split())
                if key and key not in seen:
                    seen.add(key)
                    unique.append(clause)

            removed = len(clauses) - len(unique)
            if removed > 0:
                logger.debug(f"Categoria '{categoria}': {removed} duplicadas removidas")

            result[categoria] = unique

        return result

    def _compute_confidence_score(self, data: dict[str, Any]) -> float:
        """
        Calcula um score de 0 a 1 baseado na cobertura da extração.

        Cada categoria contribui igualmente. Identificação é peso duplo.

        Args:
            data: Dados extraídos.

        Returns:
            Score de confiabilidade.
        """
        score = 0.0
        max_score = 0.0

        # Identificação tem peso duplo (mais crítica)
        identificacao = data.get("identificacao", {})
        ident_fields = ["modalidade", "numero_edital", "objeto"]
        for field_name in ident_fields:
            max_score += 2.0
            if identificacao.get(field_name):
                score += 2.0

        # Cada categoria de cláusula contribui se tiver ao menos 1 item
        categorias = [
            "prazos", "multas", "exigencias_tecnicas", "documentacoes",
            "criterios_habilitacao", "cronograma", "valores", "garantias",
        ]
        for categoria in categorias:
            max_score += 1.0
            if data.get(categoria):
                score += 1.0

        # Entidades nomeadas
        max_score += 1.0
        if data.get("entidades_nomeadas"):
            score += 1.0

        return round(score / max_score, 3) if max_score > 0 else 0.0


def validate_extracted_data(raw_data: dict[str, Any]) -> EditalSchema:
    """
    Função de conveniência para validar dados extraídos.

    Args:
        raw_data: Dicionário com dados brutos.

    Returns:
        EditalSchema validado.
    """
    validator = DataValidator(raw_data)
    return validator.validate()
