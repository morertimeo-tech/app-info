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
