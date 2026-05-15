"""
Módulo de extração de informações de editais.

Combina:
- Regex específicas para o domínio de licitações públicas brasileiras
- NLP com spaCy (modelo pt_core_news_sm) para identificação de entidades
- Heurísticas baseadas em palavras-chave e estrutura textual

Categorias extraídas:
- Prazos (execução, vigência, recursos, etc.)
- Multas e penalidades
- Exigências técnicas (qualificação técnica)
- Documentações obrigatórias (habilitação)
- Critérios de habilitação (jurídica, fiscal, econômica)
- Cronogramas (datas-chave)
- Valores (estimado, máximo, lance)
- Garantias (contratual, proposta)
- Identificação do edital (modalidade, número, órgão)
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.utils import parse_brazilian_currency, parse_brazilian_date, setup_logger

logger = setup_logger(__name__)

# Carregamento lazy do spaCy: o modelo só é carregado quando necessário,
# evitando custo de import para usos que não precisem de NLP.
_nlp = None


def _get_nlp():
    """Carrega o modelo spaCy português sob demanda."""
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("pt_core_news_sm")
            logger.info("Modelo spaCy 'pt_core_news_sm' carregado")
        except OSError:
            logger.warning(
                "Modelo spaCy 'pt_core_news_sm' não instalado. "
                "Execute: python -m spacy download pt_core_news_sm"
            )
            _nlp = False  # Marca como indisponível para não tentar novamente
    return _nlp if _nlp else None


@dataclass
class ExtractedClause:
    """Representa uma cláusula extraída do edital."""

    category: str
    text: str
    context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EditalData:
    """Estrutura completa de dados extraídos de um edital."""

    identificacao: dict[str, Any] = field(default_factory=dict)
    prazos: list[ExtractedClause] = field(default_factory=list)
    multas: list[ExtractedClause] = field(default_factory=list)
    exigencias_tecnicas: list[ExtractedClause] = field(default_factory=list)
    documentacoes: list[ExtractedClause] = field(default_factory=list)
    criterios_habilitacao: list[ExtractedClause] = field(default_factory=list)
    cronograma: list[ExtractedClause] = field(default_factory=list)
    valores: list[ExtractedClause] = field(default_factory=list)
    garantias: list[ExtractedClause] = field(default_factory=list)
    entidades_nomeadas: dict[str, list[str]] = field(default_factory=dict)
    estatisticas: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário serializável em JSON."""
        return {
            "identificacao": self.identificacao,
            "prazos": [self._clause_to_dict(c) for c in self.prazos],
            "multas": [self._clause_to_dict(c) for c in self.multas],
            "exigencias_tecnicas": [self._clause_to_dict(c) for c in self.exigencias_tecnicas],
            "documentacoes": [self._clause_to_dict(c) for c in self.documentacoes],
            "criterios_habilitacao": [self._clause_to_dict(c) for c in self.criterios_habilitacao],
            "cronograma": [self._clause_to_dict(c) for c in self.cronograma],
            "valores": [self._clause_to_dict(c) for c in self.valores],
            "garantias": [self._clause_to_dict(c) for c in self.garantias],
            "entidades_nomeadas": self.entidades_nomeadas,
            "estatisticas": self.estatisticas,
        }

    @staticmethod
    def _clause_to_dict(clause: ExtractedClause) -> dict[str, Any]:
        return {
            "category": clause.category,
            "text": clause.text,
            "context": clause.context,
            "metadata": clause.metadata,
        }


