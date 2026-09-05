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
        # Phase 1.1: Index tehsils / talukas for hyper-local sub-district resolution
        for tehsil in d.get("tehsils", []):
            t_name = tehsil["name"].lower()
            t_obj = dict(d)
            t_obj["tehsil"] = tehsil["name"]
            if tehsil.get("lat") is not None and tehsil.get("lon") is not None:
                t_obj["lat"] = tehsil["lat"]
                t_obj["lon"] = tehsil["lon"]
            if t_name not in _choice_to_district:
                _choices.append(t_name)
                _choice_to_district[t_name] = t_obj
            for t_alias in tehsil.get("aliases", []):
                t_alias_low = t_alias.lower()
                if t_alias_low not in _choice_to_district:
                    _choices.append(t_alias_low)
                    _choice_to_district[t_alias_low] = t_obj

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
            "tehsil": top_district.get("tehsil"),
            "agro_zone": top_district.get("agro_zone"),
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


def _detect_state_hint(query: str) -> Optional[str]:
    """Return state name if the query looks state-wide (plan.md 3.4)."""
    districts = _load_districts()
    states = sorted({d["state"].lower() for d in districts if d.get("state")})
    for state in states:
        if state in query:
            # return canonical casing from data
            for d in districts:
                if d.get("state", "").lower() == state:
                    return d["state"]
    return None


def resolve_with_fallback(location_text: str, threshold: int = 70) -> Dict[str, Any]:
    """Resolve + spatial fallback (plan.md 3.4).

    - confidence >= threshold: resolved, fallback=None.
    - confidence < threshold: candidates (top 3) for clarification + nearest
      lat/lon of the best candidate so the caller can retry via
      cityforecast?lat=&lon=. Includes state_hint when the query names a
      state (caller should use subdivision warnings).
    """
    result = fuzzy_match(location_text, threshold=threshold)
    query = (location_text or "").strip().lower()
    state_hint = _detect_state_hint(query)

    if result.get("district_id"):
        result["fallback"] = None
        result["state_hint"] = state_hint
        return result

    # Low confidence: attach nearest lat/lon from best candidate for GPS retry.
    nearest = None
    candidates = result.get("candidates") or []
    if candidates:
        top = get_district_by_id(candidates[0]["district_id"])
        if top and top.get("lat") is not None and top.get("lon") is not None:
            nearest = {"lat": top["lat"], "lon": top["lon"],
                       "district_id": top["district_id"],
                       "district_name": top["district_name"]}
    result["fallback"] = {
        "strategy": "clarify_then_latlon",
        "nearest": nearest,
        "note": "Ask single clarification; on retry use lat/lon fallback.",
    }
    result["state_hint"] = state_hint
    return result

def all_districts() -> List[Dict[str, Any]]:
    return _load_districts()


def find_nearest_location(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Resolve GPS coordinates to nearest district/tehsil."""
    districts = _load_districts()
    if not districts:
        return None
    import math
    best_dist = float("inf")
    best_loc = None
    for d in districts:
        d_lat = d.get("lat")
        d_lon = d.get("lon")
        if d_lat is not None and d_lon is not None:
            dist = math.hypot(lat - d_lat, lon - d_lon)
            if dist < best_dist:
                best_dist = dist
                best_loc = {
                    "district_id": d["district_id"],
                    "district_name": d["district_name"],
                    "state": d["state"],
                    "coastal": d.get("coastal"),
                    "agro_zone": d.get("agro_zone"),
                    "lat": d_lat,
                    "lon": d_lon,
                    "distance_deg": round(dist, 4),
                }
        for t in d.get("tehsils", []):
            t_lat = t.get("lat")
            t_lon = t.get("lon")
            if t_lat is not None and t_lon is not None:
                dist = math.hypot(lat - t_lat, lon - t_lon)
                if dist < best_dist:
                    best_dist = dist
                    best_loc = {
                        "district_id": d["district_id"],
                        "district_name": d["district_name"],
                        "state": d["state"],
                        "tehsil": t["name"],
                        "coastal": d.get("coastal"),
                        "agro_zone": d.get("agro_zone"),
                        "lat": t_lat,
                        "lon": t_lon,
                        "distance_deg": round(dist, 4),
                    }
    return best_loc

