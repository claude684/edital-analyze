"""
Módulo de utilidades do sistema.

Contém:
- Configuração centralizada de logging
- Funções de limpeza e normalização de texto
- Helpers de manipulação de datas e valores monetários
- Carregamento de variáveis de ambiente
"""

import logging
import os
import re
import unicodedata
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# Diretórios base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
LOGS_DIR = BASE_DIR / "logs"

# Garante que os diretórios existam
for directory in (DATA_DIR, OUTPUTS_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str = "edital_analyzer", level: Optional[str] = None) -> logging.Logger:
    """
    Configura um logger padronizado para o sistema.

    Args:
        name: Nome do logger (geralmente o nome do módulo).
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Se None, usa LOG_LEVEL do .env ou INFO como padrão.

    Returns:
        Instância configurada de logging.Logger.
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    logger = logging.getLogger(name)

    # Evita adicionar handlers duplicados se o logger já foi configurado
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler rotativo para arquivo (5 MB por arquivo, mantém 3 backups)
    file_handler = RotatingFileHandler(
        LOGS_DIR / "edital_analyzer.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Logger global do módulo
logger = setup_logger(__name__)


def clean_text(text: str) -> str:
    """
    Limpa e normaliza texto extraído de documentos.

    Remove caracteres de controle, espaços excessivos e normaliza quebras de linha.

    Args:
        text: Texto bruto extraído do documento.

    Returns:
        Texto limpo e normalizado.
    """
    if not text:
        return ""

    # Normaliza caracteres Unicode (NFKC = compatibility composition)
    text = unicodedata.normalize("NFKC", text)

    # Remove caracteres de controle (exceto \n, \t, \r)
    text = "".join(
        ch for ch in text if ch in ("\n", "\t", "\r") or not unicodedata.category(ch).startswith("C")
    )

    # Normaliza quebras de linha (\r\n e \r -> \n)
    text = re.sub(r"\r\n?", "\n", text)

    # Remove espaços múltiplos dentro de linhas, preservando quebras de linha
    text = re.sub(r"[ \t]+", " ", text)

    # Remove linhas vazias excessivas (mais de 2 seguidas viram 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def parse_brazilian_currency(value_str: str) -> Optional[float]:
    """
    Converte valores monetários no formato brasileiro para float.

    Exemplos:
        "R$ 1.234.567,89" -> 1234567.89
        "1.500,00"        -> 1500.00
        "R$1.000"         -> 1000.00

    Args:
        value_str: String contendo valor monetário em formato brasileiro.

    Returns:
        Valor numérico como float ou None se inválido.
    """
    if not value_str:
        return None

    try:
        # Remove "R$", espaços, e quaisquer caracteres não-numéricos exceto . , -
        cleaned = re.sub(r"[^\d,.\-]", "", value_str)

        # Formato BR: pontos como separador de milhar e vírgula como decimal
        # Remove pontos (milhar) e troca vírgula por ponto (decimal)
        if "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        # Caso só tenha pontos, assumimos que são separadores de milhar
        # apenas se houver mais de um ponto ou se o ponto não for decimal
        elif cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")

        return float(cleaned)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Falha ao converter valor monetário '{value_str}': {e}")
        return None


def parse_brazilian_date(date_str: str) -> Optional[str]:
    """
    Converte datas no formato brasileiro para ISO 8601 (YYYY-MM-DD).

    Aceita formatos:
        - DD/MM/YYYY
        - DD-MM-YYYY
        - DD.MM.YYYY
        - DD de <mês> de YYYY

    Args:
        date_str: String contendo a data em formato brasileiro.

    Returns:
        Data em formato ISO (YYYY-MM-DD) ou None se inválida.
    """
    if not date_str:
        return None

    meses = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
        "outubro": 10, "novembro": 11, "dezembro": 12,
    }

    date_str = date_str.strip().lower()

    # Tenta formato numérico (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY)
    match = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", date_str)
    if match:
        try:
            day, month, year = match.groups()
            year_int = int(year)
            if year_int < 100:
                year_int += 2000 if year_int < 50 else 1900
            return datetime(year_int, int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError as e:
            logger.warning(f"Data numérica inválida '{date_str}': {e}")
            return None

    # Tenta formato por extenso ("12 de janeiro de 2025")
    match = re.match(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", date_str)
    if match:
        try:
            day, month_name, year = match.groups()
            month = meses.get(month_name)
            if not month:
                return None
            return datetime(int(year), month, int(day)).strftime("%Y-%m-%d")
        except ValueError as e:
            logger.warning(f"Data por extenso inválida '{date_str}': {e}")
            return None

    return None


def slugify(text: str) -> str:
    """
    Converte uma string em um slug seguro para nome de arquivo.

    Args:
        text: Texto original.

    Returns:
        String sem acentos, em minúsculas, com '-' no lugar de espaços.
    """
    if not text:
        return "untitled"

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text or "untitled"


def get_file_extension(filename: str) -> str:
    """
    Retorna a extensão de um arquivo em minúsculas, sem o ponto.

    Args:
        filename: Nome ou caminho do arquivo.

    Returns:
        Extensão (ex: 'pdf', 'docx', 'txt') ou string vazia.
    """
    return Path(filename).suffix.lower().lstrip(".")
