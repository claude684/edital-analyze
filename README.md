# 📑 Edital Analyzer

> Sistema de análise automatizada de editais de licitação de obras públicas brasileiras.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## ✨ Funcionalidades

- 📄 **Leitura multi-formato:** PDF, DOCX e TXT
- 🔍 **Extração estruturada** de:
  - Prazos (execução, vigência, recursos)
  - Multas e penalidades (com percentuais)
  - Exigências técnicas (atestados, ARTs, registros CREA/CAU)
  - Documentações obrigatórias
  - Critérios de habilitação (jurídica, fiscal, técnica, econômica)
  - Cronograma (datas-chave em ISO 8601)
  - Valores (estimado, máximo, lance — com parsing R$ → float)
  - Garantias (contratual, proposta, caução)
- 🧠 **NLP** com spaCy (modelo `pt_core_news_sm`) para entidades nomeadas
- ✅ **Validação** com Pydantic v2 + score de confiabilidade
- 📊 **Relatórios** em **JSON, CSV e Markdown**
- 🌐 **API REST** com FastAPI (OpenAPI/Swagger UI incluídos)
- 💻 **CLI** para uso em lote
- 🐍 Arquitetura modular e escalável

---

## 🏗️ Estrutura do Projeto

```
edital-analyzer/
│
├── app/                          # Código fonte
│   ├── __init__.py
│   ├── main.py                   # API FastAPI (entrypoint)
│   ├── cli.py                    # Interface de linha de comando
│   ├── parser.py                 # Leitura de PDF/DOCX/TXT
│   ├── extractor.py              # Extração via regex + NLP
│   ├── validator.py              # Validação Pydantic
│   ├── report_generator.py       # Geração de relatórios
│   └── utils.py                  # Logging, helpers, configuração
│
├── data/                         # Editais de entrada (não versionado)
├── outputs/                      # Relatórios gerados (não versionado)
├── logs/                         # Logs rotativos (não versionado)
│
├── tests/                        # Testes pytest
│   ├── conftest.py
│   ├── test_utils.py
│   ├── test_extractor.py
│   ├── test_validator.py
│   └── test_api.py
│
├── .vscode/                      # Configurações VS Code
│   ├── launch.json               # Debug
│   ├── tasks.json                # Tarefas rápidas
│   ├── settings.json             # Settings do workspace
│   └── extensions.json           # Extensões recomendadas
│
├── .github/workflows/
│   └── ci.yml                    # Pipeline CI/CD GitHub Actions
│
├── requirements.txt              # Dependências Python
├── pyproject.toml                # Configuração de black/ruff/pytest
├── .gitignore
├── .env.example                  # Template de variáveis de ambiente
├── LICENSE
└── README.md
```

---

## 🚀 Instalação

### Pré-requisitos

- **Python 3.11** ou superior
- **pip** atualizado
- Git

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/edital-analyzer.git
cd edital-analyzer

# 2. Crie um ambiente virtual
python -m venv .venv

# 3. Ative o ambiente
# Linux/Mac:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat

# 4. Instale as dependências
pip install --upgrade pip
pip install -r requirements.txt

# 5. Baixe o modelo spaCy em português
python -m spacy download pt_core_news_sm

# 6. Configure as variáveis de ambiente
cp .env.example .env
# (Edite o .env conforme necessário)
```

---

## 💻 Como Rodar no VS Code

1. **Abra a pasta** do projeto no VS Code:

   ```bash
   code .
   ```

2. **Selecione o interpretador Python**:
   - `Ctrl+Shift+P` → "Python: Select Interpreter" → escolha `.venv/bin/python`

3. **Instale as extensões recomendadas** (o VS Code irá sugerir automaticamente).

4. **Execute via Debugger** (F5):
   - "FastAPI: Uvicorn (Debug)" — sobe a API em modo debug
   - "CLI: Analisar Arquivo" — roda a CLI em arquivo único
   - "Pytest: Todos os Testes" — roda toda a suite de testes

5. **Ou via Tasks** (`Ctrl+Shift+P` → "Tasks: Run Task"):
   - "Setup completo (pip + spaCy)"
   - "Rodar API (Uvicorn)"
   - "Rodar Testes"
   - "Rodar Testes com Coverage"

---

## ▶️ Como Executar

### Opção 1: API REST (FastAPI)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health

#### Exemplo de chamada

```bash
curl -X POST "http://localhost:8000/upload-edital?generate_files=true" \
     -F "file=@data/edital_municipal.pdf"
