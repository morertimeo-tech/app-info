"""Données fictives pour tester la mise en page sans réseau (--demo).

Tout ici est inventé : seuls les noms de sources servent à rendre l'aperçu crédible.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from .fetch import Article
from .stocks import Quote

# (source, titre, chapô)
_SAMPLES = {
    "politique": [
        ("Le Monde", "Budget 2027 : le gouvernement prêt à recourir au 49.3",
         "Faute de majorité, l'exécutif envisage d'engager sa responsabilité sur le projet de loi de finances dès la semaine prochaine."),
        ("franceinfo", "Projet de loi de finances : vers un nouveau 49.3 à l'Assemblée",
         "Les oppositions menacent de déposer une motion de censure en cas de recours à l'article 49.3."),
        ("Le Figaro", "Municipales 2026 : les alliances se dessinent à gauche",
         "Plusieurs partis négocient des listes communes dans les grandes villes avant la date limite de dépôt."),
        ("Libération", "Réforme de l'assurance chômage : les syndicats appellent à manifester",
         "Une journée de mobilisation est prévue le 3 décembre dans toute la France."),
        ("20 Minutes", "Sondage : la cote de confiance de l'exécutif recule de trois points",
         "Le baromètre mensuel enregistre un nouveau recul, notamment chez les moins de 35 ans."),
    ],
    "gaming": [
        ("IGN", "A major studio reveals its next open-world RPG",
         "The first trailer shows a sprawling fantasy world and a release window set for late 2027."),
        ("Jeuxvideo.com", "Un grand studio dévoile son prochain RPG en monde ouvert",
         "La bande-annonce, diffusée mardi soir, annonce une sortie fin 2027 sur PC et consoles."),
        ("Gamekult", "Le marché français du jeu vidéo progresse de 8 % sur un an",
         "Portées par les sorties de fin d'année, les ventes de jeux physiques et dématérialisés sont en hausse."),
        ("Eurogamer", "Popular indie roguelike gets surprise console release",
         "The game is available today on all major consoles after topping PC charts."),
        ("The Verge", "Cloud gaming service adds 20 titles to its catalog",
         "Subscribers get access to several recent releases at no extra cost."),
    ],
    "minecraft-valorant": [
        ("Minecraft.net", "Minecraft : nouvelle snapshot avec blocs décoratifs et nouveaux mobs",
         "La snapshot de la semaine ajoute des blocs décoratifs, un mob passif et corrige une quarantaine de bugs."),
        ("Dexerto", "Valorant patch notes: duelist nerfs and map pool update",
         "Riot adjusts two duelists and rotates one map out of competitive play."),
        ("Millenium", "VCT : le calendrier de la prochaine saison dévoilé",
         "Riot Games a publié les dates des tournois internationaux de la saison à venir."),
    ],
    "tech": [
        ("Les Echos", "Nvidia publie des résultats record portés par l'IA",
         "Le chiffre d'affaires trimestriel dépasse les attentes, tiré par la demande de puces pour centres de données."),
        ("CNBC", "Nvidia beats estimates as data center revenue surges",
         "Shares rose in after-hours trading after the company raised its guidance."),
        ("The Verge", "Microsoft brings new AI agents to Office apps",
         "The update lets Copilot run multi-step tasks across Word, Excel and Outlook."),
        ("TechCrunch", "Google unveils a new Gemini model for developers",
         "The model is available through the API with lower prices than the previous generation."),
        ("Numerama", "IA : l'Union européenne précise ses règles pour les grands modèles",
         "La Commission publie de nouvelles lignes directrices sur la transparence des modèles d'IA."),
    ],
}

# Sujets regroupés dans la démo : (indices des articles, indice de l'article « principal » en français)
_GROUPS = {"politique": [([0, 1], 0)], "gaming": [([0, 1], 1)], "tech": [([0, 1], 0)]}

_OVERVIEWS = {
    "politique": "Le budget domine l'actualité : l'exécutif se prépare à un 49.3, les oppositions brandissent la censure.",
    "gaming": "Un RPG très attendu se dévoile, et le marché français reste bien orienté en fin d'année.",
    "minecraft-valorant": "Nouvelle snapshot côté Minecraft, équilibrage des duellistes et calendrier esport côté Valorant.",
    "tech": "Nvidia signe un nouveau record grâce à l'IA ; Microsoft et Google accélèrent sur les assistants.",
}


def demo_articles(category: str, now: datetime) -> list[Article]:
    arts = []
    for i, (src, title, summary) in enumerate(_SAMPLES.get(category, [])):
        arts.append(Article(id=f"{category}-{i}", title=title, link=f"https://example.com/{category}/{i}",
                            source=src, published=now - timedelta(hours=i * 2 + 1), summary=summary,
                            category=category))
    return arts


def demo_digest(category: dict, now: datetime):
    """Digest « idéal » (comme le produirait Claude) pour juger la mise en page."""
    from .summarize import CategoryDigest, Story
    arts = demo_articles(category["id"], now)
    used, stories = set(), []
    for indices, lead in _GROUPS.get(category["id"], []):
        used.update(indices)
        lead_art = arts[lead]
        others = " ".join(arts[i].summary for i in indices if i != lead and not arts[i].summary.isascii())
        stories.append(Story(title=lead_art.title, summary=f"{lead_art.summary} {others}".strip(),
                             articles=[arts[i] for i in indices]))
    stories += [Story(title=a.title, summary=a.summary, articles=[a]) for i, a in enumerate(arts) if i not in used]
    return CategoryDigest(
        id=category["id"], title=category["title"], emoji=category["emoji"],
        overview=_OVERVIEWS.get(category["id"], ""), stories=stories, article_count=len(arts),
        ai_generated=True, short=category["short"], color=category["color"], tagline=category["tagline"],
    )


def demo_quotes() -> list[Quote]:
    specs = [("NVDA", "Nvidia", "USD", 182.0, 1), ("MSFT", "Microsoft", "USD", 512.0, -1),
             ("GOOGL", "Alphabet", "USD", 268.0, 1), ("AAPL", "Apple", "USD", 241.0, 1),
             ("META", "Meta", "USD", 702.0, -1), ("^FCHI", "CAC 40", "EUR", 8120.0, 1)]
    out = []
    for i, (sym, name, cur, base, trend) in enumerate(specs):
        hist = [base * (1 + 0.02 * math.sin(j / 2.5 + i) + trend * 0.003 * j) for j in range(22)]
        out.append(Quote(sym, name, hist[-1], cur, (hist[-1] - hist[-2]) / hist[-2] * 100,
                         (hist[-1] - hist[-6]) / hist[-6] * 100, (hist[-1] - hist[0]) / hist[0] * 100, hist))
    return out
