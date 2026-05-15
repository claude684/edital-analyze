"""Testes do módulo validator."""

from app.extractor import extract_edital_data
from app.validator import DataValidator, validate_extracted_data, EditalSchema


class TestDataValidator:
    def test_basic_validation(self, sample_edital_text):
        data = extract_edital_data(sample_edital_text)
        schema = validate_extracted_data(data.to_dict())

        assert isinstance(schema, EditalSchema)
        assert schema.identificacao.numero_edital == "045/2024"

    def test_score_calculation(self, sample_edital_text):
        data = extract_edital_data(sample_edital_text)
        schema = validate_extracted_data(data.to_dict())

        assert 0.0 <= schema.score_confiabilidade <= 1.0
        # O texto de exemplo é rico, espera-se um score razoável
        assert schema.score_confiabilidade > 0.3

    def test_deduplication(self):
        raw_data = {
            "identificacao": {},
            "prazos": [
                {"category": "prazos", "text": "Prazo de 30 dias", "context": "", "metadata": {}},
                {"category": "prazos", "text": "Prazo de 30 dias", "context": "", "metadata": {}},
                {"category": "prazos", "text": "Prazo de 60 dias", "context": "", "metadata": {}},
            ],
            "multas": [], "exigencias_tecnicas": [], "documentacoes": [],
            "criterios_habilitacao": [], "cronograma": [], "valores": [],
            "garantias": [], "entidades_nomeadas": {}, "estatisticas": {},
        }
        validator = DataValidator(raw_data)
        schema = validator.validate()
        assert len(schema.prazos) == 2  # 30 e 60 dias (duplicata removida)

    def test_empty_data(self):
        empty = {
            "identificacao": {}, "prazos": [], "multas": [],
            "exigencias_tecnicas": [], "documentacoes": [],
            "criterios_habilitacao": [], "cronograma": [], "valores": [],
            "garantias": [], "entidades_nomeadas": {}, "estatisticas": {},
        }
        schema = validate_extracted_data(empty)
        assert schema.score_confiabilidade == 0.0
        assert schema.prazos == []
