"""Données fictives pour tester la mise en page sans réseau (--demo)."""
from __future__ import annotations

from datetime import datetime, timedelta

from .fetch import Article
from .stocks import Quote

_SAMPLES = {
    "politique": [
        ("Le Monde", "Budget 2027 : le gouvernement prêt à recourir au 49.3", "Le Premier ministre a réuni sa majorité mardi soir pour préparer l'adoption du texte."),
        ("franceinfo", "Budget : vers un nouveau 49.3 à l'Assemblée nationale", "L'exécutif n'exclut plus d'engager sa responsabilité sur le projet de loi de finances."),
        ("Le Figaro", "Municipales : les alliances se dessinent à gauche", "Plusieurs partis négocient des listes communes dans les grandes villes."),
    ],
    "gaming": [
        ("IGN", "Big studio announces new open-world RPG", "The trailer was revealed during a livestream on Tuesday."),
        ("Jeuxvideo.com", "Un grand studio dévoile un nouveau RPG en monde ouvert", "La bande-annonce a été diffusée mardi lors d'un live."),
        ("Gamekult", "Les ventes de consoles en hausse en octobre", "Le marché français progresse de 8 % sur un an."),
    ],
    "minecraft-valorant": [
        ("Minecraft.net", "Minecraft Snapshot : nouveaux blocs et mobs", "La dernière snapshot ajoute des blocs décoratifs et corrige 40 bugs."),
        ("Dexerto", "Valorant patch notes: agent balance changes", "Riot nerfs two duelists in the latest patch."),
    ],
    "tech": [
        ("Les Echos", "Nvidia publie des résultats record portés par l'IA", "Le chiffre d'affaires trimestriel dépasse les attentes des analystes."),
        ("CNBC", "Nvidia beats estimates as data center revenue surges", "Shares rose in after-hours trading."),
        ("The Verge", "Microsoft unveils new Copilot features", "The update brings agents to Office apps."),
    ],
}


def demo_articles(category: str, now: datetime) -> list[Article]:
    arts = []
    for i, (src, title, summary) in enumerate(_SAMPLES.get(category, [])):
        arts.append(Article(id=f"{category}-{i}", title=title, link=f"https://example.com/{category}/{i}",
                            source=src, published=now - timedelta(hours=i + 1), summary=summary, category=category))
    return arts


def demo_quotes() -> list[Quote]:
    import math
    out = []
    for i, (sym, name) in enumerate([("NVDA", "Nvidia"), ("MSFT", "Microsoft"), ("^FCHI", "CAC 40")]):
        hist = [100 + 5 * math.sin(j / 3 + i) + (j * (1 if i != 1 else -0.3)) for j in range(22)]
        out.append(Quote(sym, name, hist[-1], "USD" if i < 2 else "EUR",
                         (hist[-1] - hist[-2]) / hist[-2] * 100, (hist[-1] - hist[-6]) / hist[-6] * 100,
                         (hist[-1] - hist[0]) / hist[0] * 100, hist))
    return out
