"""Notification push via ntfy (https://ntfy.sh) — app gratuite Android / iOS.

On s'abonne dans l'app ntfy au « topic » choisi (NTFY_TOPIC). Le message est
envoyé avec une livraison programmée à 8h00 (heure de Paris) : même si le
calcul du digest se termine à 6h, le téléphone sonne à 8h pile.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace

import requests

from .summarize import CategoryDigest

log = logging.getLogger(__name__)


def delivery_timestamp(now: datetime, hour: int = 8) -> int | None:
    """Timestamp Unix de la prochaine 8h00 locale du jour, ou None si déjà passée."""
    target = datetime.combine(now.date(), time(hour), tzinfo=now.tzinfo)
    if target - now < timedelta(seconds=30):
        return None  # trop tard : envoi immédiat
    return int(target.timestamp())


def digests_from_json(path: Path) -> list[SimpleNamespace]:
    """Relit le data.json produit par render() (pour notifier après le déploiement)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        SimpleNamespace(title=d["title"], emoji=d["emoji"],
                        stories=[SimpleNamespace(title=s["title"]) for s in d["stories"]])
        for d in data["digests"]
    ]


def build_message(digests: list[CategoryDigest] | list[SimpleNamespace]) -> str:
    lines = []
    for d in digests:
        if d.stories:
            lines.append(f"{d.emoji} {d.title} ({len(d.stories)}) — {d.stories[0].title}")
        else:
            lines.append(f"{d.emoji} {d.title} — rien de neuf")
    return "\n".join(lines)


def send(digests: list[CategoryDigest], page_url: str, now: datetime, immediate: bool = False) -> bool:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        log.info("NTFY_TOPIC non défini : pas de notification envoyée.")
        return False
    server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    total = sum(len(d.stories) for d in digests)
    headers = {
        "Title": f"Tes infos du {now.strftime('%d/%m')} — {total} sujets",
        "Tags": "newspaper",
        "Priority": "default",
    }
    if page_url:
        headers["Click"] = page_url
        headers["Actions"] = f"view, Ouvrir, {page_url}"
    at = None if immediate else delivery_timestamp(now)
    if at:
        headers["At"] = str(at)
    if os.environ.get("NTFY_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['NTFY_TOKEN']}"

    # En-têtes HTTP non-ASCII (accents, tirets) : encodage RFC 2047, que ntfy sait décoder
    headers = {k: _encode_header(v) for k, v in headers.items()}
    try:
        resp = requests.post(f"{server}/{topic}", data=build_message(digests).encode("utf-8"),
                             headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Échec de l'envoi de la notification : %s", exc)
        return False
    log.info("Notification %s.", "programmée pour 8h00" if at else "envoyée")
    return True


def _encode_header(value: str) -> str:
    try:
        value.encode("ascii")
        return value
    except UnicodeEncodeError:
        import base64
        return "=?UTF-8?B?" + base64.b64encode(value.encode("utf-8")).decode() + "?="
