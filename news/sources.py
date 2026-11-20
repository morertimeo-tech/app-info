"""Configuration des rubriques : flux RSS, filtres et actions suivies.

Pour ajouter/retirer un journal, il suffit de modifier les listes ci-dessous.
Les flux Google News servent pour les sujets de niche (Minecraft, Valorant)
où les sites officiels ne proposent pas de flux RSS fiable.
"""
from urllib.parse import quote_plus


def google_news(query: str, lang: str = "fr") -> str:
    """Flux RSS Google News pour une recherche, limité aux dernières 24h."""
    region = {"fr": ("fr", "FR", "FR:fr"), "en": ("en-US", "US", "US:en")}[lang]
    hl, gl, ceid = region
    return (
        f"https://news.google.com/rss/search?q={quote_plus(query + ' when:1d')}"
        f"&hl={hl}&gl={gl}&ceid={ceid}"
    )


CATEGORIES = [
    {
        "id": "politique",
        "short": "Politique",
        "color": "#3b6cf6",
        "tagline": "Gouvernement, Assemblée, partis",
        "title": "Politique française",
        "emoji": "🇫🇷",
        "feeds": [
            ("Le Monde", "https://www.lemonde.fr/politique/rss_full.xml"),
            ("franceinfo", "https://www.francetvinfo.fr/politique.rss"),
            ("Le Figaro", "https://www.lefigaro.fr/rss/figaro_politique.xml"),
            ("Libération", "https://www.liberation.fr/arc/outboundfeeds/rss-all/category/politique/?outputType=xml"),
            ("20 Minutes", "https://www.20minutes.fr/feeds/rss-politique.xml"),
            ("Google News", google_news("politique France gouvernement OR Assemblée OR Élysée")),
        ],
        "keywords": None,  # pas de filtre : les flux sont déjà thématiques
        "max_stories": 10,
    },
    {
        "id": "gaming",
        "short": "Gaming",
        "color": "#8b5cf6",
        "tagline": "Sorties, annonces, industrie",
        "title": "Gaming mondial",
        "emoji": "🎮",
        "feeds": [
            ("Jeuxvideo.com", "https://www.jeuxvideo.com/rss/rss.xml"),
            ("Gamekult", "https://www.gamekult.com/feed.xml"),
            ("Millenium", "https://www.millenium.org/rss"),
            ("IGN", "https://feeds.feedburner.com/ign/all"),
            ("Eurogamer", "https://www.eurogamer.net/feed"),
            ("The Verge", "https://www.theverge.com/rss/games/index.xml"),
            ("Polygon", "https://www.polygon.com/rss/index.xml"),
        ],
        "keywords": None,
        "max_stories": 10,
    },
    {
        "id": "minecraft-valorant",
        "short": "MC & Valo",
        "color": "#16a34a",
        "tagline": "Mises à jour, patchs, esport",
        "title": "Minecraft & Valorant",
        "emoji": "⛏️",
        "feeds": [
            ("Minecraft.net", "https://www.minecraft.net/en-us/feeds/community-content/rss"),
            ("Google News", google_news("Minecraft")),
            ("Google News", google_news("Minecraft", "en")),
            ("Google News", google_news("Valorant")),
            ("Google News", google_news("Valorant", "en")),
        ],
        "keywords": ["minecraft", "mojang", "valorant", "riot games", "vct"],
        "max_stories": 8,
    },
    {
        "id": "tech",
        "short": "Tech",
        "color": "#f59e0b",
        "tagline": "Nvidia, Microsoft, Google, IA, bourse",
        "title": "Big Tech, IA & Bourse",
        "emoji": "📈",
        "feeds": [
            ("Les Echos", "https://services.lesechos.fr/rss/les-echos-tech-medias.xml"),
            ("Numerama", "https://www.numerama.com/feed/"),
            ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
            ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
            ("CNBC", "https://www.cnbc.com/id/19854910/device/rss/rss.html"),
            ("Google News", google_news("Nvidia OR Microsoft OR Google OR OpenAI OR Anthropic OR Apple OR Meta")),
            ("Google News", google_news("Nvidia OR Microsoft OR Alphabet stock", "en")),
        ],
        "keywords": [
            "nvidia", "microsoft", "google", "alphabet", "openai", "anthropic", "claude",
            "chatgpt", "gemini", "meta", "apple", "amazon", "tesla", "amd", "intel",
            "mistral", "ia ", "intelligence artificielle", " ai ", "ai,", "a.i.",
            "bourse", "nasdaq", "wall street", "action", "stock", "shares",
        ],
        "max_stories": 10,
    },
]

# Actions et indices suivis (symboles Yahoo Finance)
TICKERS = [
    ("NVDA", "Nvidia"),
    ("MSFT", "Microsoft"),
    ("GOOGL", "Alphabet (Google)"),
    ("AAPL", "Apple"),
    ("META", "Meta"),
    ("AMZN", "Amazon"),
    ("TSLA", "Tesla"),
    ("AMD", "AMD"),
    ("UBI.PA", "Ubisoft"),
    ("^IXIC", "Nasdaq"),
    ("^GSPC", "S&P 500"),
    ("^FCHI", "CAC 40"),
]
