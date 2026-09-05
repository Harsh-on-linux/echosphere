# -*- coding: utf-8 -*-
"""
WeatherGPT User & Vessel Profile Store — Phase 5
Maintains persistent caller memory, farm records, and vessel specifications
for personalized, context-aware voice dialogues.
"""
import time
from typing import Any, Dict, List, Optional

_USERS_DB: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def normalize_phone(phone_number: str) -> str:
    cleaned = str(phone_number).strip().replace(" ", "").replace("-", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def get_or_create_user(
    phone_number: str,
    name: Optional[str] = None,
    persona: str = "farmer",
    preferred_language: str = "hi-IN",
    district: Optional[str] = None,
    tehsil: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve or create user record by phone number (E.164 or national format)."""
    norm_phone = normalize_phone(phone_number)
    if norm_phone in _USERS_DB:
        user = _USERS_DB[norm_phone]
        if name:
            user["name"] = name
        if district:
            user["district"] = district
        if tehsil:
            user["tehsil"] = tehsil
        return user

    user = {
        "phone_number": norm_phone,
        "name": name or f"User-{norm_phone[-4:]}",
        "persona": persona,
        "preferred_language": preferred_language,
        "district": district or "Pune",
        "tehsil": tehsil or "Haveli",
        "created_at": _now(),
        "farmer_details": {
            "crops": [],
            "soil_type": "alluvial",
            "farm_size_acres": 3.5,
        },
        "fisherman_details": {
            "home_port": "Pamban",
            "vessel_type": "motorized_boat",
            "engine_hp": 25,
        }
    }
    _USERS_DB[norm_phone] = user
    return user


def add_farmer_crop(
    phone_number: str,
    crop_name: str,
    growth_stage: str = "vegetative",
    sowing_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Record an active crop for a farmer."""
    user = get_or_create_user(phone_number)
    crop_record = {
        "crop": crop_name.capitalize(),
        "stage": growth_stage,
        "sowing_date": sowing_date or "2026-07-01",
        "updated_at": _now(),
    }
    # Update or append
    crops = user["farmer_details"]["crops"]
    existing = next((c for c in crops if c["crop"].lower() == crop_name.lower()), None)
    if existing:
        existing.update(crop_record)
    else:
        crops.append(crop_record)
    return user


def get_profile_context(phone_number: str) -> Optional[str]:
    """
    Format system prompt context for returning caller, eliminating repetitive questions.
    """
    norm_phone = normalize_phone(phone_number)
    if norm_phone not in _USERS_DB:
        return None

    user = _USERS_DB[norm_phone]
    p = user["persona"]
    name = user.get("name", "Caller")
    loc = f"{user.get('tehsil')}, {user.get('district')}"

    if p == "farmer":
        crops_str = ", ".join(f"{c['crop']} ({c['stage']})" for c in user["farmer_details"]["crops"]) or "None registered"
        return (
            f"Returning Farmer Profile: Name: {name}, Location: {loc}, Language: {user['preferred_language']}. "
            f"Active Crops: {crops_str}. Soil: {user['farmer_details']['soil_type']}. "
            f"Acknowledge their location and crops warmly in your greeting."
        )
    elif p == "fisherman":
        fd = user["fisherman_details"]
        return (
            f"Returning Fisherman Profile: Name: {name}, Port: {fd['home_port']}, Vessel: {fd['vessel_type']} ({fd['engine_hp']} HP). "
            f"Language: {user['preferred_language']}. Check INCOIS wave alerts for their home port."
        )
    return f"Returning User Profile: Name: {name}, Location: {loc}, Persona: {p}."


def clear_user_db() -> None:
    _USERS_DB.clear()
