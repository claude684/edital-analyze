"""
Edital Analyzer - Sistema de Análise Automatizada de Editais de Licitação.

Pacote principal contendo todos os módulos do sistema:
- parser: leitura de PDF, DOCX e TXT
- extractor: extração de cláusulas e entidades via NLP/regex
- validator: validação e normalização dos dados extraídos
- report_generator: geração de relatórios JSON, CSV e Markdown
- utils: funções auxiliares
- main: API REST com FastAPI
"""

__version__ = "1.0.0"
__author__ = "Edital Analyzer Team"
