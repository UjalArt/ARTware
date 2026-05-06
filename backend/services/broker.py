"""
Embedded MQTT broker using amqtt.
Runs in a dedicated thread with its own asyncio event loop so it
doesn't interfere with FastAPI's uvicorn loop.
Listens on 0.0.0.0:1883 (MQTT) and 0.0.0.0:8083 (WebSocket).
"""
import asyncio
import threading
import logging
from datetime import datetime

logger = logging.getLogger("artware.broker")

# Public stats updated by the broker plugin
broker_stats = {
    "status": "starting",
    "started_at": None,
    "host": "0.0.0.0",
    "mqtt_port": 1883,
    "ws_port": 8083,
    "clients_connected": 0,
    "messages_published": 0,
    "uptime_seconds": 0,
}

BROKER_CONFIG = {
    "listeners": {
        "default": {
            "type": "tcp",
            "bind": "0.0.0.0:1883",
            "max_connections": 200,
        },
        "ws": {
            "type": "ws",
            "bind": "0.0.0.0:8083",
            "max_connections": 50,
        },
    },
    "sys_interval": 10,
    "allow_anonymous": True,
    "auth": {
        "allow-anonymous": True,
        "plugins": [],
    },
    "topic_check": {
        "enabled": False,
    },
}

_broker_loop = None
_broker_thread = None


def _run_broker():
    global _broker_loop
    from amqtt.broker import Broker

    _broker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_broker_loop)

    async def _main():
        broker = Broker(BROKER_CONFIG)
        try:
            await broker.start()
            broker_stats["status"] = "running"
            broker_stats["started_at"] = datetime.utcnow().isoformat() + "Z"
            logger.info("✅ Embedded MQTT broker running on port 1883 (MQTT) / 8083 (WS)")
            # Run until the loop is cancelled
            stop_event = asyncio.Event()
            await stop_event.wait()
        except Exception as e:
            broker_stats["status"] = "error"
            logger.error(f"Broker error: {e}")

    try:
        _broker_loop.run_until_complete(_main())
    except Exception as e:
        broker_stats["status"] = "error"
        logger.error(f"Broker loop error: {e}")


def start_broker():
    global _broker_thread
    _broker_thread = threading.Thread(target=_run_broker, daemon=True, name="mqtt-broker")
    _broker_thread.start()
    logger.info("🚀 Starting embedded MQTT broker thread…")


def get_stats() -> dict:
    if broker_stats["started_at"]:
        started = datetime.fromisoformat(broker_stats["started_at"].replace("Z", ""))
        broker_stats["uptime_seconds"] = int(
            (datetime.utcnow() - started).total_seconds()
        )
    return dict(broker_stats)
