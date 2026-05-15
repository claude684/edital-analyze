"""
Interface de linha de comando (CLI) do Edital Analyzer.

Permite processar editais sem subir a API, útil para análises em lote
ou scripts automatizados.

Uso:
    python -m app.cli analisar <arquivo>
    python -m app.cli analisar <arquivo> --formato json,markdown
    python -m app.cli analisar-pasta <pasta>
"""

import argparse
import sys
from pathlib import Path

from app.extractor import extract_edital_data
from app.parser import DocumentParser
from app.report_generator import generate_reports
from app.utils import setup_logger
from app.validator import validate_extracted_data

logger = setup_logger(__name__)


def analisar_arquivo(arquivo: Path, formatos: list[str]) -> int:
    """
    Analisa um único arquivo de edital e gera relatórios.

    Args:
        arquivo: Caminho do arquivo.
        formatos: Lista de formatos de saída desejados.

    Returns:
        Código de saída (0 = sucesso, !=0 = erro).
    """
    if not arquivo.exists():
        logger.error(f"Arquivo não encontrado: {arquivo}")
        return 1

    try:
        logger.info(f"Analisando: {arquivo.name}")

        # Pipeline completo
        parser = DocumentParser(arquivo)
        text = parser.parse()
        edital_data = extract_edital_data(text)
        schema = validate_extracted_data(edital_data.to_dict())

        # Geração de relatórios
        reports = generate_reports(
            schema,
            base_filename=arquivo.stem,
            formats=formatos,
        )

        logger.info("Análise concluída com sucesso. Relatórios:")
        for formato, caminho in reports.items():
            logger.info(f"  - {formato.upper()}: {caminho}")

        return 0

    except Exception as e:
        logger.exception(f"Erro ao analisar {arquivo.name}: {e}")
        return 2


def analisar_pasta(pasta: Path, formatos: list[str]) -> int:
    """
    Analisa todos os arquivos suportados em uma pasta.

    Args:
        pasta: Diretório contendo editais.
        formatos: Lista de formatos de saída.

    Returns:
        Código de saída.
    """
    if not pasta.is_dir():
        logger.error(f"Pasta não encontrada: {pasta}")
        return 1

    extensoes_suportadas = {".pdf", ".docx", ".txt"}
    arquivos = [
        p for p in pasta.iterdir()
        if p.is_file() and p.suffix.lower() in extensoes_suportadas
    ]

    if not arquivos:
        logger.warning(f"Nenhum arquivo suportado encontrado em {pasta}")
        return 1

    logger.info(f"Encontrados {len(arquivos)} arquivos para processar")

    sucessos = 0
    falhas = 0
    for arquivo in arquivos:
        rc = analisar_arquivo(arquivo, formatos)
        if rc == 0:
            sucessos += 1
        else:
            falhas += 1

    logger.info(f"Processamento concluído: {sucessos} sucessos, {falhas} falhas")
    return 0 if falhas == 0 else 3


def main() -> int:
    """Entry point principal da CLI."""
    parser = argparse.ArgumentParser(
        prog="edital-analyzer",
        description="Analisador automatizado de editais de licitação",
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    # Comando: analisar (arquivo único)
    p_arquivo = subparsers.add_parser(
        "analisar",
        help="Analisa um único arquivo de edital",
    )
    p_arquivo.add_argument("arquivo", type=Path, help="Caminho do arquivo PDF/DOCX/TXT")
    p_arquivo.add_argument(
        "--formato",
        type=str,
        default="json,csv,markdown",
        help="Formatos de saída separados por vírgula (json,csv,markdown)",
    )

    # Comando: analisar-pasta (lote)
    p_pasta = subparsers.add_parser(
        "analisar-pasta",
        help="Analisa todos os arquivos suportados em uma pasta",
    )
    p_pasta.add_argument("pasta", type=Path, help="Caminho da pasta com editais")
    p_pasta.add_argument(
        "--formato",
        type=str,
        default="json,csv,markdown",
        help="Formatos de saída separados por vírgula",
    )

    args = parser.parse_args()
    formatos = [f.strip().lower() for f in args.formato.split(",")]

    if args.comando == "analisar":
        return analisar_arquivo(args.arquivo, formatos)
    elif args.comando == "analisar-pasta":
        return analisar_pasta(args.pasta, formatos)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
