"""Testes de integração da API FastAPI."""

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body


class TestUploadEdital:
    def test_upload_txt(self, sample_edital_text):
        file_bytes = sample_edital_text.encode("utf-8")
        response = client.post(
            "/upload-edital",
            files={"file": ("edital_teste.txt", io.BytesIO(file_bytes), "text/plain")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["filename"] == "edital_teste.txt"
        assert "data" in body
        assert body["data"]["identificacao"]["numero_edital"] == "045/2024"

    def test_upload_unsupported_extension(self):
        response = client.post(
            "/upload-edital",
            files={"file": ("teste.xyz", io.BytesIO(b"conteudo"), "application/octet-stream")},
        )
        assert response.status_code == 400


class TestAnalyzeText:
    def test_analyze_text_endpoint(self, sample_edital_text):
        response = client.post(
            "/analyze-text",
            json={"text": sample_edital_text, "generate_files": False},
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert body["data"]["identificacao"]["numero_edital"] == "045/2024"

    def test_analyze_text_too_short(self):
        response = client.post("/analyze-text", json={"text": "abc"})
        assert response.status_code == 422  # Pydantic validation error


class TestReportsEndpoint:
    def test_path_traversal_blocked(self):
        response = client.get("/reports/..%2F..%2Fetc%2Fpasswd")
        # Pode retornar 400 ou 404 dependendo do encoding; ambos são válidos
        assert response.status_code in (400, 404)

    def test_nonexistent_file(self):
        response = client.get("/reports/nao_existe.json")
        assert response.status_code == 404
