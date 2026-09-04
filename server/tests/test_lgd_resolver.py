"""Phase 1.1 tests: All-India LGD administrative gazetteer and tehsil resolution."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import location_resolver


def test_resolve_baramati_tehsil():
    r = location_resolver.fuzzy_match("Baramati")
    assert r["district_id"] == "528"
    assert r["district_name"] == "Pune"
    assert r["tehsil"] == "Baramati"
    assert r["agro_zone"] == "Western Maharashtra Scarcity Zone"
    assert abs(r["lat"] - 18.1517) < 0.01
    assert abs(r["lon"] - 74.5772) < 0.01
    assert r["confidence"] >= 90


def test_resolve_lasalgaon_alias_to_niphad_nashik():
    r = location_resolver.fuzzy_match("Lasalgaon")
    assert r["district_id"] == "516"
    assert r["district_name"] == "Nashik"
    assert r["tehsil"] == "Niphad"
    assert r["confidence"] >= 90


def test_resolve_vedaranyam_coastal_tehsil():
    r = location_resolver.fuzzy_match("Vedaranyam")
    assert r["district_id"] == "468"
    assert r["district_name"] == "Nagapattinam"
    assert r["coastal"] is True
    assert r["tehsil"] == "Vedaranyam"


def test_resolve_paradeep_port_odisha():
    r = location_resolver.fuzzy_match("Paradeep")
    assert r["district_id"] == "118"
    assert r["district_name"] == "Jagatsinghpur"
    assert r["coastal"] is True


def test_resolve_veraval_port_gujarat():
    r = location_resolver.fuzzy_match("Veraval")
    assert r["district_id"] == "315"
    assert r["district_name"] == "Gir Somnath"
    assert r["coastal"] is True


def test_resolve_devanagari_alias():
    r = location_resolver.fuzzy_match("बारामती")
    assert r["district_id"] == "528"
    assert r["tehsil"] == "Baramati"


def test_resolve_karnal_breadbasket():
    r = location_resolver.fuzzy_match("Karnal")
    assert r["district_id"] == "102"
    assert r["state"] == "Haryana"


def test_resolve_with_fallback_preserves_tehsil():
    r = location_resolver.resolve_with_fallback("Baramati")
    assert r["district_id"] == "528"
    assert r["tehsil"] == "Baramati"
    assert r["fallback"] is None
