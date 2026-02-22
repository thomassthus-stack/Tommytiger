# Analysis Backend

A simple FastAPI backend that accepts a CSV/Excel file and a text prompt, performs a basic analysis, and returns:

- text summary  
- tables (as JSON)  
- placeholder chart descriptions  

Designed to run on DigitalOcean App Platform.

---

## Endpoints

### `GET /health`

Health check.

**Response:**

```json
{ "status": "ok" }
