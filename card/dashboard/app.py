#!/usr/bin/env python3
"""
Medtronic Clinical Dashboard - CardiAVue
Interactive web interface for viewing patient device data
Updated with login authentication system
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json
import traceback

# Add project root to path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from src.database.connection import get_db_session
from src.database.models import (
    Patient, Device, Session as SessionModel, DeviceParameter,
    DeviceMeasurement, ArrhythmiaEpisode, DeviceStatus
)

app = Flask(__name__)

# SECRET KEY - Required for sessions/login to work
app.secret_key = 'your-super-secret-key-2025'  # ← UPDATED SECRET KEY

# Or use environment variable (more secure)
# app.secret_key = os.environ.get('SECRET_KEY', 'your-super-secret-key-2025')

# Test credentials for authentication
VALID_USERS = {
    'doctor': 'pass123',
    'nurse': 'pass123',
    'admin': 'admin123',
    'cubit104': 'medtronic'
}

@app.route('/')
def login():
    """Login page - New home page with animations"""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def authenticate():
    """Handle login authentication"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Check credentials
    if username in VALID_USERS and VALID_USERS[username] == password:
        session['user'] = username
        session['login_time'] = datetime.now().isoformat()
        print(f"✅ User {username} logged in successfully")
        return redirect(url_for('dashboard'))
    else:
        print(f"❌ Failed login attempt for user: {username}")
        return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard page showing patient list - requires login"""
    # Check if user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))
    
    current_user = session.get('user', 'Unknown')
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('dashboard.html', 
                         current_time=current_time,
                         current_user=current_user)

@app.route('/logout')
def logout():
    """Logout user and redirect to login page"""
    user = session.get('user', 'Unknown')
    session.pop('user', None)
    session.pop('login_time', None)
    print(f"👋 User {user} logged out")
    return redirect(url_for('login'))

@app.route('/api/patients')
def get_patients():
    """API endpoint to get all patients with their latest session info"""
    # Check if user is logged in for API access
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db_session = get_db_session()
    
    try:
        print("🔍 DEBUG: Loading patients...")
        
        # Get all patients with their latest session data
        patients_data = []
        patients = db_session.query(Patient).all()
        
        print(f"📊 DEBUG: Found {len(patients)} patients")
        
        for patient in patients:
            print(f"👤 DEBUG: Processing patient {patient.patient_name}")
            
            # Get latest session for this patient
            latest_session = db_session.query(SessionModel).filter(
                SessionModel.patient_id == patient.patient_id
            ).order_by(SessionModel.created_at.desc()).first()
            
            if latest_session:
                print(f"📋 DEBUG: Found session {latest_session.session_id}")
                
                # Get device info
                device = db_session.query(Device).filter(
                    Device.device_id == latest_session.device_id
                ).first()
                
                # Get device status
                device_status = db_session.query(DeviceStatus).filter(
                    DeviceStatus.session_id == latest_session.session_id
                ).first()
                
                patients_data.append({
                    'patient_id': str(patient.patient_id),
                    'patient_name': patient.patient_name,
                    'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                    'physician_name': patient.physician_name,
                    'device_model': device.device_model if device else 'Unknown',
                    'serial_number': device.serial_number if device else 'Unknown',
                    'last_session_id': str(latest_session.session_id),
                    'last_interrogation': latest_session.interrogation_date.isoformat(),
                    'battery_status': device_status.battery_status if device_status else 'Unknown',
                    'remaining_months': device_status.remaining_longevity_months if device_status else 0,
                    'overall_status': device_status.overall_status if device_status else 'Unknown'
                })
        
        print(f"✅ DEBUG: Returning {len(patients_data)} patients")
        return jsonify(patients_data)
    
    except Exception as e:
        print(f"❌ DEBUG: Error loading patients: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    finally:
        db_session.close()

@app.route('/patient/<patient_id>')
def patient_details(patient_id):
    """Show all sessions for this patient"""
    # Check if user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))
    
    db_session = get_db_session()
    
    try:
        print(f"🔍 DEBUG: Loading patient {patient_id}")
        
        # Get all sessions for this patient using ORM
        sessions = db_session.query(SessionModel).filter(
            SessionModel.patient_id == patient_id
        ).order_by(SessionModel.created_at.desc()).all()
        
        if not sessions:
            print(f"❌ DEBUG: No sessions found for patient {patient_id}")
            return "Patient not found", 404
        
        print(f"📋 DEBUG: Found {len(sessions)} sessions for patient")
        
        # Get patient info
        patient = db_session.query(Patient).filter(
            Patient.patient_id == patient_id
        ).first()
        
        # Format sessions data for template
        sessions_data = []
        for session_item in sessions:
            # Get device info
            device = db_session.query(Device).filter(
                Device.device_id == session_item.device_id
            ).first()
            
            sessions_data.append({
                'session_id': str(session_item.session_id),
                'interrogation_date': session_item.interrogation_date,
                'created_at': session_item.created_at,
                'session_type': session_item.session_type,
                'processing_status': session_item.processing_status,
                'pdf_filename': session_item.pdf_filename,
                'device_model': device.device_model if device else 'Unknown'
            })
        
        return render_template('patient_history.html', 
                             patient_id=patient_id,
                             patient_name=patient.patient_name if patient else 'Unknown Patient',
                             sessions=sessions_data,
                             current_user=session.get('user', 'Unknown'))
    
    except Exception as e:
        print(f"❌ DEBUG: Error loading patient {patient_id}: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    finally:
        db_session.close()

@app.route('/api/session/<session_id>')
def get_session_details(session_id):
    """Get detailed session data including measurements, parameters, and episodes"""
    # Check if user is logged in for API access
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    db_session = get_db_session()
    
    try:
        print(f"🔍 DEBUG: Loading session {session_id}")
        
        # Get session info
        session_obj = db_session.query(SessionModel).filter(
            SessionModel.session_id == session_id
        ).first()
        
        if not session_obj:
            print(f"❌ DEBUG: Session {session_id} not found")
            return jsonify({'error': 'Session not found'}), 404
        
        print(f"📋 DEBUG: Found session for patient {session_obj.patient_id}")
        
        # Get patient and device
        patient = db_session.query(Patient).filter(
            Patient.patient_id == session_obj.patient_id
        ).first()
        
        device = db_session.query(Device).filter(
            Device.device_id == session_obj.device_id
        ).first()
        
        print(f"👤 DEBUG: Patient: {patient.patient_name if patient else 'None'}")
        print(f"🔧 DEBUG: Device: {device.device_model if device else 'None'}")
        
        # Get parameters
        parameters = db_session.query(DeviceParameter).filter(
            DeviceParameter.session_id == session_id
        ).all()
        
        print(f"⚙️ DEBUG: Found {len(parameters)} parameters")
        
        parameters_data = []
        for param in parameters:
            param_dict = {
                'category': param.parameter_category,
                'name': param.parameter_name,
                'value': param.parameter_value,
                'units': param.parameter_units,
                'normal_range': param.normal_range,
                'is_changed': param.is_changed
            }
            parameters_data.append(param_dict)
            print(f"  📝 {param.parameter_name}: {param.parameter_value}")
        
        # Get measurements
        measurements = db_session.query(DeviceMeasurement).filter(
            DeviceMeasurement.session_id == session_id
        ).all()
        
        print(f"📏 DEBUG: Found {len(measurements)} measurements")
        
        measurements_data = []
        for measure in measurements:
            measure_dict = {
                'type': measure.measurement_type,
                'lead_location': measure.lead_location,
                'value': float(measure.measured_value) if measure.measured_value else 0,
                'units': measure.measurement_units,
                'normal_range': measure.normal_range,
                'status': measure.status_flag,
                'test_conditions': measure.test_conditions
            }
            measurements_data.append(measure_dict)
            print(f"  📏 {measure.measurement_type} ({measure.lead_location}): {measure.measured_value}")
        
        # Get episodes
        episodes = db_session.query(ArrhythmiaEpisode).filter(
            ArrhythmiaEpisode.session_id == session_id
        ).all()
        
        print(f"⚡ DEBUG: Found {len(episodes)} episodes")
        
        episodes_data = []
        for episode in episodes:
            episode_dict = {
                'type': episode.episode_type,
                'count': episode.episode_count,
                'since_last': episode.episodes_since_last,
                'total': episode.total_episodes,
                'therapy_delivered': episode.therapy_delivered,
                'therapy_type': episode.therapy_type
            }
            episodes_data.append(episode_dict)
            print(f"  ⚡ {episode.episode_type}: {episode.episode_count}")
        
        # Get device status
        device_status = db_session.query(DeviceStatus).filter(
            DeviceStatus.session_id == session_id
        ).first()
        
        status_data = {}
        if device_status:
            status_data = {
                'battery_voltage': float(device_status.battery_voltage) if device_status.battery_voltage else 2.7,
                'battery_status': device_status.battery_status,
                'remaining_months': device_status.remaining_longevity_months,
                'overall_status': device_status.overall_status,
                'device_alerts': device_status.device_alerts or []
            }
            print(f"🔋 DEBUG: Battery status: {device_status.battery_status}")
        else:
            print("⚠️ DEBUG: No device status found")
        
        response_data = {
            'session': {
                'session_id': str(session_obj.session_id),
                'interrogation_date': session_obj.interrogation_date.isoformat(),
                'session_type': session_obj.session_type,
                'physician_name': session_obj.physician_name,
                'processing_status': session_obj.processing_status
            },
            'patient': {
                'name': patient.patient_name if patient else 'Unknown',
                'physician': patient.physician_name if patient else None
            },
            'device': {
                'model': device.device_model if device else 'Unknown',
                'serial_number': device.serial_number if device else 'Unknown',
                'manufacturer': device.manufacturer if device else 'Medtronic',
                'device_type': device.device_type if device else 'ICD',
                'implant_date': device.implant_date.isoformat() if device and device.implant_date else None
            },
            'parameters': parameters_data,
            'measurements': measurements_data,
            'episodes': episodes_data,
            'device_status': status_data
        }
        
        print(f"✅ DEBUG: Returning complete session data")
        return jsonify(response_data)
    
    except Exception as e:
        print(f"❌ DEBUG: Error loading session {session_id}: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    finally:
        db_session.close()

@app.route('/session/<session_id>')
def session_detail_page(session_id):
    """Session detail page with clinical data"""
    # Check if user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template('session_detail.html', 
                         session_id=session_id,
                         current_user=session.get('user', 'Unknown'))

@app.route('/api/test')
def test_api():
    """Test endpoint to verify API is working"""
    return jsonify({
        'status': 'API Working',
        'timestamp': datetime.utcnow().isoformat(),
        'user': session.get('user', 'Not logged in'),
        'utc_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/user/info')
def user_info():
    """Get current user information"""
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    return jsonify({
        'username': session.get('user'),
        'login_time': session.get('login_time'),
        'current_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    print("🚀 Starting CardiAVue - Medtronic Clinical Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔐 Login required - Use test credentials")
    print(f"🕐 Started at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("🔧 Debug mode enabled - Check console for detailed logs")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
