"""Decoder engine — maps decoder_key to a decode function."""
import struct
from typing import Optional


def decode_dragino_lht65(payload_hex: str) -> dict:
    try:
        b = bytes.fromhex(payload_hex)
        battery = ((b[0] & 0x7F) << 8 | b[1]) / 1000.0
        temp = (b[2] << 8 | b[3])
        if temp > 32767:
            temp -= 65536
        temperature = temp / 100.0
        humidity = (b[4] << 8 | b[5]) / 10.0
        return {"temperature": temperature, "humidity": humidity, "battery": battery}
    except Exception:
        return {"raw": payload_hex}


def decode_dragino_lht52(payload_hex: str) -> dict:
    try:
        b = bytes.fromhex(payload_hex)
        battery = ((b[0] & 0x7F) << 8 | b[1]) / 1000.0
        temp_int = (b[2] << 8 | b[3])
        if temp_int > 32767:
            temp_int -= 65536
        temp_ext = (b[4] << 8 | b[5])
        if temp_ext > 32767:
            temp_ext -= 65536
        humidity = (b[6] << 8 | b[7]) / 10.0
        return {"temperature_internal": temp_int / 100.0, "temperature_external": temp_ext / 100.0,
                "humidity": humidity, "battery": battery}
    except Exception:
        return {"raw": payload_hex}


def decode_dragino_ldds75(payload_hex: str) -> dict:
    try:
        b = bytes.fromhex(payload_hex)
        battery = ((b[0] & 0x7F) << 8 | b[1]) / 1000.0
        distance = (b[2] << 8 | b[3])
        return {"distance_mm": distance, "battery": battery}
    except Exception:
        return {"raw": payload_hex}


def decode_dragino_lwl01(payload_hex: str) -> dict:
    try:
        b = bytes.fromhex(payload_hex)
        battery = ((b[0] & 0x7F) << 8 | b[1]) / 1000.0
        water_leak = bool(b[2] & 0x01)
        return {"water_leak": water_leak, "battery": battery}
    except Exception:
        return {"raw": payload_hex}


def decode_dragino_lds02(payload_hex: str) -> dict:
    try:
        b = bytes.fromhex(payload_hex)
        battery = ((b[0] & 0x7F) << 8 | b[1]) / 1000.0
        door_open = bool(b[2] & 0x01)
        return {"door_open": door_open, "battery": battery}
    except Exception:
        return {"raw": payload_hex}


def decode_dragino_lat9(payload_hex: str) -> dict:
    try:
        b = bytes.fromhex(payload_hex)
        lat = struct.unpack(">i", b[0:4])[0] / 1e7
        lon = struct.unpack(">i", b[4:8])[0] / 1e7
        alt = struct.unpack(">H", b[8:10])[0] / 10.0
        return {"latitude": lat, "longitude": lon, "altitude_m": alt}
    except Exception:
        return {"raw": payload_hex}


def decode_milesight_em300_th(payload_hex: str) -> dict:
    try:
        b = bytes.fromhex(payload_hex)
        idx = 0
        result = {}
        while idx < len(b):
            ch = b[idx]; typ = b[idx + 1]; idx += 2
            if ch == 0x03 and typ == 0x67:
                v = b[idx] | (b[idx + 1] << 8); idx += 2
                if v > 32767: v -= 65536
                result["temperature"] = v / 10.0
            elif ch == 0x04 and typ == 0x68:
                result["humidity"] = b[idx] / 2.0; idx += 1
            elif ch == 0x01 and typ == 0x75:
                result["battery"] = b[idx]; idx += 1
            else:
                break
        return result
    except Exception:
        return {"raw": payload_hex}


def decode_milesight_am100(payload_hex: str) -> dict:
    try:
        b = bytes.fromhex(payload_hex)
        result = {}
        idx = 0
        while idx < len(b) - 1:
            ch = b[idx]; typ = b[idx + 1]; idx += 2
            if ch == 0x03 and typ == 0x67:
                v = b[idx] | (b[idx + 1] << 8); idx += 2
                if v > 32767: v -= 65536
                result["temperature"] = v / 10.0
            elif ch == 0x04 and typ == 0x68:
                result["humidity"] = b[idx] / 2.0; idx += 1
            elif ch == 0x05 and typ == 0x02:
                result["activity"] = b[idx]; idx += 1
            elif ch == 0x06 and typ == 0x65:
                result["illuminance"] = (b[idx] | b[idx + 1] << 8); idx += 2
            elif ch == 0x07 and typ == 0x7D:
                result["co2_ppm"] = (b[idx] | b[idx + 1] << 8); idx += 2
            else:
                break
        return result
    except Exception:
        return {"raw": payload_hex}


def decode_passthrough(payload_hex: str) -> dict:
    return {"raw_hex": payload_hex, "raw_bytes": len(bytes.fromhex(payload_hex)) if payload_hex else 0}


DECODER_MAP = {
    "dragino_lht65": decode_dragino_lht65,
    "dragino_lht52": decode_dragino_lht52,
    "dragino_ldds75": decode_dragino_ldds75,
    "dragino_lwl01": decode_dragino_lwl01,
    "dragino_lds02": decode_dragino_lds02,
    "dragino_lat9": decode_dragino_lat9,
    "milesight_em300_th": decode_milesight_em300_th,
    "milesight_am100": decode_milesight_am100,
    "milesight_am300": decode_milesight_em300_th,   # similar format
    "milesight_em500_co2": decode_milesight_am100,
    "milesight_wt201": decode_passthrough,
    "tektelic_comfort": decode_passthrough,
    "tektelic_smart_room": decode_passthrough,
    "tektelic_tracker": decode_dragino_lat9,
    "elsys_ers": decode_passthrough,
    "elsys_ers_lite": decode_passthrough,
    "elsys_elt2": decode_passthrough,
    "sensecap_s2103": decode_passthrough,
    "sensecap_s2105": decode_passthrough,
    "passthrough": decode_passthrough,
}


def decode(decoder_key: str, payload_hex: str) -> dict:
    fn = DECODER_MAP.get(decoder_key, decode_passthrough)
    return fn(payload_hex)
