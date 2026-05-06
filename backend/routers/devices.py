from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
import auth as auth_utils

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceCreate(BaseModel):
    name: str
    dev_eui: str
    gateway_id: Optional[int] = None
    profile_id: Optional[int] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    gateway_id: Optional[int] = None
    profile_id: Optional[int] = None
    status: Optional[str] = None


def device_to_dict(d: models.Device):
    return {
        "id": d.id,
        "name": d.name,
        "dev_eui": d.dev_eui,
        "gateway_id": d.gateway_id,
        "gateway_name": d.gateway.name if d.gateway else None,
        "profile_id": d.profile_id,
        "profile_name": d.profile.name if d.profile else None,
        "profile_icon": d.profile.icon if d.profile else "📡",
        "manufacturer": d.profile.manufacturer if d.profile else None,
        "status": d.status,
        "last_seen": d.last_seen.isoformat() + "Z" if d.last_seen else None,
        "last_payload": d.last_payload,
        "created_at": d.created_at.isoformat() + "Z",
    }


@router.get("/")
def list_devices(db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    return [device_to_dict(d) for d in db.query(models.Device).all()]


@router.get("/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    d = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    return device_to_dict(d)


@router.get("/{device_id}/uplinks")
def get_device_uplinks(device_id: int, limit: int = 50, db: Session = Depends(get_db),
                        _=Depends(auth_utils.require_viewer)):
    logs = (
        db.query(models.UplinkLog)
        .filter(models.UplinkLog.device_id == device_id)
        .order_by(models.UplinkLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "rssi": l.rssi,
            "snr": l.snr,
            "payload_raw": l.payload_raw,
            "payload_decoded": l.payload_decoded,
            "timestamp": l.timestamp.isoformat() + "Z",
        }
        for l in logs
    ]


@router.post("/", status_code=201)
def create_device(data: DeviceCreate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(auth_utils.require_admin)):
    existing = db.query(models.Device).filter(models.Device.dev_eui == data.dev_eui).first()
    if existing:
        raise HTTPException(status_code=400, detail="DevEUI already registered")
    device = models.Device(**data.model_dump())
    db.add(device)
    db.add(models.AuditLog(user_email=current_user.email, action="CREATE",
                            resource="device", details=f"DevEUI={data.dev_eui}"))
    db.commit()
    db.refresh(device)
    return device_to_dict(device)


@router.put("/{device_id}")
def update_device(device_id: int, data: DeviceUpdate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(auth_utils.require_admin)):
    d = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(d, field, value)
    db.add(models.AuditLog(user_email=current_user.email, action="UPDATE",
                            resource="device", resource_id=str(device_id)))
    db.commit()
    db.refresh(d)
    return device_to_dict(d)


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: int, db: Session = Depends(get_db),
                  current_user: models.User = Depends(auth_utils.require_admin)):
    d = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(d)
    db.add(models.AuditLog(user_email=current_user.email, action="DELETE",
                            resource="device", resource_id=str(device_id)))
    db.commit()
