from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
import auth as auth_utils

router = APIRouter(prefix="/api/gateways", tags=["gateways"])


class GatewayCreate(BaseModel):
    name: str
    eui: str
    model: Optional[str] = "Unknown"
    mqtt_topic_pattern: Optional[str] = "application/+/device/+/rx"
    lat: Optional[float] = None
    lon: Optional[float] = None


class GatewayUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    mqtt_topic_pattern: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    status: Optional[str] = None


def gw_to_dict(gw: models.Gateway):
    return {
        "id": gw.id,
        "name": gw.name,
        "eui": gw.eui,
        "model": gw.model,
        "mqtt_topic_pattern": gw.mqtt_topic_pattern,
        "status": gw.status,
        "lat": gw.lat,
        "lon": gw.lon,
        "device_count": len(gw.devices),
        "last_seen": gw.last_seen.isoformat() + "Z" if gw.last_seen else None,
        "created_at": gw.created_at.isoformat() + "Z",
    }


@router.get("/")
def list_gateways(db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    return [gw_to_dict(gw) for gw in db.query(models.Gateway).all()]


@router.get("/{gateway_id}")
def get_gateway(gateway_id: int, db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    gw = db.query(models.Gateway).filter(models.Gateway.id == gateway_id).first()
    if not gw:
        raise HTTPException(status_code=404, detail="Gateway not found")
    return gw_to_dict(gw)


@router.post("/", status_code=201)
def create_gateway(data: GatewayCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth_utils.require_admin)):
    existing = db.query(models.Gateway).filter(models.Gateway.eui == data.eui).first()
    if existing:
        raise HTTPException(status_code=400, detail="Gateway EUI already exists")
    gw = models.Gateway(**data.model_dump())
    db.add(gw)
    db.add(models.AuditLog(user_email=current_user.email, action="CREATE",
                            resource="gateway", details=f"EUI={data.eui}"))
    db.commit()
    db.refresh(gw)
    return gw_to_dict(gw)


@router.put("/{gateway_id}")
def update_gateway(gateway_id: int, data: GatewayUpdate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth_utils.require_admin)):
    gw = db.query(models.Gateway).filter(models.Gateway.id == gateway_id).first()
    if not gw:
        raise HTTPException(status_code=404, detail="Gateway not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(gw, field, value)
    db.add(models.AuditLog(user_email=current_user.email, action="UPDATE",
                            resource="gateway", resource_id=str(gateway_id)))
    db.commit()
    db.refresh(gw)
    return gw_to_dict(gw)


@router.delete("/{gateway_id}", status_code=204)
def delete_gateway(gateway_id: int, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth_utils.require_admin)):
    gw = db.query(models.Gateway).filter(models.Gateway.id == gateway_id).first()
    if not gw:
        raise HTTPException(status_code=404, detail="Gateway not found")
    db.delete(gw)
    db.add(models.AuditLog(user_email=current_user.email, action="DELETE",
                            resource="gateway", resource_id=str(gateway_id)))
    db.commit()
