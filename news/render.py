"""Génération de la page HTML statique."""
from __future__ import annotations

import json
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


def french_date(d: datetime) -> str:
    return f"{DAYS[d.weekday()].capitalize()} {d.day} {MONTHS[d.month - 1]} {d.year}"


def sparkline(values: list[float]) -> str:
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = 100 / (len(values) - 1)
    return " ".join(f"{i * step:.1f},{26 - (v - lo) / span * 24:.1f}" for i, v in enumerate(values))


def render(digests: list[CategoryDigest], quotes: list[Quote], now: datetime, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    tz = now.tzinfo
    for d in digests:
        for s in d.stories:
            for a in s.articles:
                a.local_time = a.published.astimezone(tz).strftime("%d/%m à %Hh%M")
    for q in quotes:
        q.spark = sparkline(q.history)

    env = Environment(loader=FileSystemLoader(ROOT / "news" / "templates"), autoescape=select_autoescape())
    page = env.get_template("index.html.j2").render(
        digests=digests,
        quotes=quotes,
        date_long=french_date(now),
        generated_at=now.strftime("%Hh%M"),
        any_ai=any(d.ai_generated for d in digests),
    )
    index = out_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    for f in (ROOT / "static").iterdir():
        shutil.copy(f, out_dir / f.name)
    # Données brutes, utiles pour une autre app ou un archivage
    (out_dir / "data.json").write_text(
        json.dumps({"generated": now.isoformat(), "digests": [asdict(d) for d in digests],
                    "quotes": [asdict(q) for q in quotes]}, default=str, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return index