```

Resposta (resumida):

```json
{
  "filename": "edital_municipal.pdf",
  "data": {
    "identificacao": {
      "modalidade": "Pregão Eletrônico",
      "numero_edital": "045/2024",
      "objeto": "Pavimentação asfáltica..."
    },
    "prazos": [...],
    "multas": [...],
    "valores": [...],
    "score_confiabilidade": 0.87
  },
  "reports": {
    "json": "edital_municipal.json",
    "csv": "edital_municipal.csv",
    "markdown": "edital_municipal.md"
  }
}
```

### Opção 2: CLI

```bash
# Analisar um arquivo
python -m app.cli analisar data/edital.pdf

# Analisar todos os editais de uma pasta
python -m app.cli analisar-pasta data/

# Especificar formatos de saída
python -m app.cli analisar data/edital.pdf --formato json,markdown
```

Os relatórios são salvos em `outputs/`.

### Opção 3: Programaticamente

```python
from app.parser import DocumentParser
from app.extractor import extract_edital_data
from app.validator import validate_extracted_data
from app.report_generator import generate_reports

# Pipeline completo
text = DocumentParser("data/edital.pdf").parse()
data = extract_edital_data(text)
schema = validate_extracted_data(data.to_dict())
reports = generate_reports(schema, base_filename="meu_edital")

print(f"Score: {schema.score_confiabilidade}")
print(f"Relatórios: {reports}")
```

---

## 🧪 Testes

```bash
# Rodar todos os testes
pytest -v

# Com cobertura
pytest --cov=app --cov-report=term-missing tests/

# Cobertura HTML (gera htmlcov/index.html)
pytest --cov=app --cov-report=html tests/
```

---

## 🛠️ Endpoints da API

| Método | Rota                  | Descrição                              |
|--------|-----------------------|----------------------------------------|
| GET    | `/`                   | Informações da API                     |
| GET    | `/health`             | Health check                           |
| POST   | `/upload-edital`      | Upload de PDF/DOCX/TXT e análise       |
| POST   | `/analyze-text`       | Análise de texto enviado no body JSON  |
| GET    | `/reports/{filename}` | Download de relatório gerado           |

Documentação interativa completa em `/docs` (Swagger) e `/redoc`.

---

## 📤 Como Subir no GitHub

```bash
# 1. Inicialize o repositório local
git init
git add .
git commit -m "feat: initial commit - edital-analyzer"

# 2. Crie um repositório no GitHub (via interface web ou GitHub CLI):
gh repo create edital-analyzer --public --source=. --remote=origin

# (ou manualmente, depois adicione o remote)
git remote add origin https://github.com/SEU_USUARIO/edital-analyzer.git

# 3. Renomeie a branch principal e faça o push
git branch -M main
git push -u origin main
```

O pipeline de CI definido em `.github/workflows/ci.yml` rodará automaticamente
em cada `push` e `pull_request`, verificando lint, formatação e testes.

---

## 🧰 Tecnologias

| Categoria        | Bibliotecas                                   |
|------------------|-----------------------------------------------|
| Web Framework    | FastAPI, Uvicorn                              |
| Parsing          | pdfplumber, PyPDF2, python-docx               |
| NLP              | spaCy + `pt_core_news_sm`                     |
| Dados            | pandas, numpy                                 |
| Validação        | Pydantic v2                                   |
| Testes           | pytest, pytest-cov, httpx                     |
| Qualidade        | black, ruff, mypy                             |

---

## 🗺️ Roadmap

- [ ] Integração com OCR (Tesseract) para PDFs escaneados
- [ ] Banco de dados (PostgreSQL) para histórico de análises
- [ ] Dashboard web (React/Vue) consumindo a API
- [ ] Comparação automática entre editais
- [ ] Detecção de cláusulas restritivas/abusivas
- [ ] Integração com APIs de licitações governamentais (PNCP)

---

## 🤝 Contribuindo

1. Fork do projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto é distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## ⚠️ Aviso

Este sistema realiza extração heurística baseada em regex e NLP. Os resultados
**não substituem** análise jurídica profissional de editais. Sempre revise manualmente
as informações extraídas antes de tomar decisões de negócio ou legais.
