import hashlib
import json

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cgu_checklist import DocumentTooLong, Link, analyze, combine, extract

HOST = "127.0.0.1"
PORT = 8787

app = FastAPI(title="cgu-checklist")
cache: dict[str, dict] = {}


class PageLink(BaseModel):
    text: str
    href: str


class Document(BaseModel):
    url: str
    html: str
    links: list[PageLink] = []


class AnalyzeRequest(BaseModel):
    documents: list[Document] = Field(min_length=1)


def analyze_cached(document: Document) -> dict | None:
    text = extract(document.html)
    if not text:
        return None
    links = [Link(link.text, link.href) for link in document.links]
    key = hashlib.sha256(json.dumps([text, [(l.text, l.href) for l in links]]).encode()).hexdigest()
    if key not in cache:
        try:
            cache[key] = analyze(text, links)
        except DocumentTooLong as e:
            raise HTTPException(413, f"Document trop long pour une seule requête : {document.url} ({e})") from e
    return cache[key]


@app.post("/analyze")
def analyze_pages(request: AnalyzeRequest) -> dict:
    analyses = [(doc.url, analysis) for doc in request.documents if (analysis := analyze_cached(doc))]
    if not analyses:
        raise HTTPException(422, "Aucun texte exploitable dans ces pages")
    return combine(analyses)


def main() -> None:
    uvicorn.run(app, host=HOST, port=PORT)
