"""Point d'entrée : python -m news.main [--demo] [--no-notify] [--notify-now]"""
from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import notify
from .fetch import fetch_category
from .render import render
from .sources import CATEGORIES, TICKERS
from .stocks import fetch_quotes, quotes_as_text
from .summarize import build_digest

TZ = ZoneInfo("Europe/Paris")
log = logging.getLogger("news")


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère le digest d'actualités du jour.")
    parser.add_argument("--out", default="site", help="dossier de sortie (défaut : site/)")
    parser.add_argument("--hours", type=int, default=24, help="fenêtre en heures (défaut : 24)")
    parser.add_argument("--demo", action="store_true", help="données fictives, sans réseau")
    parser.add_argument("--no-notify", action="store_true", help="ne pas envoyer de notification")
    parser.add_argument("--notify-now", action="store_true", help="notifier tout de suite au lieu de 8h")
    parser.add_argument("--notify-from", metavar="DATA_JSON",
                        help="envoyer seulement la notification à partir d'un data.json déjà généré")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    now = datetime.now(TZ)
    if args.notify_from:
        digests = notify.digests_from_json(Path(args.notify_from))
        sent = notify.send(digests, os.environ.get("PAGE_URL", ""), now, immediate=args.notify_now)
        raise SystemExit(0 if sent or not os.environ.get("NTFY_TOPIC") else 1)

    since = now - timedelta(hours=args.hours)

    if args.demo:
        from .demo import demo_articles, demo_quotes
        quotes = demo_quotes()
        per_cat = {c["id"]: demo_articles(c["id"], now) for c in CATEGORIES}
    else:
        quotes = fetch_quotes(TICKERS)
        per_cat = {c["id"]: fetch_category(c, since) for c in CATEGORIES}

    digests = []
    for cat in CATEGORIES:
        extra = quotes_as_text(quotes) if cat["id"] == "tech" and quotes else ""
        digests.append(build_digest(cat, per_cat[cat["id"]], extra))

    index = render(digests, quotes, now, Path(args.out))
    log.info("Page générée : %s", index)

    if not args.no_notify:
        notify.send(digests, os.environ.get("PAGE_URL", ""), now, immediate=args.notify_now)


if __name__ == "__main__":
    main()
