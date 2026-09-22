"""Package cgu_checklist lit des conditions d'utilisation et en tire une check-list de points cruciaux avec Jev."""

import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
import trafilatura

API_URL = "https://api.typesafe.ai/v1/systemone"
MAX_PARAGRAPHS = 254
MAX_HEADING_LENGTH = 90
MAX_STATE_TOKENS = 30_000
CONFIDENT = 0.7


@dataclass(frozen=True)
class Point:
    key: str
    label: str
    question: str
    yes: str
    no: str


POINTS = [
    Point(
        "commercial_data",
        "Utilise vos données à des fins commerciales ou publicitaires",
        "Do these terms allow the company to use the user's personal data for commercial, marketing or advertising purposes?",
        "The terms explicitly allow using personal data for advertising, marketing, profiling or other commercial purposes",
        "The terms explicitly state personal data is not used for advertising or commercial purposes",
    ),
    Point(
        "third_party_sharing",
        "Partage vos données avec des tiers",
        "Do these terms allow the company to share or sell the user's personal data to third parties or partners, beyond technical subcontractors?",
        "The terms allow sharing, selling or transferring personal data to partners, advertisers or other third parties",
        "The terms explicitly state personal data is never shared with or sold to third parties",
    ),
    Point(
        "content_license",
        "S'arroge des droits sur ce que vous publiez",
        "Do these terms grant the company a license to use, reproduce, modify or distribute content the user uploads or publishes?",
        "The user grants the company a license over their content",
        "The terms explicitly state the company obtains no rights over user content",
    ),
    Point(
        "unilateral_changes",
        "Peut modifier les conditions sans votre accord explicite",
        "Can the company change these terms unilaterally, with continued use counting as acceptance or without individual notice?",
        "The company may modify the terms at its discretion; continued use means acceptance, or notice is not guaranteed",
        "Changes require the user's explicit consent",
    ),
    Point(
        "account_termination",
        "Peut suspendre ou supprimer votre compte à sa discrétion",
        "Can the company suspend or terminate the user's account at its own discretion or without prior notice?",
        "The company may suspend or close accounts at its discretion, for any reason, or without notice",
        "Termination is only possible for listed reasons and with prior notice",
    ),
    Point(
        "liability_limit",
        "Limite ou exclut sa responsabilité",
        "Do these terms limit or exclude the company's liability towards the user, or disclaim warranties on the service?",
        "The terms cap, limit or exclude the company's liability, or provide the service as is without warranty",
        "The terms explicitly state the company's liability is not limited",
    ),
    Point(
        "dispute_resolution",
        "Impose l'arbitrage ou un tribunal éloigné",
        "Do these terms force disputes into arbitration, waive class actions, or impose a court or jurisdiction far from the user?",
        "The terms require arbitration, waive collective actions, or impose a specific foreign or distant jurisdiction",
        "The terms explicitly let the user go to their local courts",
    ),
    Point(
        "data_retention",
        "Conserve vos données après suppression du compte",
        "Do these terms allow the company to keep the user's personal data after the account is deleted?",
        "Some personal data is retained after account deletion, beyond what the law strictly requires",
        "The terms state personal data is deleted when the account is deleted",
    ),
]



class DocumentTooLong(Exception):
    pass


@dataclass(frozen=True)
class Paragraph:
    text: str
    quote: str


def extract(html: str) -> str:
    return trafilatura.extract(html, include_tables=True) or ""


