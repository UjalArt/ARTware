from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
import models
import auth as auth_utils

router = APIRouter(prefix="/api/rules", tags=["rules"])


class RuleCreate(BaseModel):
    name: str
    device_id: Optional[int] = None
    profile_id: Optional[int] = None
    target_type: str  # thingsboard, chirpstack, webhook
    target_url: str
    target_config: Optional[dict] = {}
    is_active: Optional[bool] = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    target_url: Optional[str] = None
    target_config: Optional[dict] = None
    is_active: Optional[bool] = None


def rule_to_dict(r: models.ForwardingRule):
    device_name = None
    profile_name = None
    if r.device_id:
        device = r.device_id  # just keep the ID
    return {
        "id": r.id,
        "name": r.name,
        "device_id": r.device_id,
        "profile_id": r.profile_id,
        "target_type": r.target_type,
        "target_url": r.target_url,
        "target_config": r.target_config,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat() + "Z",
    }


@router.get("/")
def list_rules(db: Session = Depends(get_db), _=Depends(auth_utils.require_viewer)):
    rules = db.query(models.ForwardingRule).all()
    result = []
    for r in rules:
        d = rule_to_dict(r)
        if r.device_id:
            dev = db.query(models.Device).filter(models.Device.id == r.device_id).first()
            d["device_name"] = dev.name if dev else None
        if r.profile_id:
            prof = db.query(models.DeviceProfile).filter(models.DeviceProfile.id == r.profile_id).first()
            d["profile_name"] = prof.name if prof else None
        result.append(d)
    return result


@router.post("/", status_code=201)
def create_rule(data: RuleCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth_utils.require_operator)):
    rule = models.ForwardingRule(**data.model_dump())
    db.add(rule)
    db.add(models.AuditLog(user_email=current_user.email, action="CREATE",
                            resource="forwarding_rule", details=data.name))
    db.commit()
    db.refresh(rule)
    return rule_to_dict(rule)


@router.put("/{rule_id}")
def update_rule(rule_id: int, data: RuleUpdate, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth_utils.require_operator)):
    rule = db.query(models.ForwardingRule).filter(models.ForwardingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    db.add(models.AuditLog(user_email=current_user.email, action="UPDATE",
                            resource="forwarding_rule", resource_id=str(rule_id)))
    db.commit()
    db.refresh(rule)
    return rule_to_dict(rule)


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth_utils.require_operator)):
    rule = db.query(models.ForwardingRule).filter(models.ForwardingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.add(models.AuditLog(user_email=current_user.email, action="DELETE",
                            resource="forwarding_rule", resource_id=str(rule_id)))
    db.commit()
