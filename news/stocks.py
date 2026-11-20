"""Cours de bourse via l'API (non officielle) de Yahoo Finance."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from .fetch import USER_AGENT

log = logging.getLogger(__name__)
CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d"


@dataclass
class Quote:
    symbol: str
    name: str
    price: float
    currency: str
    change_1d: float  # en %
    change_5d: float | None
    change_1m: float | None
    history: list[float]  # clôtures du dernier mois, pour le mini-graphique

    @property
    def link(self) -> str:
        return f"https://finance.yahoo.com/quote/{self.symbol}"


def _pct(new: float, old: float | None) -> float | None:
    return None if not old else (new - old) / old * 100


def fetch_quote(symbol: str, name: str) -> Quote | None:
    try:
        resp = requests.get(CHART_URL.format(symbol=symbol), headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        log.warning("Cours indisponible pour %s : %s", symbol, exc)
        return None

    meta = result["meta"]
    closes = [c for c in result["indicators"]["quote"][0].get("close", []) if c is not None]
    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    if price is None:
        return None
    # La dernière bougie est en général celle de la dernière séance (= cours actuel) :
    # la clôture précédente est alors l'avant-dernière.
    if closes and abs(closes[-1] - price) / price < 1e-6:
        prev = closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose")
    else:
        prev = closes[-1] if closes else meta.get("chartPreviousClose")
    return Quote(
        symbol=symbol,
        name=name,
        price=price,
        currency=meta.get("currency", ""),
        change_1d=_pct(price, prev) or 0.0,
        change_5d=_pct(price, closes[-6]) if len(closes) >= 6 else None,
        change_1m=_pct(price, closes[0]) if closes else None,
        history=closes[-22:],
    )


def fetch_quotes(tickers: list[tuple[str, str]]) -> list[Quote]:
    quotes = [fetch_quote(sym, name) for sym, name in tickers]
    return [q for q in quotes if q]


def quotes_as_text(quotes: list[Quote]) -> str:
    """Résumé texte des cours, transmis à Claude pour contextualiser la rubrique Tech."""
    return "\n".join(
        f"{q.name} ({q.symbol}) : {q.price:.2f} {q.currency}, {q.change_1d:+.2f}% sur 1 jour"
        + (f", {q.change_5d:+.2f}% sur 5 jours" if q.change_5d is not None else "")
        for q in quotes
    )
