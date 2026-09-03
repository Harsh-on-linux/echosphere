# WeatherGPT Location Resolver — Phase 1.2 stub
# Fuzzy district resolver over data/imd_districts.json using rapidfuzz
# See plan.md 1.2: handle Marathi/Tamil transliteration + aliases, return nearest 3 if confidence <70

"""
Placeholder. Real resolver in Phase 1.2:
- load data/imd_districts.json
- rapidfuzz fuzz.WRatio on district_name + aliases
- lat/lon fallback via Nominatim if not found
"""

import json
import pathlib

DATA_PATH = pathlib.Path(__file__).parents[2] / "data" / "imd_districts.json"

def fuzzy_match(location_text: str) -> dict:
    """TODO: implement"""
    return {"district_id": None, "confidence": 0, "message": "stub — implement in 1.2"}
