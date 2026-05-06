# ARTware — LoRaWAN Middleware Platform

A full-stack IoT middleware that bridges LoRaWAN gateways (with built-in LNS) to downstream applications — Thingsboard, ChirpStack, or any webhook.

## Architecture

```
RAK / Dragino / Milesight Gateway (built-in LNS)
        │  MQTT publish (decoded JSON)
        ▼
  Embedded MQTT Broker (port 1883 / WS 8083)
        │  paho-mqtt subscribe
        ▼
  ARTware Backend (FastAPI)
    ├── Decoder Engine   — 20 built-in profiles + custom
    ├── Forwarder        — Thingsboard / ChirpStack / Webhook
    └── REST API         — CRUD for all resources
        │
  ARTware Frontend (Alpine.js + Tailwind)
    ├── Dashboard        — live uplink feed, stats, chart
    ├── Gateways         — register & monitor gateways
    ├── Devices          — register devices, assign profiles
    ├── Device Profiles  — 20 built-in + custom upload
    ├── Forwarding Rules — per-device or per-profile routing
    └── Admin            — RBAC users, audit log, settings
```

## Quick Start

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Open **http://localhost:8000**

## Demo Credentials

| Role       | Email                   | Password     |
|------------|-------------------------|--------------|
| superadmin | admin@artware.io        | admin123     |
| admin      | manager@artware.io      | manager123   |
| operator   | operator@artware.io     | operator123  |
| viewer     | viewer@artware.io       | viewer123    |

## Connect a Real Gateway

Point your gateway's MQTT integration at this machine:

- **MQTT URL:** `mqtt://<your-laptop-ip>:1883`
- **Auth:** anonymous (no username/password)
- **Topic pattern:** `application/+/device/+/rx`

The device must be registered in the gateway's built-in LNS first.

## Supported Device Profiles

**Dragino:** LHT65, LHT52, LDDS75, LWL01, LDS02, LAT9  
**Milesight:** EM300-TH, AM100, AM300, EM500-CO2, WT201  
**Tektelic:** Comfort, Smart Room, Industrial Tracker  
**Elsys:** ERS, ERS Lite, ELT-2  
**Sensecap:** S2103 (CO₂), S2105 (Soil)  
**Generic:** Passthrough (raw bytes)

## RBAC Roles

| Role       | Gateways | Devices | Rules | Users |
|------------|----------|---------|-------|-------|
| superadmin | ✅ full  | ✅ full | ✅    | ✅    |
| admin      | ✅ full  | ✅ full | ✅    | view  |
| operator   | view     | view    | ✅    | —     |
| viewer     | view     | view    | view  | —     |

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite, paho-mqtt
- **Broker:** amqtt (embedded, port 1883 MQTT / 8083 WebSocket)
- **Frontend:** Alpine.js, Tailwind CSS, Chart.js (CDN, no build step)
- **Auth:** JWT (HS256), bcrypt passwords
