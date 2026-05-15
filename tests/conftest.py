"""Fixtures globais para os testes."""

import pytest


SAMPLE_EDITAL_TEXT = """
EDITAL DE PREGÃO ELETRÔNICO Nº 045/2024
PROCESSO ADMINISTRATIVO Nº 12345/2024

O MUNICÍPIO DE EXEMPLO, por intermédio da Secretaria de Obras, torna público que
realizará licitação na modalidade Pregão Eletrônico, do tipo menor preço.

OBJETO: Contratação de empresa especializada em obras de pavimentação asfáltica
das vias urbanas do bairro Centro.

VALOR ESTIMADO: R$ 2.500.000,00 (dois milhões e quinhentos mil reais).

PRAZO DE EXECUÇÃO: 180 (cento e oitenta) dias contados da emissão da ordem de serviço.
PRAZO DE VIGÊNCIA: O contrato terá vigência de 12 (doze) meses.

DATA DA SESSÃO PÚBLICA: 15/03/2024 às 09h00.

HABILITAÇÃO JURÍDICA: A licitante deverá apresentar contrato social e cartão CNPJ.

REGULARIDADE FISCAL: Certidão negativa de débitos federais, FGTS e trabalhista.

QUALIFICAÇÃO TÉCNICA: A licitante deve apresentar atestado de capacidade técnica
emitido por pessoa jurídica de direito público ou privado, registrado no CREA, comprovando
a execução de obras de pavimentação com no mínimo 5.000 m².

GARANTIA DE EXECUÇÃO: Será exigida garantia contratual de 5% do valor do contrato,
podendo ser na forma de seguro-garantia ou fiança bancária.

PENALIDADES: O atraso na execução sujeitará a contratada a multa de 0,5% por dia,
limitada a 10% do valor do contrato.
"""


@pytest.fixture
def sample_edital_text() -> str:
    """Retorna um texto de edital de exemplo para uso nos testes."""
    return SAMPLE_EDITAL_TEXT
