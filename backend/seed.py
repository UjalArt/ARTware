from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session
import models
from auth import hash_password

DEVICE_PROFILES = [
    # Dragino
    {"name": "Dragino LHT65", "manufacturer": "Dragino", "model": "LHT65",
     "description": "LoRaWAN temperature & humidity sensor with external probe", "decoder_key": "dragino_lht65", "icon": "🌡️"},
    {"name": "Dragino LHT52", "manufacturer": "Dragino", "model": "LHT52",
     "description": "LoRaWAN indoor temperature & humidity sensor", "decoder_key": "dragino_lht52", "icon": "🌡️"},
    {"name": "Dragino LDDS75", "manufacturer": "Dragino", "model": "LDDS75",
     "description": "LoRaWAN distance detection sensor (ultrasonic)", "decoder_key": "dragino_ldds75", "icon": "📏"},
    {"name": "Dragino LWL01", "manufacturer": "Dragino", "model": "LWL01",
     "description": "LoRaWAN water leak sensor", "decoder_key": "dragino_lwl01", "icon": "💧"},
    {"name": "Dragino LDS02", "manufacturer": "Dragino", "model": "LDS02",
     "description": "LoRaWAN door & window open/close sensor", "decoder_key": "dragino_lds02", "icon": "🚪"},
    {"name": "Dragino LAT9", "manufacturer": "Dragino", "model": "LAT9",
     "description": "LoRaWAN asset tracker with GPS", "decoder_key": "dragino_lat9", "icon": "📍"},

    # Milesight
    {"name": "Milesight EM300-TH", "manufacturer": "Milesight", "model": "EM300-TH",
     "description": "Industrial temperature & humidity sensor IP67", "decoder_key": "milesight_em300_th", "icon": "🌡️"},
    {"name": "Milesight AM100", "manufacturer": "Milesight", "model": "AM100",
     "description": "Indoor ambience monitoring — CO₂, temp, humidity, light, PIR", "decoder_key": "milesight_am100", "icon": "🏭"},
    {"name": "Milesight AM300", "manufacturer": "Milesight", "model": "AM300",
     "description": "Smart building ambient sensor with e-ink display", "decoder_key": "milesight_am300", "icon": "🏢"},
    {"name": "Milesight EM500-CO2", "manufacturer": "Milesight", "model": "EM500-CO2",
     "description": "Outdoor/industrial CO₂ & environmental sensor", "decoder_key": "milesight_em500_co2", "icon": "💨"},
    {"name": "Milesight WT201", "manufacturer": "Milesight", "model": "WT201",
     "description": "Smart thermostat with HVAC control", "decoder_key": "milesight_wt201", "icon": "🌀"},

    # Tektelic
    {"name": "Tektelic Comfort", "manufacturer": "Tektelic", "model": "Comfort",
     "description": "Office comfort sensor — temp, humidity, CO₂, occupancy, light", "decoder_key": "tektelic_comfort", "icon": "🏠"},
    {"name": "Tektelic Smart Room", "manufacturer": "Tektelic", "model": "Smart Room",
     "description": "Compact smart room sensor — motion, temp, humidity", "decoder_key": "tektelic_smart_room", "icon": "🏠"},
    {"name": "Tektelic Industrial Tracker", "manufacturer": "Tektelic", "model": "Ag Tracker",
     "description": "Rugged GPS asset tracker", "decoder_key": "tektelic_tracker", "icon": "📍"},

    # Elsys
    {"name": "Elsys ERS", "manufacturer": "Elsys", "model": "ERS",
     "description": "Multi-sensor — temp, humidity, light, motion, CO₂", "decoder_key": "elsys_ers", "icon": "📊"},
    {"name": "Elsys ERS Lite", "manufacturer": "Elsys", "model": "ERS Lite",
     "description": "Compact temp & humidity sensor", "decoder_key": "elsys_ers_lite", "icon": "📊"},
    {"name": "Elsys ELT-2", "manufacturer": "Elsys", "model": "ELT-2",
     "description": "External sensor input with 2 analog/digital ports", "decoder_key": "elsys_elt2", "icon": "🔌"},

    # Sensecap
    {"name": "Sensecap S2103", "manufacturer": "Seeed / Sensecap", "model": "S2103",
     "description": "CO₂, temperature & humidity sensor (IP66)", "decoder_key": "sensecap_s2103", "icon": "💨"},
    {"name": "Sensecap S2105", "manufacturer": "Seeed / Sensecap", "model": "S2105",
     "description": "Soil moisture, temperature & electrical conductivity sensor", "decoder_key": "sensecap_s2105", "icon": "🌱"},

    # Generic
    {"name": "Passthrough (raw)", "manufacturer": "Generic", "model": "Passthrough",
     "description": "No decoding — forward raw bytes as-is to downstream targets", "decoder_key": "passthrough", "icon": "📡"},
]


