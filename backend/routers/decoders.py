from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.decoder import DECODER_MAP, decode
import auth as auth_utils

router = APIRouter(prefix="/api/decoders", tags=["decoders"])

DECODER_META = {
    "dragino_lht65":      {"fields": ["temperature", "humidity", "battery"], "example": "857E026D03D6"},
    "dragino_lht52":      {"fields": ["temperature_internal", "temperature_external", "humidity", "battery"], "example": "857E026D026D03D6"},
    "dragino_ldds75":     {"fields": ["distance_mm", "battery"], "example": "857E00F0"},
    "dragino_lwl01":      {"fields": ["water_leak", "battery"], "example": "857E01"},
    "dragino_lds02":      {"fields": ["door_open", "battery"], "example": "857E00"},
    "dragino_lat9":       {"fields": ["latitude", "longitude", "altitude_m"], "example": "0748D19204687A00C8"},
    "milesight_em300_th": {"fields": ["temperature", "humidity", "battery"], "example": "036701150468620175640"},
    "milesight_am100":    {"fields": ["temperature", "humidity", "activity", "illuminance", "co2_ppm"], "example": "0367010A046862"},
    "milesight_am300":    {"fields": ["temperature", "humidity", "battery"], "example": "036701500468640175640"},
    "milesight_em500_co2":{"fields": ["temperature", "humidity", "co2_ppm"], "example": "036701500468640775D007"},
    "milesight_wt201":    {"fields": ["raw_hex"], "example": "0100"},
    "tektelic_comfort":   {"fields": ["raw_hex"], "example": "0100"},
    "tektelic_smart_room":{"fields": ["raw_hex"], "example": "0100"},
    "tektelic_tracker":   {"fields": ["latitude", "longitude", "altitude_m"], "example": "0748D19204687A00C8"},
    "elsys_ers":          {"fields": ["raw_hex"], "example": "0100"},
    "elsys_ers_lite":     {"fields": ["raw_hex"], "example": "0100"},
    "elsys_elt2":         {"fields": ["raw_hex"], "example": "0100"},
    "sensecap_s2103":     {"fields": ["raw_hex"], "example": "0100"},
    "sensecap_s2105":     {"fields": ["raw_hex"], "example": "0100"},
    "passthrough":        {"fields": ["raw_hex", "raw_bytes"], "example": "DEADBEEF"},
}


@router.get("/")
def list_decoders(_=Depends(auth_utils.require_viewer)):
    result = []
    for key in DECODER_MAP:
        meta = DECODER_META.get(key, {"fields": [], "example": "00"})
        result.append({
            "key": key,
            "fields": meta["fields"],
            "example_payload": meta["example"],
        })
    return result


class TestRequest(BaseModel):
    decoder_key: str
    payload_hex: str


@router.post("/test")
def test_decoder(req: TestRequest, _=Depends(auth_utils.require_viewer)):
    if req.decoder_key not in DECODER_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown decoder: {req.decoder_key}")
    payload_hex = req.payload_hex.replace(" ", "").replace("0x", "")
    try:
        result = decode(req.decoder_key, payload_hex)
        return {"ok": True, "decoder_key": req.decoder_key, "payload_hex": payload_hex, "decoded": result}
    except Exception as e:
        return {"ok": False, "error": str(e), "decoded": {}}
