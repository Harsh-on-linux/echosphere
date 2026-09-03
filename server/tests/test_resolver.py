"""Tests for location_resolver fuzzy matching (plan.md 1.2 verification)."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import location_resolver

def test_resolve_pune_exact():
    r = location_resolver.fuzzy_match("Pune")
    assert r["district_id"] == "528"
    assert r["confidence"] >= 90
    assert r["district_name"] == "Pune"

def test_resolve_bombay_alias_to_mumbai():
    r = location_resolver.fuzzy_match("Bombay")
    assert r["district_id"] in ("533", "534")
    assert r["confidence"] >= 85

def test_resolve_mum_bai_transliteration():
    r = location_resolver.fuzzy_match("Mum-bai")
    assert r["district_id"] in ("533", "534")
    assert r["confidence"] >= 80

def test_resolve_thane_creek_noise():
    r = location_resolver.fuzzy_match("Thane Creek")
    assert r["district_id"] == "535"

def test_resolve_chennai_area_noise():
    r = location_resolver.fuzzy_match("Chennai area")
    assert r["district_id"] == "441"

def test_resolve_nagapattinam_tamil():
    r = location_resolver.fuzzy_match("Nagapattinam")
    assert r["district_id"] == "468"
    assert r["coastal"] is True

def test_resolve_low_confidence_returns_candidates():
    r = location_resolver.fuzzy_match("My small village Xyzqwe")
    assert r["district_id"] is None
    assert "candidates" in r
    assert len(r["candidates"]) <= 3

def test_resolve_empty():
    r = location_resolver.fuzzy_match("")
    assert r["district_id"] is None
    assert r["confidence"] == 0

def test_resolve_rameswaram_alias():
    r = location_resolver.fuzzy_match("Rameswaram")
    # Rameswaram vs Rameswaram alias maps to 453
    assert r["district_id"] == "453"

def test_spatial_nearest_candidates_count():
    r = location_resolver.fuzzy_match("Than", threshold=90)
    # "Than" is ambiguous (Thane vs Thanjavur) -> should return candidates with <70 or require high threshold
    if r["district_id"] is None:
        assert len(r["candidates"]) == 3
