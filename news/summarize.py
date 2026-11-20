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


# --------------------------------------------------------------------------- #
# Mode sans IA
# --------------------------------------------------------------------------- #
STOPWORDS = set(
    "les des une un le la de du et en au aux pour par sur avec dans est qui que "
    "son ses sa ce cette ces plus pas the and for with from that this are has "
    "have will its into after over new what how why".split()
)


def _tokens(title: str) -> set[str]:
    return {w for w in normalize_title(title).split() if len(w) > 3 and w not in STOPWORDS}


def _shorten(text: str, limit: int = 320) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "…"


def cluster_locally(articles: list[Article], max_stories: int) -> list[Story]:
    clusters: list[tuple[set[str], list[Article]]] = []
    for art in articles:
        toks = _tokens(art.title)
        for ctoks, members in clusters:
            if toks and ctoks and len(toks & ctoks) / len(toks | ctoks) >= 0.3:
                members.append(art)
                ctoks |= toks
                break
        else:
            clusters.append((toks, [art]))

    # Les sujets repris par plusieurs journaux d'abord, puis les plus récents
    clusters.sort(key=lambda c: (len({a.source for a in c[1]}), c[1][0].published), reverse=True)
    stories = []
    for _, members in clusters[:max_stories]:
        lead = max(members, key=lambda a: len(a.summary))
        summary = _shorten(lead.summary) if lead.summary else "Pas de résumé fourni par la source."
        stories.append(Story(title=members[0].title, summary=summary, articles=members))
    return stories


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
        n_sources = len({a.source for a in articles})
        overview = f"{len(articles)} articles de {n_sources} sources sur les dernières 24h."
    return CategoryDigest(
        id=category["id"], title=category["title"], emoji=category["emoji"],
        overview=overview, stories=stories, article_count=len(articles), ai_generated=ai,
    )

