# Analysis Backend

FastAPI-basert backend for filanalyse med LLM-generert Python-kode.

## Endepunkter

### `POST /run_analysis`
Tar imot:
- `prompt`: tekst
- `file`: CSV eller Excel

Returnerer:
- tekstlig analyse
- tabeller
- grafbeskrivelser

### `GET /health`
Sjekker om backend kjører.

## Miljøvariabler
Sett i DigitalOcean:

