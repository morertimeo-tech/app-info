"""Regroupement des articles en « sujets » et rédaction des résumés.

Deux modes :
- avec ANTHROPIC_API_KEY : Claude regroupe les articles qui parlent du même
  sujet, choisit les plus importants et rédige un vrai résumé en français ;
- sans clé : regroupement par similarité de titres, et le « résumé » est le
  chapô fourni par le journal (moins bon, mais gratuit).
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from .fetch import Article, normalize_title

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"


@dataclass
class Story:
    title: str
    summary: str
    articles: list[Article] = field(default_factory=list)

    @property
    def sources(self) -> list[str]:
        return sorted({a.source for a in self.articles})


@dataclass
class CategoryDigest:
    id: str
    title: str
    emoji: str
    overview: str
    stories: list[Story]
    article_count: int
    ai_generated: bool
    short: str = ""
    color: str = "#64748b"
    tagline: str = ""


# --------------------------------------------------------------------------- #
# Mode sans IA (gratuit)
# --------------------------------------------------------------------------- #
STOPWORDS = set(
    "les des une un le la de du et en au aux pour par sur avec dans est qui que "
    "son ses sa ce cette ces plus pas mais sont été être fait faire après vers selon "
    "the and for with from that this are has have will its into after over new "
    "what how why your you just now more about here".split()
)
STOPWORDS = {unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode() for w in STOPWORDS}
FRENCH_WORDS = {"le", "la", "les", "des", "du", "une", "est", "pour", "sur", "avec", "dans", "et", "aux", "au", "pas", "qui"}

# Pubs, promos et « bons plans » : inutiles dans une revue de presse
AD_RE = re.compile(
    r"bon(s)? plan|code promo|\bpromo\b|promotion|soldes|black friday|cyber monday|prime day|"
    r"\bdeal(s)?\b|\bsale\b|% de réduction|% off|prix cassé|au meilleur prix|à moins de \d|"
    r"meilleures? offres?|sponsoris|partenariat|concours|giveaway|à gagner",
    re.IGNORECASE,
)
# Fins de chapô ajoutées par les flux (« Lire la suite », « The post … appeared first on … »)
JUNK_RE = re.compile(
    r"(the post .* appeared first on .*|lire la suite.*|continue reading.*|read more.*|\[(…|\.\.\.)\]|\(…\))$",
    re.IGNORECASE,
)


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _tokens(title: str) -> set[str]:
    """Mots significatifs du titre, sans accents et tronqués (dévoile ≈ dévoilé ≈ dévoilent)."""
    title = re.sub(r"\b[cdjlmnst]['’]", "", title, flags=re.IGNORECASE)  # l'Assemblée → Assemblée
    words = _strip_accents(normalize_title(title)).split()
    return {w[:6] for w in words if (len(w) > 3 or w.isdigit()) and w not in STOPWORDS}


def is_french(text: str) -> bool:
    words = set(text.lower().split())
    return len(words & FRENCH_WORDS) >= 2 or bool(re.search(r"[éèêàùçôî]", text.lower()))


def is_ad(article: Article) -> bool:
    return bool(AD_RE.search(article.title))


def clean_summary(text: str) -> str:
    text = JUNK_RE.sub("", text.strip()).strip()
    return text.rstrip(" -–—:")


def _shorten(text: str, limit: int = 320) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "…"


def _same_story(a: set[str], b: set[str]) -> bool:
    """Deux titres parlent du même sujet s'ils partagent assez de mots importants."""
    common = len(a & b)
    return common >= 3 or (common >= 2 and common / min(len(a), len(b)) >= 0.5)


def cluster_locally(articles: list[Article], max_stories: int) -> list[Story]:
    articles = [a for a in articles if not is_ad(a)]
    clusters: list[list[tuple[set[str], Article]]] = []
    for art in articles:
        toks = _tokens(art.title)
        if not toks:
            continue
        for members in clusters:
            if any(_same_story(toks, t) for t, _ in members):
                members.append((toks, art))
                break
        else:
            clusters.append([(toks, art)])

    def rank(members):
        arts = [a for _, a in members]
        return (
            len({a.source for a in arts}),                 # repris par plusieurs journaux
            any(is_french(a.title) for a in arts),         # disponible en français
            max(a.published for a in arts),                # le plus récent
        )

    clusters.sort(key=rank, reverse=True)
    stories = []
    for members in clusters[:max_stories]:
        arts = sorted((a for _, a in members), key=lambda a: a.published, reverse=True)
        french = [a for a in arts if is_french(a.title)]
        title_art = french[0] if french else arts[0]
        with_summary = [a for a in (french or arts) if clean_summary(a.summary)] or \
                       [a for a in arts if clean_summary(a.summary)]
        if with_summary:
            summary = _shorten(clean_summary(max(with_summary, key=lambda a: len(a.summary)).summary))
        else:
            summary = "Le journal ne fournit pas de résumé : ouvre l'article pour le détail."
        stories.append(Story(title=title_art.title, summary=summary, articles=arts))
    return stories


