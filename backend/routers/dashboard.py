from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models
import auth as auth_utils

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    total_gateways = db.query(models.Gateway).count()
    online_gateways = db.query(models.Gateway).filter(models.Gateway.status == "online").count()
    total_devices = db.query(models.Device).count()
    online_devices = db.query(models.Device).filter(models.Device.status == "online").count()

    since_1h = datetime.utcnow() - timedelta(hours=1)
    uplinks_1h = db.query(models.UplinkLog).filter(models.UplinkLog.timestamp >= since_1h).count()
    total_uplinks = db.query(models.UplinkLog).count()

    return {
        "total_gateways": total_gateways,
        "online_gateways": online_gateways,
        "total_devices": total_devices,
        "online_devices": online_devices,
        "uplinks_last_hour": uplinks_1h,
        "total_uplinks": total_uplinks,
    }


@router.get("/uplinks/recent")
def get_recent_uplinks(limit: int = 50, db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    logs = (
        db.query(models.UplinkLog)
        .order_by(models.UplinkLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    result = []
    for log in logs:
        device_name = log.device.name if log.device else log.dev_eui
        profile_name = log.device.profile.name if log.device and log.device.profile else "Unknown"
        result.append({
            "id": log.id,
            "dev_eui": log.dev_eui,
            "device_name": device_name,
            "profile_name": profile_name,
            "rssi": log.rssi,
            "snr": log.snr,
            "payload_decoded": log.payload_decoded,
            "timestamp": log.timestamp.isoformat() + "Z",
        })
    return result


@router.get("/gateways/map")
def get_gateway_map(db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    gateways = db.query(models.Gateway).all()
    return [
        {
            "id": gw.id,
            "name": gw.name,
            "eui": gw.eui,
            "model": gw.model,
            "status": gw.status,
            "lat": gw.lat,
            "lon": gw.lon,
            "device_count": len(gw.devices),
            "last_seen": gw.last_seen.isoformat() + "Z" if gw.last_seen else None,
        }
        for gw in gateways
    ]


@router.get("/uplinks/chart")
def get_uplink_chart(db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    """Uplinks per hour for last 12 hours."""
    now = datetime.utcnow()
    labels = []
    counts = []
    for i in range(11, -1, -1):
        hour_start = now - timedelta(hours=i + 1)
        hour_end = now - timedelta(hours=i)
        count = db.query(models.UplinkLog).filter(
            models.UplinkLog.timestamp >= hour_start,
            models.UplinkLog.timestamp < hour_end
        ).count()
        labels.append(hour_start.strftime("%H:%M"))
        counts.append(count)
    return {"labels": labels, "counts": counts}
