# -*- coding: utf-8 -*-
"""
WeatherGPT Location Resolver — Phase 1.2
Fuzzy district resolver over data/imd_districts.json using rapidfuzz.
Handles informal names, transliteration (Marathi/Tamil), aliases, and returns nearest 3 if low confidence.

See plan.md 1.2: "Thane" or "Chennai area" -> district_id, <70 confidence triggers clarification.
"""
import json
import pathlib
from typing import Any, Dict, List, Optional

from rapidfuzz import fuzz, process

DATA_PATH = pathlib.Path(__file__).parents[2] / "data" / "imd_districts.json"

# Simple transliteration map for common suffixes/prefixes
TRANSLITERATION_MAP = {
    "mum-bai": "mumbai",
    "bombay": "mumbai",
    "puna": "pune",
    "poona": "pune",
    "madras": "chennai",
    "thana": "thane",
    "tanjore": "thanjavur",
    "nagai": "nagapattinam",
    "rameshwaram": "rameswaram",
}

_districts: Optional[List[Dict[str, Any]]] = None
_choices: Optional[List[str]] = None
_choice_to_district: Optional[Dict[str, Dict[str, Any]]] = None

def _load_districts() -> List[Dict[str, Any]]:
    global _districts
    if _districts is None:
        if not DATA_PATH.exists():
            _districts = []
        else:
            _districts = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return _districts

def _build_choices() -> None:
    global _choices, _choice_to_district
    if _choices is not None:
        return
    districts = _load_districts()
    _choice_to_district = {}
    _choices = []
    for d in districts:
        name = d["district_name"].lower()
        _choices.append(name)
        _choice_to_district[name] = d
        for alias in d.get("aliases", []):
            alias_low = alias.lower()
            if alias_low not in _choice_to_district:
                _choices.append(alias_low)
                _choice_to_district[alias_low] = d

def _normalize(text: str) -> str:
    t = text.strip().lower()
    # remove "district", "area", "creek" noise
    for noise in [" district", " area", " creek", " city"]:
        if t.endswith(noise):
            t = t[: -len(noise)]
    # transliteration
    t = TRANSLITERATION_MAP.get(t, t)
    # also map substring
    for k, v in TRANSLITERATION_MAP.items():
        if k in t:
            t = t.replace(k, v)
    return t.strip()

def fuzzy_match(location_text: str, threshold: int = 70) -> Dict[str, Any]:
    """
    Resolve spoken place to IMD district_id.

    Returns:
      {
        district_id: str|None,
        district_name: str|None,
        state: str|None,
        confidence: int (0-100),
        lat/lon: float|None,
        coastal: bool|None,
        candidates: [{district_id, district_name, confidence}, ...] (up to 3 if low)
        message: str
      }
    """
    if not location_text or not location_text.strip():
        return {"district_id": None, "confidence": 0, "candidates": [], "message": "empty location_text"}

    _build_choices()
    districts = _load_districts()
    if not districts:
        return {"district_id": None, "confidence": 0, "candidates": [], "message": "no district data"}

    query = _normalize(location_text)

    # Use rapidfuzz process.extract with WRatio, limit 5
    results = process.extract(query, _choices, scorer=fuzz.WRatio, limit=5)
    # results: List[(choice, score, index)]
    if not results:
        return {"district_id": None, "confidence": 0, "candidates": [], "message": "no match"}

    # Map to district, keep best score per district (dedupe)
    best_per_district: Dict[str, tuple] = {}  # district_id -> (score, district)
    for choice, score, _idx in results:
        d = _choice_to_district[choice]
        did = d["district_id"]
        if did not in best_per_district or score > best_per_district[did][0]:
            best_per_district[did] = (score, d)

    # Sort by score desc
    sorted_d = sorted(best_per_district.values(), key=lambda x: x[0], reverse=True)
    top_score, top_district = sorted_d[0]

    if top_score >= threshold:
        return {
            "district_id": top_district["district_id"],
            "district_name": top_district["district_name"],
            "state": top_district["state"],
            "confidence": int(top_score),
            "lat": top_district.get("lat"),
            "lon": top_district.get("lon"),
            "coastal": top_district.get("coastal"),
            "candidates": [],
            "message": "resolved",
        }
    # Low confidence: return nearest 3 candidates for clarification
    candidates = [
        {"district_id": d["district_id"], "district_name": d["district_name"], "state": d["state"], "confidence": int(s)}
        for s, d in sorted_d[:3]
    ]
    return {
        "district_id": None,
        "confidence": int(top_score),
        "candidates": candidates,
        "message": f"Did you mean {', '.join(c['district_name'] for c in candidates)}?",
    }

def resolve_location(location_text: str) -> Dict[str, Any]:
    """Alias for MCP tool naming per research.md #6."""
    return fuzzy_match(location_text)

def get_district_by_id(district_id: str) -> Optional[Dict[str, Any]]:
    for d in _load_districts():
        if d["district_id"] == district_id:
            return d
    return None

def all_districts() -> List[Dict[str, Any]]:
    return _load_districts()
