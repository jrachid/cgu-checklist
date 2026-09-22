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
CONFIDENT = 0.7
NO_EVIDENCE = 0.5
MAX_CITATIONS = 3
MIN_CITATION = 0.15


@dataclass(frozen=True)
class Point:
    key: str
    label: str
    question: str
    yes: str
    no: str
    no_from_absence: bool = False


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
        "arbitration_opt_out",
        "Vous laisse refuser l'arbitrage",
        "Can the user opt out of or reject the arbitration agreement, for example by sending a notice within a set period after accepting the terms?",
        "The terms give the user a way to opt out of or reject arbitration, such as a written notice within a deadline",
        "The terms make arbitration mandatory with no way for the user to opt out",
        no_from_absence=True,
    ),
    Point(
        "indemnity",
        "Vous oblige à l'indemniser",
        "Do these terms require the user to indemnify or defend the company, paying its losses, damages or legal fees for claims related to the user's use of the service?",
        "The user must indemnify, defend or hold the company harmless, including covering its legal costs",
        "The terms explicitly state the user owes the company no indemnification",
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
    if response.status_code == 400:
        detail = response.json().get("detail")
        if isinstance(detail, dict) and detail.get("error_type") == "max_tokens_exceeded":
            raise DocumentTooLong(f"{len(document)} caractères")
    response.raise_for_status()
    return response.json()


def verdict(point: Point, answer: dict, where: dict) -> str:
    """verdict rend unsure quand Jev hésite, ou quand il tranche sans trouver de paragraphe qui le justifie."""
    if answer["probabilities"][answer["choice"]] < CONFIDENT:
        return "unsure"
    needs_clause = answer["choice"] == "yes" or (answer["choice"] == "no" and not point.no_from_absence)
    if needs_clause and where["probabilities"]["NONE"] >= NO_EVIDENCE:
        return "unsure"
    return answer["choice"]


def citations(where: dict, paras: list[Paragraph]) -> list[dict]:
    ranked = sorted(
        ((pid_, prob) for pid_, prob in where["probabilities"].items() if pid_ != "NONE"),
        key=lambda item: -item[1],
    )
    kept = [item for item in ranked[:MAX_CITATIONS] if item[1] >= MIN_CITATION] or ranked[:1]
    return [
        {"id": pid_, "probability": prob, "text": paras[int(pid_[1:])].text, "quote": paras[int(pid_[1:])].quote}
        for pid_, prob in kept
    ]


def analyze(text: str) -> dict:
    """analyze lève DocumentTooLong si le texte dépasse le contexte de Jev."""
    paras = paragraphs(text)
    result = ask_jev(paras)
    answers = result["answers"]
    points = []
    for p in POINTS:
        answer, where = answers[p.key], answers[f"{p.key}__where"]
        points.append(
            {
                "key": p.key,
                "label": p.label,
                "verdict": verdict(p, answer, where),
                "probabilities": answer["probabilities"],
                "citations": [] if answer["choice"] == "not_mentioned" else citations(where, paras),
            }
        )
    return {
        "model": result["model"],
        "input_tokens": result["usage"]["input_tokens"],
        "paragraphs": len(paras),
        "points": points,
    }


RANK = {"yes": 2, "no": 2, "unsure": 1, "not_mentioned": 0}


def strength(point: dict) -> tuple[int, float]:
    probs = point["probabilities"]
    return RANK[point["verdict"]], max(probs["yes"], probs["no"])


def combine(analyses: list[tuple[str, dict]]) -> dict:
    """combine garde, pour chaque point, le document qui y répond le plus nettement ; deux réponses opposées donnent unsure."""
    points = []
    for i in range(len(POINTS)):
        candidates = [
            {**analysis["points"][i], "source": url} for url, analysis in analyses
        ]
        best = max(candidates, key=strength)
        if {"yes", "no"} <= {c["verdict"] for c in candidates}:
            best = {**best, "verdict": "unsure"}
        best = {**best, "citations": [{**c, "url": best["source"]} for c in best["citations"]]}
        points.append(best)
    return {
        "documents": [
            {"url": url, **{k: analysis[k] for k in ("model", "input_tokens", "paragraphs")}}
            for url, analysis in analyses
        ],
        "points": points,
    }


ICONS = {"yes": "✅", "no": "❌", "not_mentioned": "➖", "unsure": "⚠️ "}


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage : cgu-checklist <url-ou-fichier> [<url-ou-fichier>…]")
    try:
        result = combine([(source, analyze(load_text(source))) for source in sys.argv[1:]])
    except DocumentTooLong as e:
        sys.exit(f"Document trop long pour une seule requête ({e}) : il faudrait le découper")

    print()
    for doc in result["documents"]:
        print(f"{doc['url']} : {doc['paragraphs']} paragraphes, {doc['input_tokens']} tokens ({doc['model']})")
    print()
    for point in result["points"]:
        probs = " ".join(f"{k}={v:.2f}" for k, v in point["probabilities"].items())
        print(f"{ICONS[point['verdict']]}  {point['label']}   [{probs}]")
        for c in point["citations"]:
            excerpt = f"{c['text'][:220]}{'…' if len(c['text']) > 220 else ''}"
            print(f"      ↳ {Path(c['url']).name} {c['id']} ({c['probability']:.2f}) « {excerpt} »")
    print()
