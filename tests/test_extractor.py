"""Testes do módulo extractor."""

from app.extractor import EditalExtractor, extract_edital_data


class TestEditalExtractor:
    def test_identification_extraction(self, sample_edital_text):
        extractor = EditalExtractor(sample_edital_text)
        extractor.extract_all()
        ident = extractor.data.identificacao

        assert "modalidade" in ident
        assert "pregão" in ident["modalidade"].lower() or "pregao" in ident["modalidade"].lower()
        assert ident.get("numero_edital") == "045/2024"
        assert ident.get("numero_processo") == "12345/2024"

    def test_prazos_extracted(self, sample_edital_text):
        data = extract_edital_data(sample_edital_text)
        assert len(data.prazos) >= 1
        # Pelo menos um prazo deve ter quantidade/unidade extraídas
        with_metadata = [c for c in data.prazos if "quantidade" in c.metadata]
        assert len(with_metadata) >= 1

    def test_valores_extracted(self, sample_edital_text):
        data = extract_edital_data(sample_edital_text)
        assert len(data.valores) >= 1
        # Pelo menos um valor com numeric parseado
        valores_numericos = [
            c.metadata.get("valores_numericos", [])
            for c in data.valores
        ]
        all_values = [v for sublist in valores_numericos for v in sublist]
        assert any(v >= 1000 for v in all_values)

    def test_multas_extracted(self, sample_edital_text):
        data = extract_edital_data(sample_edital_text)
        assert len(data.multas) >= 1

    def test_garantias_extracted(self, sample_edital_text):
        data = extract_edital_data(sample_edital_text)
        assert len(data.garantias) >= 1

    def test_habilitacao_extracted(self, sample_edital_text):
        data = extract_edital_data(sample_edital_text)
        assert len(data.criterios_habilitacao) >= 1

    def test_estatisticas_present(self, sample_edital_text):
        data = extract_edital_data(sample_edital_text)
        assert data.estatisticas["total_caracteres"] > 0
        assert data.estatisticas["total_palavras"] > 0

    def test_to_dict_serializable(self, sample_edital_text):
        import json
        data = extract_edital_data(sample_edital_text)
        # Deve ser serializável em JSON sem erros
        json_str = json.dumps(data.to_dict(), ensure_ascii=False)
        assert len(json_str) > 0
