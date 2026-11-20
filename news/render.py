"""Génération de l'app web : une seule page (index.html) + données embarquées.

Toute la navigation (onglets, rubriques, fiche d'un sujet) se fait côté
téléphone dans static/app.js, sans rechargement, comme une app native.
"""
from __future__ import annotations

import json
import math
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .stocks import Quote
from .summarize import CategoryDigest

ROOT = Path(__file__).resolve().parent.parent
MONTHS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
DAYS = "lundi mardi mercredi jeudi vendredi samedi dimanche".split()
CURRENCY = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}


def french_date(d: datetime) -> str:
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"


def greeting(d: datetime) -> str:
    return "Bonsoir" if d.hour >= 18 else "Bonjour"


def format_price(value: float, currency: str) -> str:
    """1234.5 → « 1 234,50 $ » (format français, espaces insécables)."""
    num = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    symbol = CURRENCY.get(currency, currency)
    return f"{num} {symbol}" if symbol else num


def _safe_url(url: str) -> str:
    return url if url.startswith(("https://", "http://")) else ""


def build_payload(digests: list[CategoryDigest], quotes: list[Quote], now: datetime) -> dict:
    tz = now.tzinfo
    categories = []
    for d in digests:
        stories = []
        for i, s in enumerate(d.stories):
            arts = sorted(s.articles, key=lambda a: a.published, reverse=True)
            stories.append({
                "id": f"{d.id}-{i + 1}",
                "title": s.title,
                "summary": s.summary,
                "sources": s.sources,
                "time": arts[0].published.astimezone(tz).strftime("%Hh%M") if arts else "",
                "articles": [
                    {"title": a.title, "link": _safe_url(a.link), "source": a.source,
                     "time": a.published.astimezone(tz).strftime("%d/%m · %Hh%M")}
                    for a in arts
                ],
            })
        categories.append({
            "id": d.id, "title": d.title, "short": d.short, "emoji": d.emoji, "color": d.color,
            "tagline": d.tagline, "overview": d.overview, "articleCount": d.article_count,
            "stories": stories,
        })

    words = sum(len(s["title"].split()) + len(s["summary"].split()) for c in categories for s in c["stories"])
    return {
        "date": now.date().isoformat(),
        "dateLong": french_date(now),
        "greeting": greeting(now),
        "generatedAt": now.strftime("%Hh%M"),
        "aiGenerated": any(d.ai_generated for d in digests),
        "readingMinutes": max(1, math.ceil(words / 220)),
        "stats": {
            "stories": sum(len(c["stories"]) for c in categories),
            "articles": sum(d.article_count for d in digests),
            "sources": len({a.source for d in digests for s in d.stories for a in s.articles}),
        },
        "categories": categories,
        "quotes": [
            {"symbol": q.symbol, "name": q.name, "price": format_price(q.price, q.currency),
             "change": {"1j": q.change_1d, "5j": q.change_5d, "1m": q.change_1m},
             "history": [round(v, 4) for v in q.history], "link": q.link}
            for q in quotes
        ],
    }


def render(digests: list[CategoryDigest], quotes: list[Quote], now: datetime, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(digests, quotes, now)
    # « </ » échappé pour qu'un titre d'article ne puisse pas fermer la balise <script>
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    env = Environment(loader=FileSystemLoader(ROOT / "news" / "templates"),
                      autoescape=select_autoescape(["html", "j2"]))
    page = env.get_template("app.html.j2").render(data_json=data_json, version=now.strftime("%Y%m%d%H%M"))
    index = out_dir / "index.html"
    index.write_text(page, encoding="utf-8")

    for f in (ROOT / "static").iterdir():
        if f.is_file():
            shutil.copy(f, out_dir / f.name)

    # Données complètes (utilisées par la notification après déploiement)
    (out_dir / "data.json").write_text(
        json.dumps({"generated": now.isoformat(), "digests": [asdict(d) for d in digests],
                    "quotes": [asdict(q) for q in quotes]}, default=str, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return index
