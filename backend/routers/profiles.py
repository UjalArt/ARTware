from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
import auth as auth_utils

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


class ProfileCreate(BaseModel):
    name: str
    manufacturer: str
    model: str
    description: Optional[str] = ""
    decoder_key: Optional[str] = "passthrough"
    icon: Optional[str] = "📡"


def profile_to_dict(p: models.DeviceProfile):
    return {
        "id": p.id,
        "name": p.name,
        "manufacturer": p.manufacturer,
        "model": p.model,
        "description": p.description,
        "decoder_key": p.decoder_key,
        "icon": p.icon,
        "is_custom": p.is_custom,
        "device_count": len(p.devices),
        "created_at": p.created_at.isoformat() + "Z",
    }


@router.get("/")
def list_profiles(db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    return [profile_to_dict(p) for p in db.query(models.DeviceProfile).all()]


@router.get("/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    p = db.query(models.DeviceProfile).filter(models.DeviceProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile_to_dict(p)


@router.post("/", status_code=201)
def create_profile(data: ProfileCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth_utils.require_admin)):
    p = models.DeviceProfile(**data.model_dump(), is_custom=True)
    db.add(p)
    db.add(models.AuditLog(user_email=current_user.email, action="CREATE",
                            resource="device_profile", details=f"{data.manufacturer} {data.model}"))
    db.commit()
    db.refresh(p)
    return profile_to_dict(p)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth_utils.require_admin)):
    p = db.query(models.DeviceProfile).filter(models.DeviceProfile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not p.is_custom:
        raise HTTPException(status_code=400, detail="Cannot delete built-in profiles")
    db.delete(p)
    db.add(models.AuditLog(user_email=current_user.email, action="DELETE",
                            resource="device_profile", resource_id=str(profile_id)))
    db.commit()
