# Pasta `data/`

Coloque aqui os arquivos de edital que deseja analisar (PDF, DOCX ou TXT).

Os arquivos desta pasta são ignorados pelo Git por padrão (ver `.gitignore`),
para evitar que editais confidenciais ou pesados sejam commitados.

## Exemplo de uso

```bash
# Copie um edital para esta pasta
cp ~/Downloads/edital_municipal.pdf data/

# Analise pela CLI
python -m app.cli analisar data/edital_municipal.pdf

# Ou pela API
curl -X POST http://localhost:8000/upload-edital \
     -F "file=@data/edital_municipal.pdf"
```
