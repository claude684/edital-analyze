"""
Módulo de geração de relatórios.

Gera relatórios em múltiplos formatos a partir do EditalSchema validado:
- JSON estruturado (formato canônico)
- CSV (uma linha por cláusula)
- Markdown (relatório legível por humanos)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from app.utils import OUTPUTS_DIR, setup_logger, slugify
from app.validator import EditalSchema

logger = setup_logger(__name__)


class ReportGenerator:
    """
    Gerador de relatórios a partir de um EditalSchema validado.
    """

    def __init__(self, schema: EditalSchema, base_filename: Optional[str] = None):
        """
        Args:
            schema: Schema validado do edital.
            base_filename: Nome base dos arquivos gerados (sem extensão).
                          Se None, gera baseado no número do edital ou timestamp.
        """
        self.schema = schema
        self.base_filename = base_filename or self._auto_filename()
        self.output_dir = OUTPUTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _auto_filename(self) -> str:
        """Gera nome de arquivo baseado nos dados do edital."""
        numero = self.schema.identificacao.numero_edital
        if numero:
            return f"edital-{slugify(numero)}"
        return f"edital-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def generate_json(self) -> Path:
        """
        Gera relatório em JSON estruturado.

        Returns:
            Caminho do arquivo gerado.
        """
        output_path = self.output_dir / f"{self.base_filename}.json"
        data = self.schema.model_dump()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Relatório JSON gerado: {output_path}")
        return output_path

    def generate_csv(self) -> Path:
        """
        Gera relatório em CSV (uma linha por cláusula).

        Returns:
            Caminho do arquivo gerado.
        """
        output_path = self.output_dir / f"{self.base_filename}.csv"
        rows = []

        categorias = [
            ("prazos", self.schema.prazos),
            ("multas", self.schema.multas),
            ("exigencias_tecnicas", self.schema.exigencias_tecnicas),
            ("documentacoes", self.schema.documentacoes),
            ("criterios_habilitacao", self.schema.criterios_habilitacao),
            ("cronograma", self.schema.cronograma),
            ("valores", self.schema.valores),
            ("garantias", self.schema.garantias),
        ]

        for nome_categoria, clausulas in categorias:
            for clausula in clausulas:
                rows.append({
                    "categoria": nome_categoria,
                    "texto": clausula.text,
                    "contexto": clausula.context,
                    "metadata": json.dumps(clausula.metadata, ensure_ascii=False),
                })

        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        else:
            # Cria CSV vazio com cabeçalho para consistência
            pd.DataFrame(columns=["categoria", "texto", "contexto", "metadata"]).to_csv(
                output_path, index=False, encoding="utf-8-sig"
            )

        logger.info(f"Relatório CSV gerado: {output_path} ({len(rows)} linhas)")
        return output_path

    def generate_markdown(self) -> Path:
        """
        Gera relatório em Markdown legível.

        Returns:
            Caminho do arquivo gerado.
        """
        output_path = self.output_dir / f"{self.base_filename}.md"
        md_parts: list[str] = []

        # Cabeçalho
        md_parts.append("# Relatório de Análise de Edital\n")
        md_parts.append(f"*Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*\n")
        md_parts.append(
            f"*Score de Confiabilidade: **{self.schema.score_confiabilidade:.1%}***\n"
        )
        md_parts.append("---\n")

        # Identificação
        md_parts.append("## 1. Identificação\n")
        ident = self.schema.identificacao
        if ident.modalidade:
            md_parts.append(f"- **Modalidade:** {ident.modalidade}")
        if ident.numero_edital:
            md_parts.append(f"- **Número do Edital:** {ident.numero_edital}")
        if ident.numero_processo:
            md_parts.append(f"- **Número do Processo:** {ident.numero_processo}")
        if ident.objeto:
            md_parts.append(f"- **Objeto:** {ident.objeto}")
        if not any([ident.modalidade, ident.numero_edital, ident.numero_processo, ident.objeto]):
            md_parts.append("*Nenhuma informação de identificação encontrada.*")
        md_parts.append("")

        # Seções por categoria
        sections = [
            ("2. Prazos", self.schema.prazos),
            ("3. Multas e Penalidades", self.schema.multas),
            ("4. Exigências Técnicas", self.schema.exigencias_tecnicas),
            ("5. Documentações Obrigatórias", self.schema.documentacoes),
            ("6. Critérios de Habilitação", self.schema.criterios_habilitacao),
            ("7. Cronograma", self.schema.cronograma),
            ("8. Valores", self.schema.valores),
            ("9. Garantias", self.schema.garantias),
        ]

        for titulo, clausulas in sections:
            md_parts.append(f"## {titulo}\n")
            if not clausulas:
                md_parts.append("*Nenhuma cláusula encontrada nesta categoria.*\n")
                continue

            for idx, clausula in enumerate(clausulas, start=1):
                md_parts.append(f"### {idx}. {clausula.text[:120]}{'...' if len(clausula.text) > 120 else ''}\n")
                md_parts.append(f"**Texto completo:** {clausula.text}\n")
                if clausula.metadata:
                    md_parts.append("**Metadados:**")
                    for k, v in clausula.metadata.items():
                        md_parts.append(f"  - `{k}`: {v}")
                    md_parts.append("")

        # Entidades nomeadas
        if self.schema.entidades_nomeadas:
            md_parts.append("## 10. Entidades Nomeadas (NLP)\n")
            for label, values in self.schema.entidades_nomeadas.items():
                md_parts.append(f"### {label}")
                md_parts.append(", ".join(values[:20]))
                if len(values) > 20:
                    md_parts.append(f"*(+{len(values) - 20} entidades omitidas)*")
                md_parts.append("")

        # Estatísticas
        md_parts.append("## 11. Estatísticas\n")
        for k, v in self.schema.estatisticas.items():
            md_parts.append(f"- **{k.replace('_', ' ').title()}:** {v}")

        content = "\n".join(md_parts)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Relatório Markdown gerado: {output_path}")
        return output_path

    def generate_all(self) -> dict[str, Path]:
        """
        Gera todos os formatos de relatório.

        Returns:
            Dicionário com os caminhos de cada formato.
        """
        logger.info("Gerando relatórios em todos os formatos")
        return {
            "json": self.generate_json(),
            "csv": self.generate_csv(),
            "markdown": self.generate_markdown(),
        }


def generate_reports(
    schema: EditalSchema,
    base_filename: Optional[str] = None,
    formats: Optional[list[str]] = None,
) -> dict[str, Path]:
    """
    Função de conveniência para gerar relatórios.

    Args:
        schema: Schema validado.
        base_filename: Nome base dos arquivos (sem extensão).
        formats: Lista de formatos desejados ('json', 'csv', 'markdown').
                 Se None, gera todos.

    Returns:
        Dicionário {formato: caminho_arquivo}.
    """
    generator = ReportGenerator(schema, base_filename)
    formats = formats or ["json", "csv", "markdown"]

    result: dict[str, Path] = {}
    if "json" in formats:
        result["json"] = generator.generate_json()
    if "csv" in formats:
        result["csv"] = generator.generate_csv()
    if "markdown" in formats:
        result["markdown"] = generator.generate_markdown()

    return result
