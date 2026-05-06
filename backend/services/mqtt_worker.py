"""
Real MQTT uplink worker using paho-mqtt.

Two jobs:
  1. SUBSCRIBER  — subscribes to the embedded broker on port 1883,
                   listens for real gateway uplinks on configured topics,
                   decodes payloads, stores UplinkLog rows.
  2. PUBLISHER   — publishes fake demo-device uplinks every 15 s so the
                   dashboard live-feed has moving data from day one.

Real gateways point to this machine on port 1883 and publish to their
topic pattern (e.g. application/+/device/+/rx).  The subscriber picks
those up exactly like the fake ones.
"""
import json
import random
import threading
import time
import logging
from datetime import datetime

import paho.mqtt.client as mqtt

from database import SessionLocal
import models
from services import broker as broker_svc
from services.decoder import decode

logger = logging.getLogger("artware.worker")

BROKER_HOST = "localhost"
BROKER_PORT = 1883
DEMO_DEV_EUI = "0102030405060708"
DEMO_GW_EUI  = "AA555A0000000101"
DEMO_TOPIC   = f"application/1/device/{DEMO_DEV_EUI}/rx"
SUBSCRIBE_PATTERNS = [
    "application/#",
    "lorawan/#",
    "v3/#",        # TTN-style
]


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _extract_dev_eui(topic: str, payload: dict) -> str | None:
    """Try to pull DevEUI from the decoded JSON payload or from the topic."""
    for key in ("devEUI", "dev_eui", "deviceInfo", "DevEui"):
        if key in payload:
            v = payload[key]
            if isinstance(v, dict):
                v = v.get("devEui") or v.get("devEUI") or ""
            return str(v)
    # Fall back: extract from topic segments
    parts = topic.split("/")
    for i, p in enumerate(parts):
        if p in ("device", "devices") and i + 1 < len(parts):
            return parts[i + 1]
    return None


def _handle_uplink(topic: str, raw: bytes, db):
    try:
        payload_json = json.loads(raw.decode())
    except Exception:
        payload_json = {"raw": raw.hex()}

    dev_eui = _extract_dev_eui(topic, payload_json)

    # RAK / generic format: payload is in "data" (base64) or "payload" (hex)
    payload_hex = None
    data_b64 = payload_json.get("data") or payload_json.get("payload_raw")
    if data_b64:
        try:
            import base64
            payload_hex = base64.b64decode(data_b64).hex()
        except Exception:
            payload_hex = data_b64  # already hex maybe
    if not payload_hex:
        payload_hex = payload_json.get("payload_decoded_hex", "")

    # Look up device
    device = None
    gateway = None
    decoded = {}

    if dev_eui:
        device = db.query(models.Device).filter(models.Device.dev_eui == dev_eui).first()
    if device:
        gateway = device.gateway
        decoder_key = (device.profile.decoder_key if device.profile else "passthrough") or "passthrough"
        if payload_hex:
            decoded = decode(decoder_key, payload_hex)
        else:
            # payload already decoded by gateway
            decoded = payload_json.get("payload_decoded") or payload_json.get("object") or {}

    rssi = (payload_json.get("rxInfo", [{}])[0].get("rssi") if "rxInfo" in payload_json else None) or \
           payload_json.get("rssi") or payload_json.get("signal")
    snr  = (payload_json.get("rxInfo", [{}])[0].get("loRaSNR") if "rxInfo" in payload_json else None) or \
           payload_json.get("snr")

    uplink = models.UplinkLog(
        device_id=device.id if device else None,
        gateway_id=gateway.id if gateway else None,
        dev_eui=dev_eui or "unknown",
        rssi=rssi,
        snr=snr,
        payload_raw=payload_hex or raw.hex(),
        payload_decoded=decoded or payload_json,
        topic=topic,
        timestamp=datetime.utcnow(),
    )
    db.add(uplink)

    if device:
        device.last_seen   = datetime.utcnow()
        device.status      = "online"
        device.last_payload = decoded or {}
    if gateway:
        gateway.last_seen = datetime.utcnow()
        gateway.status    = "online"

    # Update broker message counter
    broker_svc.broker_stats["messages_published"] += 1

    db.commit()
    logger.debug(f"Uplink stored: {dev_eui} on {topic}")


# ─────────────────────────────────────────────────────────────────────
# Subscriber thread
# ─────────────────────────────────────────────────────────────────────

def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("✅ MQTT worker connected to embedded broker")
        for pattern in SUBSCRIBE_PATTERNS:
            client.subscribe(pattern)
            logger.info(f"   Subscribed to: {pattern}")
    else:
        logger.warning(f"MQTT connect failed: rc={rc}")


def _on_message(client, userdata, msg):
    db = SessionLocal()
    try:
        _handle_uplink(msg.topic, msg.payload, db)
    except Exception as e:
        logger.error(f"on_message error: {e}")
        db.rollback()
    finally:
        db.close()


def _subscriber_loop():
    """Connects to the embedded broker and processes real uplinks."""
    # Wait for broker to start
    time.sleep(4)

    client = mqtt.Client(client_id="artware-worker")
    client.on_connect = _on_connect
    client.on_message = _on_message

    while True:
        try:
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            client.loop_forever()
        except Exception as e:
            logger.warning(f"Subscriber disconnected ({e}), retrying in 5s…")
            time.sleep(5)


# ─────────────────────────────────────────────────────────────────────
# Demo publisher thread
# ─────────────────────────────────────────────────────────────────────

def _make_demo_payload() -> dict:
    temp = round(20.0 + random.uniform(-3, 8), 1)
    hum  = round(55.0 + random.uniform(-10, 20), 1)
    batt = round(3.1  + random.uniform(0, 0.6), 2)
    rssi = round(-80  + random.uniform(-15, 10), 1)
    snr  = round(9.0  + random.uniform(-4, 4), 1)
    return {
        "devEUI": DEMO_DEV_EUI,
        "rssi": rssi,
        "snr": snr,
        "payload_decoded": {"temperature": temp, "humidity": hum, "battery": batt},
        "object": {"temperature": temp, "humidity": hum, "battery": batt},
        "gwEUI": DEMO_GW_EUI,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def _publisher_loop():
    """Publishes a fake demo uplink every 15 s via the real broker."""
    # Wait for broker + subscriber to be ready
    time.sleep(8)

    pub = mqtt.Client(client_id="artware-demo-gw")
    while True:
        try:
            pub.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            pub.loop_start()
            logger.info("✅ Demo gateway publisher connected")
            while True:
                payload = _make_demo_payload()
                pub.publish(DEMO_TOPIC, json.dumps(payload), qos=1)
                logger.debug(f"Published demo uplink → {DEMO_TOPIC}")
                time.sleep(15)
        except Exception as e:
            logger.warning(f"Publisher error ({e}), retrying in 5s…")
            try:
                pub.loop_stop()
                pub.disconnect()
            except Exception:
                pass
            time.sleep(5)


# ─────────────────────────────────────────────────────────────────────
# Public start function
# ─────────────────────────────────────────────────────────────────────

def start_worker():
    sub = threading.Thread(target=_subscriber_loop, daemon=True, name="mqtt-subscriber")
    pub = threading.Thread(target=_publisher_loop,  daemon=True, name="mqtt-publisher")
    sub.start()
    pub.start()
    logger.info("🚀 MQTT subscriber + demo publisher threads started")
