"""Génération du site statique : accueil + une page par catégorie."""
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
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


def greeting(d: datetime) -> str:
    return "Bonsoir" if d.hour >= 18 else "Bonjour"


def format_price(value: float, currency: str) -> str:
    """1234.5 → « 1 234,50 $ » (format français, espaces insécables)."""
    num = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    symbol = CURRENCY.get(currency, currency)
    return f"{num} {symbol}" if symbol else num


def pct(value: float, decimals: int = 2) -> str:
    """+1.234 → « +1,23 % » (virgule décimale, espace insécable)."""
    return f"{value:+.{decimals}f}".replace(".", ",").replace("-", "−") + " %"


def sparkline(values: list[float]) -> str:
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = 100 / (len(values) - 1)
    return " ".join(f"{i * step:.1f},{25 - (v - lo) / span * 22:.1f}" for i, v in enumerate(values))


def _prepare(digests: list[CategoryDigest], quotes: list[Quote], tz) -> None:
    for d in digests:
        for i, s in enumerate(d.stories):
            s.anchor = f"{d.id}-{i + 1}"
            for a in s.articles:
                a.local_time = a.published.astimezone(tz).strftime("%d/%m à %Hh%M")
    for q in quotes:
        q.spark = sparkline(q.history)
        q.price_fmt = format_price(q.price, q.currency)


def render(digests: list[CategoryDigest], quotes: list[Quote], now: datetime, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    _prepare(digests, quotes, now.tzinfo)

    env = Environment(loader=FileSystemLoader(ROOT / "news" / "templates"),
                      autoescape=select_autoescape(["html", "j2"]))
    env.filters["pct"] = pct
    words = sum(len(s.title.split()) + len(s.summary.split()) for d in digests for s in d.stories)
    sources = {a.source for d in digests for s in d.stories for a in s.articles}
    common = dict(
        digests=digests,
        quotes=quotes,
        date_long=french_date(now),
        date_iso=now.date().isoformat(),
        generated_at=now.strftime("%Hh%M"),
        any_ai=any(d.ai_generated for d in digests),
        version=now.strftime("%Y%m%d%H%M"),
    )

    home = env.get_template("home.html.j2").render(
        **common,
        active="home",
        greeting=greeting(now),
        headlines=[(d, d.stories[0]) for d in digests if d.stories],
        total_stories=sum(len(d.stories) for d in digests),
        total_articles=sum(d.article_count for d in digests),
        total_sources=len(sources),
        reading_minutes=max(1, math.ceil(words / 220)),
    )
    (out_dir / "index.html").write_text(home, encoding="utf-8")

    category_tpl = env.get_template("category.html.j2")
    for i, d in enumerate(digests):
        page = category_tpl.render(**common, active=d.id, d=d, next=digests[(i + 1) % len(digests)])
        (out_dir / f"{d.id}.html").write_text(page, encoding="utf-8")

    for f in (ROOT / "static").iterdir():
        shutil.copy(f, out_dir / f.name)

    # Données brutes (utiles pour la notification ou une autre app)
    (out_dir / "data.json").write_text(
        json.dumps({"generated": now.isoformat(), "digests": [asdict(d) for d in digests],
                    "quotes": [asdict(q) for q in quotes]}, default=str, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return out_dir / "index.html"
