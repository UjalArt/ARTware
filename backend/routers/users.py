from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import get_db
import models
import auth as auth_utils

router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: Optional[str] = "viewer"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


def user_to_dict(u: models.User):
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() + "Z",
    }


@router.get("/")
def list_users(db: Session = Depends(get_db), _=Depends(auth_utils.require_admin)):
    return [user_to_dict(u) for u in db.query(models.User).all()]


@router.post("/", status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth_utils.require_superadmin)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=data.email,
        full_name=data.full_name,
        password_hash=auth_utils.hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.add(models.AuditLog(user_email=current_user.email, action="CREATE",
                            resource="user", details=f"{data.email} role={data.role}"))
    db.commit()
    db.refresh(user)
    return user_to_dict(user)


@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth_utils.require_superadmin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.add(models.AuditLog(user_email=current_user.email, action="UPDATE",
                            resource="user", resource_id=str(user_id)))
    db.commit()
    db.refresh(user)
    return user_to_dict(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth_utils.require_superadmin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    db.delete(user)
    db.add(models.AuditLog(user_email=current_user.email, action="DELETE",
                            resource="user", resource_id=str(user_id)))
    db.commit()


@router.get("/audit-log")
def get_audit_log(limit: int = 100, db: Session = Depends(get_db),
                  _=Depends(auth_utils.require_admin)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "user_email": l.user_email,
            "action": l.action,
            "resource": l.resource,
            "resource_id": l.resource_id,
            "details": l.details,
            "timestamp": l.timestamp.isoformat() + "Z",
        }
        for l in logs
    ]