class EditalExtractor:
    """
    Extrator principal de informações de editais de licitação de obras públicas.

    Funciona em duas fases:
    1. Aplicação de regex específicas para o domínio
    2. Pós-processamento com NLP (spaCy) para entidades nomeadas
    """

    # === Padrões Regex (compilados na inicialização para performance) ===

    # Modalidades comuns em licitações brasileiras (Lei 14.133/2021 e Lei 8.666/93)
    REGEX_MODALIDADE = re.compile(
        r"(preg[ãa]o\s+(?:eletr[ôo]nico|presencial)|concorr[êe]ncia|tomada\s+de\s+pre[çc]os|"
        r"convite|leil[ãa]o|concurso|di[áa]logo\s+competitivo|RDC)",
        re.IGNORECASE,
    )

    REGEX_NUMERO_EDITAL = re.compile(
        r"(?:edital|preg[ãa]o|concorr[êe]ncia|tomada\s+de\s+pre[çc]os)\s*"
        r"(?:eletr[ôo]nico\s+)?n[ºo°.]*\s*(\d{1,5}[/\-]\d{2,4})",
        re.IGNORECASE,
    )

    REGEX_PROCESSO = re.compile(
        r"processo\s+(?:administrativo\s+)?n[ºo°.]*\s*(\d+[/\-.]?\d*[/\-]\d{2,4})",
        re.IGNORECASE,
    )

    # Valores monetários em formato brasileiro
    REGEX_VALOR_BR = re.compile(
        r"R\$\s*([\d.]+(?:,\d{2})?)",
        re.IGNORECASE,
    )

    # Datas em formato brasileiro
    REGEX_DATA = re.compile(
        r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\b"
    )

    REGEX_DATA_EXTENSO = re.compile(
        r"\b(\d{1,2}\s+de\s+(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|"
        r"julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4})\b",
        re.IGNORECASE,
    )

    # Prazos em dias/meses/anos
    REGEX_PRAZO = re.compile(
        r"(?:prazo|vig[êe]ncia|dura[çc][ãa]o|execu[çc][ãa]o)[^.]*?"
        r"(\d{1,4})\s*\(?[^)]*?\)?\s*(dias?|meses|m[êe]s|anos?)",
        re.IGNORECASE,
    )

    # Multas e penalidades (% ou valores fixos)
    REGEX_MULTA = re.compile(
        r"multa[^.]*?(?:de\s+)?(\d+(?:[.,]\d+)?)\s*%",
        re.IGNORECASE,
    )

    # Palavras-chave para detecção de seções/cláusulas
    KEYWORDS = {
        "prazos": [
            "prazo de execução", "prazo de vigência", "prazo de entrega",
            "prazo contratual", "prazo de recurso", "prazo de impugnação",
            "vigência do contrato", "duração do contrato",
        ],
        "multas": [
            "multa", "penalidade", "sanção", "advertência", "suspensão",
            "declaração de inidoneidade", "impedimento de licitar",
        ],
        "exigencias_tecnicas": [
            "qualificação técnica", "atestado de capacidade técnica",
            "acervo técnico", "CAT", "responsável técnico", "ART", "RRT",
            "experiência técnica", "comprovação técnica", "registro no CREA",
            "registro no CAU",
        ],
        "documentacoes": [
            "habilitação jurídica", "contrato social", "ato constitutivo",
            "cartão CNPJ", "alvará", "certidão negativa", "regularidade fiscal",
            "FGTS", "INSS", "trabalhista", "documentação obrigatória",
            "documentos para habilitação",
        ],
        "criterios_habilitacao": [
            "habilitação jurídica", "regularidade fiscal", "qualificação econômico-financeira",
            "qualificação técnica", "habilitação trabalhista", "cumprimento ao art. 7",
            "menor de 18 anos", "balanço patrimonial", "índices contábeis",
        ],
        "cronograma": [
            "cronograma", "data de abertura", "sessão pública", "entrega das propostas",
            "início das obras", "data de assinatura", "ordem de serviço",
        ],
        "valores": [
            "valor estimado", "valor máximo", "valor global", "valor de referência",
            "preço máximo", "orçamento estimado", "valor total", "valor unitário",
            "lance mínimo",
        ],
        "garantias": [
            "garantia de proposta", "garantia contratual", "caução", "seguro-garantia",
            "fiança bancária", "garantia de execução", "garantia de manutenção",
        ],
    }

    def __init__(self, text: str):
        """
        Inicializa o extrator com o texto do edital.

        Args:
            text: Texto bruto/limpo extraído do edital.
        """
        self.text = text
        self.data = EditalData()
        logger.info(f"Extractor inicializado com {len(text)} caracteres")

    def extract_all(self) -> EditalData:
        """
        Executa todas as extrações e retorna o objeto consolidado.

        Returns:
            EditalData com todas as categorias preenchidas.
        """
        logger.info("Iniciando extração completa do edital")

        self._extract_identification()
        self._extract_by_category("prazos", self.data.prazos)
        self._extract_by_category("multas", self.data.multas)
        self._extract_by_category("exigencias_tecnicas", self.data.exigencias_tecnicas)
        self._extract_by_category("documentacoes", self.data.documentacoes)
        self._extract_by_category("criterios_habilitacao", self.data.criterios_habilitacao)
        self._extract_by_category("cronograma", self.data.cronograma)
        self._extract_by_category("valores", self.data.valores)
        self._extract_by_category("garantias", self.data.garantias)
        self._extract_named_entities()
        self._compute_statistics()

        logger.info("Extração concluída com sucesso")
        return self.data

    def _extract_identification(self) -> None:
        """Extrai identificação do edital (modalidade, número, processo)."""
        identification = {}

        modalidade_match = self.REGEX_MODALIDADE.search(self.text)
        if modalidade_match:
            identification["modalidade"] = modalidade_match.group(1).strip()

        numero_match = self.REGEX_NUMERO_EDITAL.search(self.text)
        if numero_match:
            identification["numero_edital"] = numero_match.group(1).strip()

        processo_match = self.REGEX_PROCESSO.search(self.text)
        if processo_match:
            identification["numero_processo"] = processo_match.group(1).strip()

        # Tenta detectar o objeto da licitação (primeira ocorrência após "objeto")
        objeto_match = re.search(
            r"objeto[:\s]+([^.\n]{20,300})",
            self.text,
            re.IGNORECASE,
        )
        if objeto_match:
            identification["objeto"] = objeto_match.group(1).strip()

        self.data.identificacao = identification
        logger.debug(f"Identificação extraída: {identification}")

    def _extract_by_category(self, category: str, target_list: list[ExtractedClause]) -> None:
        """
        Extrai cláusulas de uma categoria com base em palavras-chave.

        Para cada palavra-chave encontrada, captura um trecho contextual
        ao redor (sentença que a contém + adjacente).

        Args:
            category: Nome da categoria (chave em KEYWORDS).
            target_list: Lista para append dos resultados.
        """
        keywords = self.KEYWORDS.get(category, [])
        sentences = self._split_sentences(self.text)
        found_indexes = set()

        for idx, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            for kw in keywords:
                if kw.lower() in sentence_lower and idx not in found_indexes:
                    # Pega um contexto: a frase anterior e a posterior
                    start = max(0, idx - 1)
                    end = min(len(sentences), idx + 2)
                    context = " ".join(sentences[start:end])

                    clause = ExtractedClause(
                        category=category,
                        text=sentence.strip(),
                        context=context.strip(),
                        metadata={"keyword": kw, "sentence_index": idx},
                    )

                    # Extrai metadados específicos por categoria
                    self._enrich_clause(clause, category)

                    target_list.append(clause)
                    found_indexes.add(idx)
                    break  # Evita duplicar a mesma sentença com outra keyword

        logger.debug(f"Categoria '{category}': {len(target_list)} cláusulas extraídas")

    def _enrich_clause(self, clause: ExtractedClause, category: str) -> None:
        """
        Adiciona metadados estruturados à cláusula conforme a categoria.

        Args:
            clause: Cláusula a ser enriquecida.
            category: Nome da categoria.
        """
        text = clause.text

        if category == "prazos":
            match = self.REGEX_PRAZO.search(text)
            if match:
                clause.metadata["quantidade"] = int(match.group(1))
                clause.metadata["unidade"] = match.group(2).lower().rstrip("s")

        elif category == "multas":
            match = self.REGEX_MULTA.search(text)
            if match:
                clause.metadata["percentual"] = float(match.group(1).replace(",", "."))

        elif category in ("valores", "garantias"):
            valores = self.REGEX_VALOR_BR.findall(text)
            if valores:
                parsed = [parse_brazilian_currency(f"R$ {v}") for v in valores]
                clause.metadata["valores_brutos"] = valores
                clause.metadata["valores_numericos"] = [v for v in parsed if v is not None]

        elif category == "cronograma":
            datas_num = self.REGEX_DATA.findall(text)
            datas_ext = self.REGEX_DATA_EXTENSO.findall(text)
            todas_datas = datas_num + datas_ext
            if todas_datas:
                parsed = [parse_brazilian_date(d) for d in todas_datas]
                clause.metadata["datas_brutas"] = todas_datas
                clause.metadata["datas_iso"] = [d for d in parsed if d is not None]

    def _extract_named_entities(self) -> None:
        """
        Extrai entidades nomeadas usando spaCy (se disponível).

        Categorias: ORG (organizações), PER (pessoas), LOC (locais),
        MISC (diversos).
        """
        nlp = _get_nlp()
        if nlp is None:
            logger.info("spaCy indisponível - pulando extração de entidades nomeadas")
            self.data.entidades_nomeadas = {}
            return

        # Limita o tamanho do texto processado pelo spaCy para evitar OOM
        # (spaCy tem limite padrão de 1.000.000 caracteres)
        text_to_process = self.text[:900_000]

        try:
            doc = nlp(text_to_process)
            entities: dict[str, set[str]] = {}

            for ent in doc.ents:
                label = ent.label_
                value = ent.text.strip()
                # Filtra entidades muito curtas ou ruidosas
                if len(value) < 3 or value.isnumeric():
                    continue
                entities.setdefault(label, set()).add(value)

            # Converte sets para listas ordenadas para serialização JSON
            self.data.entidades_nomeadas = {
                label: sorted(values)[:50]  # Limita a 50 por categoria
                for label, values in entities.items()
            }
            logger.info(
                f"Entidades nomeadas extraídas: "
                f"{sum(len(v) for v in self.data.entidades_nomeadas.values())} totais"
            )
        except Exception as e:
            logger.warning(f"Falha ao extrair entidades com spaCy: {e}")
            self.data.entidades_nomeadas = {}

    def _compute_statistics(self) -> None:
        """Calcula estatísticas gerais do edital."""
        self.data.estatisticas = {
            "total_caracteres": len(self.text),
            "total_palavras": len(self.text.split()),
            "total_clausulas_prazos": len(self.data.prazos),
            "total_clausulas_multas": len(self.data.multas),
            "total_clausulas_exigencias_tecnicas": len(self.data.exigencias_tecnicas),
            "total_clausulas_documentacoes": len(self.data.documentacoes),
            "total_clausulas_habilitacao": len(self.data.criterios_habilitacao),
            "total_clausulas_cronograma": len(self.data.cronograma),
            "total_clausulas_valores": len(self.data.valores),
            "total_clausulas_garantias": len(self.data.garantias),
        }

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """
        Divisão simples de sentenças por pontuação.

        Não usa spaCy aqui para evitar dependência obrigatória,
        já que regex resolve bem para o caso de uso de editais.

        Args:
            text: Texto completo.

        Returns:
            Lista de sentenças.
        """
        # Divide por . ! ? seguidos de espaço/quebra, mas preserva trechos longos
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ÿ0-9])", text)
        return [s.strip() for s in sentences if s.strip()]


def extract_edital_data(text: str) -> EditalData:
    """
    Função de conveniência para extrair todos os dados de um edital.

    Args:
        text: Texto do edital já limpo.

    Returns:
        EditalData populado.
    """
    extractor = EditalExtractor(text)
    return extractor.extract_all()