def local_overview(stories: list[Story]) -> str:
    """« L'essentiel » sans IA : le sujet le plus repris, puis les suivants."""
    if not stories:
        return ""
    top = stories[0]
    text = top.title.rstrip(".")
    if len(top.sources) > 1:
        text += f" (repris par {len(top.sources)} journaux)"
    others = [s.title.rstrip(".") for s in stories[1:3]]
    if others:
        text += ". Aussi : " + " ; ".join(others)
    return text + "."


# --------------------------------------------------------------------------- #
# Mode Claude
# --------------------------------------------------------------------------- #
class StoryOut(BaseModel):
    titre: str = Field(description="Titre court et factuel du sujet, en français")
    resume: str = Field(description="Résumé en français, 2 à 4 phrases, factuel")
    article_ids: list[str] = Field(description="Identifiants des articles qui traitent ce sujet")


class DigestOut(BaseModel):
    apercu: str = Field(description="Une ou deux phrases qui résument l'essentiel de la rubrique")
    sujets: list[StoryOut]


SYSTEM_PROMPT = """Tu prépares la revue de presse quotidienne d'un lecteur français.
On te donne les articles parus dans les dernières 24h pour une rubrique.

Ta tâche :
1. Regroupe les articles qui parlent du même événement en un seul sujet.
2. Garde au maximum {max_stories} sujets, classés du plus important au moins important
   (un sujet repris par plusieurs journaux est en général plus important).
   Ignore les articles hors sujet pour la rubrique, les jeux-concours, bons plans et publicités.
3. Pour chaque sujet, écris un résumé en français de 2 à 4 phrases : les faits, les chiffres
   clés, et pourquoi c'est important. N'invente rien : appuie-toi uniquement sur le contenu fourni.
   Si l'information est partielle (seulement un titre), reste prudent et le dire si besoin.
4. Indique les identifiants exacts des articles utilisés pour chaque sujet.

Rubrique : {title}"""


def _format_articles(articles: list[Article]) -> str:
    lines = []
    for a in articles:
        when = a.published.strftime("%d/%m %H:%M")
        body = f" — {a.summary[:400]}" if a.summary else ""
        lines.append(f"[{a.id}] ({a.source}, {when} UTC) {a.title}{body}")
    return "\n".join(lines)


def summarize_with_claude(category: dict, articles: list[Article], extra_context: str = "") -> tuple[str, list[Story]] | None:
    try:
        import anthropic
    except ImportError:
        return None

    client = anthropic.Anthropic()
    model = os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
    max_stories = category["max_stories"]
    content = _format_articles(articles[:150])
    if extra_context:
        content += f"\n\nContexte supplémentaire :\n{extra_context}"

    kwargs = dict(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT.format(max_stories=max_stories, title=category["title"]),
        messages=[{"role": "user", "content": content}],
        output_config={"effort": os.environ.get("CLAUDE_EFFORT", "low")},
        output_format=DigestOut,
    )
    # Repli serveur si le modèle refuse : disponible sur Opus 5.5 / Sonnet 5.5 / Fable
    if model in {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2", "claude-fable-5-1", "claude-opus-5"}:
        kwargs.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")

    try:
        response = client.beta.messages.parse(**kwargs)
    except anthropic.APIStatusError as exc:
        log.error("Erreur API Claude (%s) pour %s : %s", exc.status_code, category["id"], exc.message)
        return None
    except anthropic.APIConnectionError as exc:
        log.error("Connexion à l'API Claude impossible : %s", exc)
        return None

    if response.stop_reason == "refusal" or response.parsed_output is None:
        log.warning("Pas de réponse exploitable de Claude pour %s (%s)", category["id"], response.stop_reason)
        return None

    by_id = {a.id: a for a in articles}
    stories = []
    for s in response.parsed_output.sujets[:max_stories]:
        members = [by_id[i] for i in s.article_ids if i in by_id]
        if members:
            stories.append(Story(title=s.titre, summary=s.resume, articles=members))
    log.info("Claude : %s → %d sujets (%d tokens in / %d out)", category["id"], len(stories),
             response.usage.input_tokens, response.usage.output_tokens)
    return response.parsed_output.apercu, stories


def build_digest(category: dict, articles: list[Article], extra_context: str = "") -> CategoryDigest:
    overview, stories, ai = "", [], False
    if not articles:
        overview = "Aucun article trouvé sur les dernières 24h."
    elif os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        result = summarize_with_claude(category, articles, extra_context)
        if result:
            overview, stories = result
            ai = True
    if articles and not stories:
        stories = cluster_locally(articles, category["max_stories"])
        overview = local_overview(stories)
    for s in stories:  # visible dans les journaux GitHub Actions, pour vérifier le tri
        log.info("  [%s] %d source(s) · %s", category["id"], len(s.sources), s.title[:90])
    return CategoryDigest(
        id=category["id"], title=category["title"], emoji=category["emoji"],
        overview=overview, stories=stories, article_count=len(articles), ai_generated=ai,
        short=category.get("short", category["title"]), color=category.get("color", "#64748b"),
        tagline=category.get("tagline", ""),
    )