def load_text(source: str) -> str:
    if Path(source).exists():
        return Path(source).read_text()
    html = httpx.get(source, follow_redirects=True, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
    text = extract(html)
    if not text:
        sys.exit(f"Aucun texte exploitable extrait de {source}")
    return text


def is_heading(line: str) -> bool:
    return (
        len(line) <= MAX_HEADING_LENGTH
        and not line.startswith(("-", "–", "•", "*"))
        and not line.endswith((".", ",", ";", ":", "!", "?", "»", ")"))
    )


def paragraphs(text: str) -> list[Paragraph]:
    paras, heading = [], []
    for line in (raw.strip() for raw in text.splitlines()):
        if not line:
            continue
        if is_heading(line):
            heading.append(line)
            continue
        paras.append(Paragraph(" — ".join([*heading, line]), line))
        heading = []
    if heading:
        paras.append(Paragraph(" — ".join(heading), heading[-1]))
    size = math.ceil(len(paras) / MAX_PARAGRAPHS)
    return [
        Paragraph(" ".join(p.text for p in paras[i : i + size]), paras[i].quote)
        for i in range(0, len(paras), size)
    ]


def pid(i: int) -> str:
    return f"P{i:03d}"


def questions(ids: list[str]) -> dict:
    qs = {}
    for p in POINTS:
        qs[p.key] = {
            "type": "choice",
            "instructions": p.question,
            "criteria": {
                "yes": p.yes,
                "no": p.no,
                "not_mentioned": "The terms do not address this point",
            },
        }
        qs[f"{p.key}__where"] = {
            "type": "choice",
            "instructions": f"Which paragraph of `cgu` best supports the answer to: {p.question}",
            "criteria": {**{i: None for i in ids}, "NONE": "No paragraph addresses this"},
        }
    return qs


def ask_jev(paras: list[Paragraph]) -> dict:
    document = "\n".join(f"{pid(i)}| {p.text}" for i, p in enumerate(paras))
    # Estimation grossière : le français tourne autour de 3,5 caractères par token.
    if len(document) / 3.5 > MAX_STATE_TOKENS:
        raise DocumentTooLong(f"~{len(document) / 3.5:.0f} tokens")
    response = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}"},
        json={
            "model": "jev-latest",
            "state": {"cgu": document},
            "questions": questions([pid(i) for i in range(len(paras))]),
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def verdict(answer: dict) -> str:
    if answer["probabilities"][answer["choice"]] < CONFIDENT:
        return "unsure"
    return answer["choice"]


def analyze(text: str) -> dict:
    """analyze lève DocumentTooLong si le texte dépasse le contexte de Jev."""
    paras = paragraphs(text)
    result = ask_jev(paras)
    answers = result["answers"]
    points = []
    for p in POINTS:
        answer, where = answers[p.key], answers[f"{p.key}__where"]
        citation = None
        if answer["choice"] != "not_mentioned" and where["choice"] != "NONE":
            para = paras[int(where["choice"][1:])]
            citation = {
                "id": where["choice"],
                "probability": where["probabilities"][where["choice"]],
                "text": para.text,
                "quote": para.quote,
            }
        points.append(
            {
                "key": p.key,
                "label": p.label,
                "verdict": verdict(answer),
                "probabilities": answer["probabilities"],
                "citation": citation,
            }
        )
    return {
        "model": result["model"],
        "input_tokens": result["usage"]["input_tokens"],
        "paragraphs": len(paras),
        "points": points,
    }


ICONS = {"yes": "✅", "no": "❌", "not_mentioned": "➖", "unsure": "⚠️ "}


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage : cgu-checklist <url-ou-fichier>")
    try:
        result = analyze(load_text(sys.argv[1]))
    except DocumentTooLong as e:
        sys.exit(f"Document trop long pour une seule requête ({e}) : il faudrait le découper")

    print(f"\n{result['paragraphs']} paragraphes analysés — {result['input_tokens']} tokens ({result['model']})\n")
    for point in result["points"]:
        probs = " ".join(f"{k}={v:.2f}" for k, v in point["probabilities"].items())
        print(f"{ICONS[point['verdict']]}  {point['label']}   [{probs}]")
        if c := point["citation"]:
            print(f"      ↳ {c['id']} ({c['probability']:.2f}) « {c['text'][:220]}{'…' if len(c['text']) > 220 else ''} »")
    print()
