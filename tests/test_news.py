"""Tests hors-ligne : python -m pytest -q"""
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import anthropic

from news import notify, summarize
from news.demo import demo_articles
from news.sources import CATEGORIES

TZ = ZoneInfo("Europe/Paris")
CAT = next(c for c in CATEGORIES if c["id"] == "politique")


def test_delivery_is_8am_paris():
    now = datetime(2026, 11, 20, 6, 10, tzinfo=TZ)
    assert datetime.fromtimestamp(notify.delivery_timestamp(now), TZ).hour == 8
    # été (UTC+2) : toujours 8h locale
    summer = datetime(2026, 7, 1, 7, 15, tzinfo=TZ)
    assert datetime.fromtimestamp(notify.delivery_timestamp(summer), TZ).strftime("%H:%M") == "08:00"
    # après 8h : envoi immédiat
    assert notify.delivery_timestamp(datetime(2026, 11, 20, 8, 5, tzinfo=TZ)) is None


def test_local_clustering_groups_same_story():
    now = datetime.now(TZ)
    arts = demo_articles("gaming", now)
    arts.append(summarize.Article(id="x", title="Major studio reveals its next open-world RPG trailer",
                                  link="l", source="Polygon", published=now - timedelta(hours=5)))
    stories = summarize.cluster_locally(arts, 10)
    assert len(stories[0].articles) == 2  # repris par 2 sources -> en tête


def test_claude_output_is_mapped(monkeypatch):
    now = datetime.now(TZ)
    arts = demo_articles("politique", now)
    parsed = summarize.DigestOut(apercu="Journée budgétaire.", sujets=[
        summarize.StoryOut(titre="Vers un 49.3 sur le budget", resume="Résumé.",
                           article_ids=["politique-0", "politique-1", "inconnu"]),
    ])
    captured = {}

    class FakeClient:
        def __init__(self, *a, **k):
            self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

        def parse(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(stop_reason="end_turn", parsed_output=parsed,
                                   usage=SimpleNamespace(input_tokens=1, output_tokens=1))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    digest = summarize.build_digest(CAT, arts)
    assert digest.ai_generated and digest.overview == "Journée budgétaire."
    assert [a.id for a in digest.stories[0].articles] == ["politique-0", "politique-1"]
    assert captured["model"] == "claude-opus-5-5" and captured["fallbacks"] == "default"


def test_refusal_falls_back_to_local(monkeypatch):
    class FakeClient:
        def __init__(self, *a, **k):
            self.beta = SimpleNamespace(messages=SimpleNamespace(
                parse=lambda **kw: SimpleNamespace(stop_reason="refusal", parsed_output=None)))

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    digest = summarize.build_digest(CAT, demo_articles("politique", datetime.now(TZ)))
    assert not digest.ai_generated and digest.stories


def _art(i, title, source, summary="", hours=1):
    return summarize.Article(id=f"t-{i}", title=title, link="https://x", source=source,
                             published=datetime.now(TZ) - timedelta(hours=hours), summary=summary)


def test_free_mode_groups_variants_and_prefers_french():
    arts = [
        _art(0, "A major studio reveals its next open-world RPG", "IGN", "The trailer shows a fantasy world."),
        _art(1, "Un grand studio dévoile son prochain RPG en monde ouvert", "Jeuxvideo.com", "La bande-annonce montre un monde."),
        _art(2, "Budget 2027 : le gouvernement prêt à recourir au 49.3", "Le Monde", "Faute de majorité…"),
        _art(3, "Budget : vers un nouveau 49.3 à l'Assemblée", "franceinfo", ""),
        _art(4, "Bon plan : la PS5 à prix cassé pour le Black Friday", "Dealabs"),
        _art(5, "Le marché du jeu vidéo progresse", "Gamekult", "Hausse de 8 %. Lire la suite"),
    ]
    stories = summarize.cluster_locally(arts, 10)
    titles = [s.title for s in stories]
    assert not any("Bon plan" in t for t in titles)                 # pub filtrée
    budget = next(s for s in stories if "Budget" in s.title)
    assert len(budget.articles) == 2                                  # même sujet regroupé
    market = next(s for s in stories if "marché" in s.title)
    assert "Lire la suite" not in market.summary                      # chapô nettoyé
    assert summarize.local_overview(stories).startswith("Budget")     # sujet le plus repris en tête
