"""
API REST do Edital Analyzer.

Endpoints:
- GET  /                  - Health check / info da API
- GET  /health            - Health check simples
- POST /upload-edital     - Upload e análise de um edital
- POST /analyze-text      - Análise de texto já extraído
- GET  /reports/{name}    - Download de um relatório gerado

Para executar localmente:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Documentação interativa:
    http://localhost:8000/docs    (Swagger UI)
    http://localhost:8000/redoc   (ReDoc)
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app import __version__
from app.extractor import extract_edital_data
from app.parser import DocumentParser, DocumentParseError, UnsupportedFileError
from app.report_generator import generate_reports
from app.utils import OUTPUTS_DIR, setup_logger
from app.validator import validate_extracted_data

logger = setup_logger(__name__)

# === Configuração da app FastAPI ===
app = FastAPI(
    title="Edital Analyzer API",
    description=(
        "API para análise automatizada de editais de licitação de obras públicas. "
        "Extrai cláusulas, prazos, valores, garantias e demais informações relevantes."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS - libera origens conforme variável de ambiente (default: *)
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Modelos de request/response ===

class TextAnalysisRequest(BaseModel):
    """Request para análise de texto puro."""

    text: str = Field(..., min_length=10, description="Texto do edital a ser analisado")
    base_filename: Optional[str] = Field(None, description="Nome base para os relatórios")
    generate_files: bool = Field(False, description="Se deve gerar arquivos de relatório")


class HealthResponse(BaseModel):
    """Response do health check."""

    status: str = "ok"
    version: str = __version__
    service: str = "Edital Analyzer API"


# === Endpoints ===

@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root() -> HealthResponse:
    """Endpoint raiz com informações da API."""
    return HealthResponse()


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check para monitoramento."""
    return HealthResponse()


@app.post("/upload-edital", tags=["Análise"])
async def upload_edital(
    file: UploadFile = File(..., description="Arquivo PDF, DOCX ou TXT do edital"),
    generate_files: bool = False,
) -> JSONResponse:
    """
    Recebe um arquivo de edital, processa e retorna dados estruturados.

    O fluxo é:
    1. Salva o arquivo em local temporário
    2. Parseia o conteúdo (PDF/DOCX/TXT)
    3. Extrai cláusulas via regex + NLP
    4. Valida e normaliza com Pydantic
    5. (Opcional) Gera relatórios JSON/CSV/MD em disco
    6. Retorna o JSON estruturado

    Args:
        file: Arquivo enviado (multipart/form-data).
        generate_files: Se True, gera relatórios persistidos em outputs/.

    Returns:
        JSON com a estrutura completa do edital analisado.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome do arquivo ausente",
        )

    logger.info(f"Recebido upload: {file.filename}")

    # Salva o arquivo em diretório temporário
    suffix = Path(file.filename).suffix
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
    except Exception as e:
        logger.exception(f"Erro ao salvar arquivo temporário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar arquivo: {e}",
        )
    finally:
        await file.close()

    try:
        # 1. Parse
        try:
            parser = DocumentParser(tmp_path)
            text = parser.parse()
        except UnsupportedFileError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except DocumentParseError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Erro ao parsear arquivo: {e}",
            )

        # 2. Extração
        edital_data = extract_edital_data(text)

        # 3. Validação
        schema = validate_extracted_data(edital_data.to_dict())

        response_data: dict = {
            "filename": file.filename,
            "data": schema.model_dump(),
        }

        # 4. Geração de relatórios (opcional)
        if generate_files:
            base = Path(file.filename).stem
            reports = generate_reports(schema, base_filename=base)
            response_data["reports"] = {k: str(v.name) for k, v in reports.items()}
            logger.info(f"Relatórios gerados para {file.filename}: {list(reports.keys())}")

        logger.info(
            f"Análise concluída: {file.filename} "
            f"(score: {schema.score_confiabilidade:.2f})"
        )
        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erro inesperado durante análise: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado: {e}",
        )
    finally:
        # Limpa arquivo temporário
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError as e:
                logger.warning(f"Falha ao remover temp file {tmp_path}: {e}")


@app.post("/analyze-text", tags=["Análise"])
async def analyze_text(request: TextAnalysisRequest) -> JSONResponse:
    """
    Analisa texto já extraído (não precisa fazer upload de arquivo).

    Útil para integrações que já fazem o parsing externamente.

    Args:
        request: Body com o texto e opções de geração.

    Returns:
        JSON com a estrutura completa do edital analisado.
    """
    try:
        edital_data = extract_edital_data(request.text)
        schema = validate_extracted_data(edital_data.to_dict())

        response_data: dict = {"data": schema.model_dump()}

        if request.generate_files:
            reports = generate_reports(schema, base_filename=request.base_filename)
            response_data["reports"] = {k: str(v.name) for k, v in reports.items()}

        return JSONResponse(content=response_data)

    except Exception as e:
        logger.exception(f"Erro durante analyze-text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.get("/reports/{filename}", tags=["Relatórios"])
async def download_report(filename: str) -> FileResponse:
    """
    Faz download de um relatório previamente gerado.

    Args:
        filename: Nome do arquivo no diretório outputs/.

    Returns:
        Arquivo binário para download.
    """
    # Bloqueia path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de arquivo inválido",
        )

    file_path = OUTPUTS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relatório '{filename}' não encontrado",
        )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )


# Permite rodar com `python -m app.main` além de `uvicorn app.main:app`
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload_flag = os.getenv("API_RELOAD", "true").lower() == "true"

    logger.info(f"Iniciando servidor em http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_flag)
