"""
Database operations for inserting Medtronic device data
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import get_db_session, engine
from src.database.models import (
    Patient, Device, Session as SessionModel, DeviceParameter,
    DeviceMeasurement, ArrhythmiaEpisode, DeviceStatus
)
from src.utils.logger import setup_logging

class MedtronicDataInserter:
    """Handle database operations for Medtronic device data"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.session = None
    
    def __enter__(self):
        self.session = get_db_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
    
    def insert_complete_session(self, extracted_data: Dict[str, Any]) -> Optional[str]:
        """Insert all extracted data and return session ID"""
        try:
            # Insert patient
            patient = self._insert_or_get_patient(extracted_data["patient"])
            
            # Insert device
            device = self._insert_or_get_device(extracted_data["device"])
            
            # Insert session
            session = self._insert_session(patient.patient_id, device.device_id, extracted_data)
            
            # Insert parameters (with validation)
            valid_parameters = self._validate_parameters(extracted_data["parameters"])
            self._insert_parameters(session.session_id, valid_parameters)
            
            # Insert measurements (with validation)
            valid_measurements = self._validate_measurements(extracted_data["measurements"])
            self._insert_measurements(session.session_id, valid_measurements)
            
            # Insert episodes (with validation)
            valid_episodes = self._validate_episodes(extracted_data["episodes"])
            self._insert_episodes(session.session_id, valid_episodes)
            
            # Insert device status
            self._insert_device_status(session.session_id, extracted_data["device_status"])
            
            # Commit transaction
            self.session.commit()
            
            self.logger.info(f"✅ Successfully inserted session: {session.session_id}")
            return str(session.session_id)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to insert session data: {e}")
            if self.session:
                self.session.rollback()
            return None
    
    def _validate_parameters(self, parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and filter parameters"""
        valid_params = []
        for param in parameters:
            # Check required fields
            if (param.get("parameter_name") and 
                param.get("parameter_value") is not None):
                valid_params.append(param)
            else:
                self.logger.warning(f"Skipping invalid parameter: {param}")
        
        self.logger.info(f"Validated {len(valid_params)} of {len(parameters)} parameters")
        return valid_params
    
    def _validate_measurements(self, measurements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and filter measurements"""
        valid_measurements = []
        for measurement in measurements:
            # Check required fields
            if (measurement.get("measurement_type") and 
                measurement.get("measured_value") is not None):
                valid_measurements.append(measurement)
            else:
                self.logger.warning(f"Skipping invalid measurement: {measurement}")
        
        self.logger.info(f"Validated {len(valid_measurements)} of {len(measurements)} measurements")
        return valid_measurements
    
    def _validate_episodes(self, episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and filter episodes"""
        valid_episodes = []
        for episode in episodes:
            # Check required fields
            if (episode.get("episode_type") and 
                episode.get("episode_count") is not None):
                valid_episodes.append(episode)
            else:
                self.logger.warning(f"Skipping invalid episode: {episode}")
        
        self.logger.info(f"Validated {len(valid_episodes)} of {len(episodes)} episodes")
        return valid_episodes
    
    def _insert_or_get_patient(self, patient_data: Dict[str, Any]) -> Patient:
        """Insert or retrieve existing patient"""
        patient_name = patient_data.get("patient_name")
        if not patient_name:
            raise ValueError("Patient name is required")
        
        # Check if patient exists
        existing_patient = self.session.query(Patient).filter(
            Patient.patient_name == patient_name
        ).first()
        
        if existing_patient:
            self.logger.info(f"Found existing patient: {patient_name}")
            return existing_patient
        
        # Create new patient
        patient = Patient(
            patient_name=patient_name,
            date_of_birth=patient_data.get("date_of_birth"),
            medical_record_number=patient_data.get("medical_record_number"),
            physician_name=patient_data.get("physician_name")
        )
        
        self.session.add(patient)
        self.session.flush()  # Get the ID
        
        self.logger.info(f"Created new patient: {patient_name}")
        return patient
    
    def _insert_or_get_device(self, device_data: Dict[str, Any]) -> Device:
        """Insert or retrieve existing device"""
        serial_number = device_data.get("serial_number")
        device_model = device_data.get("device_model")
        
        if not serial_number:
            raise ValueError("Device serial number is required")
        
        # Check if device exists
        existing_device = self.session.query(Device).filter(
            Device.serial_number == serial_number
        ).first()
        
        if existing_device:
            self.logger.info(f"Found existing device: {serial_number}")
            return existing_device
        
        # Create new device
        device = Device(
            device_model=device_model or "Unknown",
            serial_number=serial_number,
            manufacturer=device_data.get("manufacturer", "Medtronic"),
            device_type=device_data.get("device_type"),
            implant_date=device_data.get("implant_date")
        )
        
        self.session.add(device)
        self.session.flush()  # Get the ID
        
        self.logger.info(f"Created new device: {device_model}")
        return device
    
    def _insert_session(self, patient_id: str, device_id: str, extracted_data: Dict[str, Any]) -> SessionModel:
        """Insert new session"""
        session_record = SessionModel(
            patient_id=patient_id,
            device_id=device_id,
            interrogation_date=datetime.now(),
            session_type="interrogation",
            physician_name=extracted_data["patient"].get("physician_name"),
            pdf_filename=getattr(extracted_data, "pdf_filename", "icd.pdf"),
            processing_status="completed"
        )
        
        self.session.add(session_record)
        self.session.flush()  # Get the ID
        
        self.logger.info(f"Created session for patient {patient_id}")
        return session_record
    
    def _insert_parameters(self, session_id: str, parameters: List[Dict[str, Any]]):
        """Insert device parameters"""
        for param_data in parameters:
            parameter = DeviceParameter(
                session_id=session_id,
                parameter_category=param_data.get("parameter_category"),
                parameter_name=param_data["parameter_name"],  # Required
                parameter_value=str(param_data["parameter_value"]),  # Required
                parameter_units=param_data.get("parameter_units"),
                normal_range=param_data.get("normal_range"),
                is_changed=param_data.get("is_changed", False)
            )
            self.session.add(parameter)
        
        self.logger.info(f"Inserted {len(parameters)} parameters")
    
    def _insert_measurements(self, session_id: str, measurements: List[Dict[str, Any]]):
        """Insert device measurements"""
        for measurement_data in measurements:
            measurement = DeviceMeasurement(
                session_id=session_id,
                measurement_type=measurement_data["measurement_type"],  # Required
                lead_location=measurement_data.get("lead_location"),
                measured_value=float(measurement_data["measured_value"]),  # Required
                measurement_units=measurement_data.get("measurement_units"),
                normal_range=measurement_data.get("normal_range"),
                status_flag=measurement_data.get("status_flag"),
                test_conditions=measurement_data.get("test_conditions")
            )
            self.session.add(measurement)
        
        self.logger.info(f"Inserted {len(measurements)} measurements")
    
    def _insert_episodes(self, session_id: str, episodes: List[Dict[str, Any]]):
        """Insert arrhythmia episodes"""
        for episode_data in episodes:
            episode = ArrhythmiaEpisode(
                session_id=session_id,
                episode_type=episode_data["episode_type"],  # Required
                episode_count=int(episode_data.get("episode_count", 0)),
                episodes_since_last=int(episode_data.get("episodes_since_last", 0)),
                total_episodes=int(episode_data.get("total_episodes", 0)),
                therapy_delivered=int(episode_data.get("therapy_delivered", 0)),
                therapy_type=episode_data.get("therapy_type"),
                longest_episode_duration=episode_data.get("longest_episode_duration")
            )
            self.session.add(episode)
        
        self.logger.info(f"Inserted {len(episodes)} episodes")
    
    def _insert_device_status(self, session_id: str, status_data: Dict[str, Any]):
        """Insert device status"""
        device_status = DeviceStatus(
            session_id=session_id,
            battery_voltage=status_data.get("battery_voltage"),
            battery_status=status_data.get("battery_status", "Unknown"),
            remaining_longevity_months=status_data.get("remaining_longevity_months"),
            device_alerts=status_data.get("device_alerts", []),
            overall_status=status_data.get("overall_status", "Unknown")
        )
        
        self.session.add(device_status)
        self.logger.info("Inserted device status")

# Test database operations
if __name__ == "__main__":
    # Test database connection
    from src.database.connection import test_connection
    test_connection()