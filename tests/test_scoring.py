from datetime import datetime, timedelta, timezone

from scoring.credibility import (domain_credibility, final_score,
                                 freshness_score)


def test_domain_scores():
    assert domain_credibility("nature.com") == 98
    assert domain_credibility("sub.nature.com") == 98
    assert domain_credibility("cdc.gov") == 100
    assert domain_credibility("randomsite.xyz") == 20
    assert domain_credibility("medium.com") == 60


def test_freshness():
    today = datetime.now(timezone.utc).date().isoformat()
    old = (datetime.now(timezone.utc) - timedelta(days=800)).date().isoformat()
    assert freshness_score(today) == 100
    assert freshness_score(old) == 20
    assert freshness_score("") == 50


def test_final_score_weights():
    assert final_score(100, 100, 100) == 100
    assert final_score(0, 0, 0) == 0
    assert final_score(100, 0, 0) == 45.0
