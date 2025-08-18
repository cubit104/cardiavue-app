import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from src.database.connection import get_db_session
from src.database.models import Patient, Device, Session as SessionModel, DeviceParameter, DeviceMeasurement

# Quick check of what's in the database
db_session = get_db_session()

print("📊 QUICK DATABASE CHECK")
print("="*50)

# Count records
patients = db_session.query(Patient).count()
devices = db_session.query(Device).count() 
sessions = db_session.query(SessionModel).count()
parameters = db_session.query(DeviceParameter).count()
measurements = db_session.query(DeviceMeasurement).count()

print(f"Patients: {patients}")
print(f"Devices: {devices}")
print(f"Sessions: {sessions}")
print(f"Parameters: {parameters}")
print(f"Measurements: {measurements}")

# Show latest session
latest_session = db_session.query(SessionModel).order_by(SessionModel.created_at.desc()).first()
if latest_session:
    print(f"\nLatest Session: {latest_session.session_id}")
    print(f"Created: {latest_session.created_at}")

db_session.close()