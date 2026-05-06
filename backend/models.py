from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime,
    ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="viewer")  # superadmin, admin, operator, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Gateway(Base):
    __tablename__ = "gateways"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    eui = Column(String, unique=True, nullable=False)
    model = Column(String, default="Unknown")
    mqtt_topic_pattern = Column(String, default="application/+/device/+/rx")
    status = Column(String, default="offline")  # online, offline, warning
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    devices = relationship("Device", back_populates="gateway")


class DeviceProfile(Base):
    __tablename__ = "device_profiles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    manufacturer = Column(String, nullable=False)
    model = Column(String, nullable=False)
    description = Column(Text, default="")
    decoder_key = Column(String, default="passthrough")
    icon = Column(String, default="🔌")
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    devices = relationship("Device", back_populates="profile")


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    dev_eui = Column(String, unique=True, nullable=False)
    gateway_id = Column(Integer, ForeignKey("gateways.id"), nullable=True)
    profile_id = Column(Integer, ForeignKey("device_profiles.id"), nullable=True)
    status = Column(String, default="offline")
    last_seen = Column(DateTime, nullable=True)
    last_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    gateway = relationship("Gateway", back_populates="devices")
    profile = relationship("DeviceProfile", back_populates="devices")
    uplinks = relationship("UplinkLog", back_populates="device")


class ForwardingRule(Base):
    __tablename__ = "forwarding_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    profile_id = Column(Integer, ForeignKey("device_profiles.id"), nullable=True)
    target_type = Column(String, nullable=False)  # thingsboard, chirpstack, webhook
    target_url = Column(String, nullable=False)
    target_config = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UplinkLog(Base):
    __tablename__ = "uplink_logs"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    gateway_id = Column(Integer, ForeignKey("gateways.id"), nullable=True)
    dev_eui = Column(String, nullable=False)
    rssi = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)
    payload_raw = Column(String, nullable=True)
    payload_decoded = Column(JSON, nullable=True)
    topic = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    device = relationship("Device", back_populates="uplinks")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
