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
{
  "text": "Analysis based on prompt...",
  "tables": [
    {
      "name": "Head of dataset",
      "data": [
        { "col1": 1, "col2": 2 }
      ]
    }
  ],
  "charts": [
    {
      "title": "Placeholder chart",
      "description": "Chart generation can be added later."
    }
  ]
}
