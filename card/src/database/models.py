"""
SQLAlchemy models for Medtronic database tables
Maps to the 12 UUID tables we created
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, ARRAY, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .connection import Base

class Patient(Base):
    __tablename__ = 'patients'
    
    patient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date)
    medical_record_number = Column(String(100))
    physician_name = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

class Device(Base):
    __tablename__ = 'devices'
    
    device_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_model = Column(String(255), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=False)
    manufacturer = Column(String(100), default='Medtronic')
    device_type = Column(String(100))
    implant_date = Column(Date)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

class Session(Base):
    __tablename__ = 'sessions'
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), nullable=False)
    device_id = Column(UUID(as_uuid=True), nullable=False)
    interrogation_date = Column(DateTime, nullable=False)
    session_type = Column(String(50), default='interrogation')
    physician_name = Column(String(255))
    clinic_location = Column(String(255))
    pdf_filename = Column(String(500))
    processing_status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

class DeviceParameter(Base):
    __tablename__ = 'device_parameters'
    
    parameter_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    parameter_category = Column(String(100))
    parameter_name = Column(String(255), nullable=False)
    parameter_value = Column(String(255))
    parameter_units = Column(String(50))
    normal_range = Column(String(100))
    is_changed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class DeviceMeasurement(Base):
    __tablename__ = 'device_measurements'
    
    measurement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    measurement_type = Column(String(100))
    lead_location = Column(String(50))
    measured_value = Column(Numeric(10, 3))  # Changed from Decimal to Numeric
    measurement_units = Column(String(50))
    normal_range = Column(String(100))
    status_flag = Column(String(50))
    test_conditions = Column(String(255))
    created_at = Column(DateTime, default=func.now())

class ArrhythmiaEpisode(Base):
    __tablename__ = 'arrhythmia_episodes'
    
    episode_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    episode_type = Column(String(50))
    episode_count = Column(Integer, default=0)
    episodes_since_last = Column(Integer, default=0)
    total_episodes = Column(Integer, default=0)
    therapy_delivered = Column(Integer, default=0)
    therapy_type = Column(String(100))
    longest_episode_duration = Column(String(50))
    created_at = Column(DateTime, default=func.now())

class DeviceStatus(Base):
    __tablename__ = 'device_status'
    
    status_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    battery_voltage = Column(Numeric(4, 2))  # Changed from Decimal to Numeric
    battery_status = Column(String(50))
    remaining_longevity_months = Column(Integer)
    device_alerts = Column(ARRAY(Text))
    lead_status = Column(JSONB)
    overall_status = Column(String(50))
    next_followup_date = Column(Date)
    created_at = Column(DateTime, default=func.now())