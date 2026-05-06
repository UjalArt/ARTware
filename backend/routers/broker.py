from fastapi import APIRouter, Depends
from services.broker import get_stats
import auth as auth_utils

router = APIRouter(prefix="/api/broker", tags=["broker"])


@router.get("/status")
def broker_status(_=Depends(auth_utils.require_viewer)):
    stats = get_stats()
    return {
        **stats,
        "mqtt_url": f"mqtt://localhost:{stats['mqtt_port']}",
        "ws_url":   f"ws://localhost:{stats['ws_port']}",
        "subscribe_topics": [
            "application/+/device/+/rx",
            "lorawan/#",
            "v3/#",
        ],
        "notes": "Point your gateway MQTT integration at this host on port 1883. Anonymous connections allowed.",
    }
