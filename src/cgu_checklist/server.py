import hashlib

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cgu_checklist import DocumentTooLong, analyze, extract

HOST = "127.0.0.1"
PORT = 8787

app = FastAPI(title="cgu-checklist")
cache: dict[str, dict] = {}


class AnalyzeRequest(BaseModel):
    url: str
    html: str


@app.post("/analyze")
def analyze_page(request: AnalyzeRequest) -> dict:
    text = extract(request.html)
    if not text:
        raise HTTPException(422, "Aucun texte exploitable dans cette page")
    key = hashlib.sha256(text.encode()).hexdigest()
    if key not in cache:
        try:
            cache[key] = analyze(text)
        except DocumentTooLong as e:
            raise HTTPException(413, f"Document trop long pour une seule requête ({e})") from e
    return {"url": request.url, **cache[key]}


def main() -> None:
    uvicorn.run(app, host=HOST, port=PORT)