def seed_database(db: Session):
    # Skip if already seeded
    if db.query(models.User).count() > 0:
        return

    # --- Users ---
    users = [
        models.User(email="admin@artware.io", full_name="Super Admin", role="superadmin",
                    password_hash=hash_password("admin123"), is_active=True),
        models.User(email="manager@artware.io", full_name="Site Manager", role="admin",
                    password_hash=hash_password("manager123"), is_active=True),
        models.User(email="operator@artware.io", full_name="Field Operator", role="operator",
                    password_hash=hash_password("operator123"), is_active=True),
        models.User(email="viewer@artware.io", full_name="Read-Only Viewer", role="viewer",
                    password_hash=hash_password("viewer123"), is_active=True),
    ]
    db.add_all(users)
    db.flush()

    # --- Device Profiles ---
    profiles = []
    for p in DEVICE_PROFILES:
        profile = models.DeviceProfile(**p)
        db.add(profile)
        profiles.append(profile)
    db.flush()

    lht65_profile = profiles[0]  # Dragino LHT65

    # --- Demo Gateway ---
    gateway = models.Gateway(
        name="ARTware Demo Gateway",
        eui="AA555A0000000101",
        model="RAK WisGate Edge Lite 2 (RAK7268)",
        mqtt_topic_pattern="application/+/device/+/rx",
        status="online",
        lat=12.9716,
        lon=77.5946,
        last_seen=datetime.utcnow(),
    )
    db.add(gateway)
    db.flush()

    # --- Demo Device ---
    device = models.Device(
        name="Demo Dragino LHT65 — Warehouse",
        dev_eui="0102030405060708",
        gateway_id=gateway.id,
        profile_id=lht65_profile.id,
        status="online",
        last_seen=datetime.utcnow(),
        last_payload={"temperature": 24.5, "humidity": 62.0, "battery": 3.42},
    )
    db.add(device)
    db.flush()

    # --- Demo Forwarding Rule ---
    rule = models.ForwardingRule(
        name="Demo → Webhook (Test)",
        device_id=device.id,
        target_type="webhook",
        target_url="https://webhook.site/demo-artware",
        target_config={"method": "POST", "headers": {}},
        is_active=True,
    )
    db.add(rule)

    # --- Seed 20 fake uplinks for the demo device ---
    for i in range(20):
        ts = datetime.utcnow() - timedelta(minutes=(20 - i) * 3)
        temp = round(22.0 + random.uniform(-2, 4), 1)
        hum = round(58.0 + random.uniform(-5, 10), 1)
        batt = round(3.3 + random.uniform(0, 0.4), 2)
        uplink = models.UplinkLog(
            device_id=device.id,
            gateway_id=gateway.id,
            dev_eui="0102030405060708",
            rssi=round(-85 + random.uniform(-10, 10), 1),
            snr=round(8.5 + random.uniform(-3, 3), 1),
            payload_raw="0260" + format(int(temp * 100), "04X"),
            payload_decoded={"temperature": temp, "humidity": hum, "battery": batt},
            topic="application/1/device/0102030405060708/rx",
            timestamp=ts,
        )
        db.add(uplink)

    # --- Audit log entry ---
    db.add(models.AuditLog(
        user_email="system",
        action="SEED",
        resource="database",
        details="Initial seed with demo gateway, device and 20 uplinks",
    ))

    db.commit()
    print("✅ Database seeded with demo data")
