\#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.database.connection import get_db_session
from src.database.models import (
    Patient, Device, Session as SessionModel, DeviceParameter,
    DeviceMeasurement, ArrhythmiaEpisode, DeviceStatus
)

def view_session_data(session_id: str = "d89896a7-5e82-4f8b-acff-18fbc0a9dde2"):
    """View all data for the latest session"""
    db_session = get_db_session()
    
    try:
        print(f"📋 SESSION DATA: {session_id}")
        print("="*80)
        
        # Get session info
        session_record = db_session.query(SessionModel).filter(
            SessionModel.session_id == session_id
        ).first()
        
        if not session_record:
            print("❌ Session not found!")
            return
        
        # Get patient and device
        patient = db_session.query(Patient).filter(
            Patient.patient_id == session_record.patient_id
        ).first()
        
        device = db_session.query(Device).filter(
            Device.device_id == session_record.device_id
        ).first()
        
        print(f"👤 PATIENT: {patient.patient_name}")
        print(f"🔧 DEVICE: {device.device_model} (S/N: {device.serial_number})")
        print(f"📅 INTERROGATION: {session_record.interrogation_date}")
        print(f"👨‍⚕️ PHYSICIAN: {patient.physician_name}")
        
        # Parameters
        parameters = db_session.query(DeviceParameter).filter(
            DeviceParameter.session_id == session_id
        ).all()
        
        print(f"\n⚙️  DEVICE PARAMETERS ({len(parameters)}):")
        print("-" * 50)
        for param in parameters:
            units = f" {param.parameter_units}" if param.parameter_units else ""
            category = f"[{param.parameter_category}] " if param.parameter_category else ""
            print(f"  • {category}{param.parameter_name}: {param.parameter_value}{units}")
        
        # Measurements  
        measurements = db_session.query(DeviceMeasurement).filter(
            DeviceMeasurement.session_id == session_id
        ).all()
        
        print(f"\n📏 LEAD MEASUREMENTS ({len(measurements)}):")
        print("-" * 50)
        for measure in measurements:
            status = f" [{measure.status_flag}]" if measure.status_flag else ""
            location = f" ({measure.lead_location})" if measure.lead_location else ""
            units = f" {measure.measurement_units}" if measure.measurement_units else ""
            normal = f" (Normal: {measure.normal_range})" if measure.normal_range else ""
            print(f"  • {measure.measurement_type}{location}: {measure.measured_value}{units}{status}{normal}")
        
        # Episodes
        episodes = db_session.query(ArrhythmiaEpisode).filter(
            ArrhythmiaEpisode.session_id == session_id
        ).all()
        
        print(f"\n⚡ ARRHYTHMIA EPISODES ({len(episodes)}):")
        print("-" * 50)
        for episode in episodes:
            therapy_info = ""
            if episode.therapy_delivered > 0:
                therapy_type = f" ({episode.therapy_type})" if episode.therapy_type else ""
                therapy_info = f" | Therapy: {episode.therapy_delivered}{therapy_type}"
            print(f"  • {episode.episode_type}: {episode.episode_count} episodes{therapy_info}")
        
        # Device Status
        device_status = db_session.query(DeviceStatus).filter(
            DeviceStatus.session_id == session_id
        ).first()
        
        if device_status:
            print(f"\n🔋 DEVICE STATUS:")
            print("-" * 50)
            if device_status.battery_voltage:
                print(f"  • Battery: {device_status.battery_voltage}V | {device_status.battery_status}")
            if device_status.remaining_longevity_months:
                print(f"  • Longevity: {device_status.remaining_longevity_months} months remaining")
            print(f"  • Overall Status: {device_status.overall_status}")
            if device_status.device_alerts:
                print(f"  • Alerts: {', '.join(device_status.device_alerts)}")
        
        print(f"\n✅ Session successfully processed on {session_record.created_at}")
        
    except Exception as e:
        print(f"❌ Error viewing data: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_session.close()

def view_all_sessions():
    """View summary of all sessions"""
    db_session = get_db_session()
    
    try:
        print("\n📊 ALL SESSIONS SUMMARY:")
        print("="*80)
        
        sessions = db_session.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
        
        for i, session_record in enumerate(sessions, 1):
            patient = db_session.query(Patient).filter(
                Patient.patient_id == session_record.patient_id
            ).first()
            
            device = db_session.query(Device).filter(
                Device.device_id == session_record.device_id
            ).first()
            
            print(f"{i}. {patient.patient_name} | {device.device_model} | {session_record.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Session ID: {session_record.session_id}")
            print(f"   Status: {session_record.processing_status}")
            print()
    
    except Exception as e:
        print(f"❌ Error viewing sessions: {e}")
    
    finally:
        db_session.close()

if __name__ == "__main__":
    # View the specific session
    view_session_data()
    
    # Also show all sessions
    view_all_sessions()