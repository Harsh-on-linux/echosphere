# -*- coding: utf-8 -*-
"""
VaayuMitra Agro-Advisory Engine — Phase 2.2
Translates raw meteorological variables (rainfall, humidity, wind, temperature)
into actionable agronomic guidance based on ICAR / Krishi Vigyan Kendra (KVK) guidelines.

Supports major Indian cash & food crops: Cotton, Soybean, Onion, Rice/Paddy, Wheat, Tomato, Sugarcane.
"""
import time
from typing import Any, Dict, Optional

# Crop-specific vulnerabilities and action thresholds
CROP_RULES: Dict[str, Dict[str, Any]] = {
    "cotton": {
        "heavy_rain_risk": "Waterlogging causes root rot and flower shedding. Open drainage channels immediately.",
        "pesticide_rule": "Avoid spraying if rainfall is expected within 24 hours. Wait for dry canopy.",
        "pest_risk_condition": lambda rh, temp: rh > 75 and temp > 28,
        "pest_risk_msg": "High humidity & warm weather favor Whitefly and Bollworm infestation. Scout fields regularly."
    },
    "onion": {
        "heavy_rain_risk": "Standing water causes bulb rot and purple blotch. Ensure rapid drainage.",
        "pesticide_rule": "Do not spray fungicide before rain. Postpone until leaves dry.",
        "pest_risk_condition": lambda rh, temp: rh > 80 and 20 <= temp <= 30,
        "pest_risk_msg": "Cloudy weather with high humidity creates favorable conditions for Purple Blotch & Stemphylium blight."
    },
    "paddy": {
        "heavy_rain_risk": "Submergence during flowering stage damages panicles. Maintain water level below 5 cm.",
        "pesticide_rule": "Postpone urea top-dressing before heavy showers to prevent nutrient runoff.",
        "pest_risk_condition": lambda rh, temp: rh > 85 and temp >= 25,
        "pest_risk_msg": "High relative humidity promotes Brown Planthopper (BPH) and Bacterial Leaf Blight."
    },
    "wheat": {
        "heavy_rain_risk": "Lodging risk if accompanied by gusty winds during grain filling stage.",
        "pesticide_rule": "Spray weedicide only on calm, sunny mornings.",
        "pest_risk_condition": lambda rh, temp: rh > 70 and temp > 25,
        "pest_risk_msg": "Unseasonal warm humid weather increases risk of Yellow and Brown Rust."
    },
    "soybean": {
        "heavy_rain_risk": "Waterlogging during germination and pod filling severely reduces yield.",
        "pesticide_rule": "Hold off on insecticide spraying if rain is forecast within 48 hours.",
        "pest_risk_condition": lambda rh, temp: rh > 80,
        "pest_risk_msg": "Humid conditions favor Girdle Beetle and Spodoptera caterpillar outbreak."
    },
    "general": {
        "heavy_rain_risk": "Ensure proper drainage in crop fields to prevent standing water.",
        "pesticide_rule": "Postpone all pesticide and fertilizer spraying if rain is anticipated.",
        "pest_risk_condition": lambda rh, temp: rh > 80,
        "pest_risk_msg": "High humidity conditions favor fungal proliferation. Inspect crop canopy."
    }
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalize_crop(crop: str) -> str:
    c = (crop or "").strip().lower()
    for known in ["cotton", "onion", "paddy", "wheat", "soybean"]:
        if known in c:
            return known
    if "rice" in c:
        return "paddy"
    if "pyaaz" in c or "kanda" in c:
        return "onion"
    if "kapas" in c:
        return "cotton"
    return "general"


def evaluate_agro_advisory_sync(
    crop: str,
    district_or_location: str,
    rainfall_mm: float = 0.0,
    humidity_percent: float = 65.0,
    temp_max: float = 30.0,
    temp_min: float = 20.0,
    wind_kmh: float = 12.0,
    growth_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate actionable agro-meteorological advisory.
    Takes weather indices and crop type to return practical farming guidance.
    """
    crop_key = _normalize_crop(crop)
    rules = CROP_RULES.get(crop_key, CROP_RULES["general"])

    actions = []
    warnings = []
    spraying_safe = True

    # 1. Rainfall evaluation
    if rainfall_mm >= 30.0:
        spraying_safe = False
        warnings.append("HEAVY RAINFALL WARNING: High risk of waterlogging and nutrient leaching.")
        actions.append(rules["heavy_rain_risk"])
        actions.append("Postpone nitrogen/urea top-dressing and chemical application.")
    elif rainfall_mm >= 10.0:
        spraying_safe = False
        warnings.append("MODERATE RAINFALL EXPECTED: Surface soil will be wet.")
        actions.append(rules["pesticide_rule"])
    else:
        if temp_max >= 35.0:
            actions.append("High temperature with low moisture: provide light evening irrigation.")
        else:
            actions.append("Soil moisture conditions normal for routine inter-culture operations.")

    # 2. Wind evaluation
    if wind_kmh >= 30.0:
        spraying_safe = False
        warnings.append(f"GUSTY WINDS ({wind_kmh:.0f} km/h): Risk of spray drift and crop lodging.")
        actions.append("Postpone foliar sprays to prevent chemical drift. Secure tall crops and polyhouses.")

    # 3. Pest & Disease risk via Humidity + Temperature
    avg_temp = (temp_max + temp_min) / 2.0
    if rules["pest_risk_condition"](humidity_percent, avg_temp):
        warnings.append(rules["pest_risk_msg"])
        actions.append("Scout fields for early symptoms; prepare neem-based biopesticide if needed.")

    # 4. Temperature extremes
    if temp_min <= 5.0:
        warnings.append("COLD WAVE / FROST HAZARD: Low temperatures may cause crop damage.")
        actions.append("Apply light evening irrigation or mulch to protect root zone from frost.")

    stage_note = f" (Growth Stage: {growth_stage})" if growth_stage else ""

    return {
        "status": "success",
        "source": "ICAR-KVK Agro-Advisory Decision Support System",
        "cached_at": _now(),
        "crop": crop.capitalize(),
        "location": district_or_location,
        "growth_stage": growth_stage,
        "weather_summary": {
            "expected_rain_mm": rainfall_mm,
            "relative_humidity": humidity_percent,
            "temp_range_c": f"{temp_min:.1f} - {temp_max:.1f}",
            "wind_speed_kmh": wind_kmh,
        },
        "spraying_advisable": spraying_safe,
        "warnings": warnings,
        "recommended_actions": actions,
        "message": f"Agro-advisory for {crop.capitalize()}{stage_note}: Spraying {'PERMITTED' if spraying_safe else 'NOT RECOMMENDED'}. {actions[0] if actions else ''}",
    }


async def evaluate_agro_advisory(
    crop: str,
    district_or_location: str,
    rainfall_mm: float = 0.0,
    humidity_percent: float = 65.0,
    temp_max: float = 30.0,
    temp_min: float = 20.0,
    wind_kmh: float = 12.0,
    growth_stage: Optional[str] = None,
) -> Dict[str, Any]:
    return evaluate_agro_advisory_sync(
        crop=crop,
        district_or_location=district_or_location,
        rainfall_mm=rainfall_mm,
        humidity_percent=humidity_percent,
        temp_max=temp_max,
        temp_min=temp_min,
        wind_kmh=wind_kmh,
        growth_stage=growth_stage,
    )


generate_agro_advisory = evaluate_agro_advisory_sync
