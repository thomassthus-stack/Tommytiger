import io
import os
import json
import time
from typing import List, Optional

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openai import OpenAI

# ---------- Konfig ----------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY mangler. Sett den i .env eller som env var.")

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Analysis Backend", version="1.0.0")

# Tillat frontend (Lovable) å snakke med backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # stram inn senere om du vil
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Modeller ----------

class TableResult(BaseModel):
    name: str
    data: list  # liste av rader (dicts)

class ChartResult(BaseModel):
    title: str
    description: Optional[str] = None
    # Her kan du senere legge inn f.eks. base64-bilder eller plot-data

class AnalysisResult(BaseModel):
    text: str
    tables: List[TableResult] = []
    charts: List[ChartResult] = []


# ---------- LLM-hjelper ----------

def call_llm_for_code(user_prompt: str, df_preview: str) -> str:
    """
    Ber LLM skrive Python-kode som:
    - bruker en pandas DataFrame 'df'
    - gjør analysen brukeren ber om
    - setter variabelen result_json til json.dumps(dict med keys: text, tables, charts)
    """
    system_msg = """
Du er en dyktig dataanalytiker og Python-utvikler.
Du får en pandas DataFrame kalt 'df'.

Oppgave:
- Analyser df basert på brukerens ønske.
- Lag en tekstlig forklaring (string).
- Lag eventuelle tabeller (liste av dict-lister).
- Lag eventuelle grafer (du kan beskrive dem i tekst).

Til slutt MÅ du sette variabelen 'result_json' til json.dumps(result_dict)
med følgende struktur:

result_dict = {
    "text": "<forklaring>",
    "tables": [
        {
            "name": "<tabellnavn>",
            "data": [ { "kol1": verdi, "kol2": verdi, ... }, ... ]
        },
        ...
    ],
    "charts": [
        {
            "title": "<tittel>",
            "description": "<beskrivelse av grafen>"
        },
        ...
    ]
}

VIKTIG:
- Skriv KUN Python-kode, ingen forklarende tekst.
- Ikke print noe.
- Ikke les filer fra disk, bruk kun DataFrame 'df' som allerede finnes.
- Ikke bruk nettverk.
"""

    user_msg = f"""
Brukerens ønske:
{user_prompt}

Her er df.head():
{df_preview}
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )

    code = resp.choices[0].message.content
    if not code:
        raise RuntimeError("LLM returnerte ingen kode.")
    return code


# ---------- Sikker kjøring av generert kode ----------

def run_user_code_safely(code: str, df: pd.DataFrame) -> AnalysisResult:
    """
    Kjører LLM-generert Python-kode i et begrenset miljø.
    Forventer at koden setter variabelen 'result_json'.
    """

    allowed_builtins = {
        "print": print,
        "len": len,
        "range": range,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
    }

    safe_globals = {
        "__builtins__": allowed_builtins,
        "pd": pd,
        "np": np,
        "plt": plt,
        "json": json,
    }
    safe_locals = {
        "df": df,
    }

    start_time = time.time()

    def check_timeout():
        if time.time() - start_time > 10:
            raise TimeoutError("Koden brukte for lang tid og ble stoppet.")

    # Vi wrapper koden slik at:
    # - den kjører i _user_main()
    # - vi kan kalle check_timeout()
    wrapped_code = f"""
import json

result_json = None

def _user_main():
{chr(10).join("    " + line for line in code.splitlines())}

    check_timeout()

_user_main()
"""

    safe_globals["check_timeout"] = check_timeout

    try:
        exec(wrapped_code, safe_globals, safe_locals)
    except Exception as e:
        raise RuntimeError(f"Feil ved kjøring av generert kode: {e}")

    result_json = safe_locals.get("result_json") or safe_globals.get("result_json")
    if result_json is None:
        raise RuntimeError("Generert kode satte ikke 'result_json'.")

    if isinstance(result_json, str):
        try:
            data = json.loads(result_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"result_json er ikke gyldig JSON: {e}")
    elif isinstance(result_json, dict):
        data = result_json
    else:
        raise RuntimeError("result_json må være str eller dict.")

    text = data.get("text", "")
    tables_raw = data.get("tables", [])
    charts_raw = data.get("charts", [])

    tables: List[TableResult] = []
    for t in tables_raw:
        name = t.get("name", "Table")
        table_data = t.get("data", [])
        tables.append(TableResult(name=name, data=table_data))

    charts: List[ChartResult] = []
    for c in charts_raw:
        title = c.get("title", "Chart")
        desc = c.get("description", None)
        charts.append(ChartResult(title=title, description=desc))

    return AnalysisResult(text=text, tables=tables, charts=charts)


# ---------- Hjelper for å lese fil ----------

def load_file_to_df(file: UploadFile) -> pd.DataFrame:
    content = file.file.read()
    filename = file.filename or ""

    if filename.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        return pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(status_code=400, detail="Kun CSV og Excel støttes foreløpig.")


# ---------- Endepunkter ----------

@app.get("/health")
async def health():
    return {"status": "ok", "message": "Backend kjører."}


@app.post("/run_analysis", response_model=AnalysisResult)
async def run_analysis(
    prompt: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Hovedendepunktet:
    - Tar imot prompt + fil
    - Leser fil til DataFrame
    - Ber LLM lage Python-kode
    - Kjører koden trygt
    - Returnerer strukturert resultat
    """
    try:
        df = load_file_to_df(file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Kunne ikke lese fil: {e}")

    df_preview = df.head().to_string()

    try:
        code = call_llm_for_code(prompt, df_preview)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feil ved LLM-kall: {e}")

    try:
        result = run_user_code_safely(code, df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feil ved kjøring av analyse: {e}")

    return result


if __name__ == "__main__":
    import uvicorn
    import os
port = int(os.getenv("PORT", 8080))
uvicorn.run(app, host="0.0.0.0", port=port)
