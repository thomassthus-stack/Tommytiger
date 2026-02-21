# Analysis Backend

En enkel FastAPI‑backend som tar imot en CSV/Excel‑fil og en tekstprompt, genererer Python‑analyse via LLM og returnerer:

- tekstlig analyse  
- tabeller  
- grafbeskrivelser  

Backend er laget for å kjøre på DigitalOcean App Platform.

---

## Endepunkter

### POST /run_analysis
Tar imot:
- `prompt` (tekst)
- `file` (CSV eller Excel)

Returnerer:
- `text`
- `tables`
- `charts`

### GET /health
Sjekker om backend kjører.

---

## Miljøvariabler

Sett i DigitalOcean App Platform:

