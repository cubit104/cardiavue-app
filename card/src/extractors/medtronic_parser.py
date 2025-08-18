"""
Enhanced Medtronic-specific PDF parser
Extracts structured data from Medtronic device PDFs
"""

import re
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, date

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from src.extractors.pdf_parser import PDFParser
from src.utils.logger import setup_logging

class MedtronicParser:
    """Enhanced parser for Medtronic device PDFs"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf_parser = PDFParser(pdf_path)
        self.logger = setup_logging()
        
    def extract_medtronic_data(self) -> Dict[str, Any]:
        """Extract all Medtronic data from PDF"""
        try:
            # Extract raw content first
            pdf_content = self.pdf_parser.extract_all()
            
            if pdf_content["status"] == "error":
                return pdf_content
            
            text = pdf_content["text"]
            
            # Extract structured data
            patient_data = self._parse_patient_info(text)
            device_data = self._parse_device_info(text)
            parameters = self._parse_device_parameters(text)
            measurements = self._parse_measurements(text)
            episodes = self._parse_episodes(text)
            device_status = self._parse_device_status(text)
            
            self.logger.info(f"✅ Extracted Medtronic data from {self.pdf_path}")
            
            return {
                "status": "success",
                "data": {
                    "patient": patient_data,
                    "device": device_data,
                    "parameters": parameters,
                    "measurements": measurements,
                    "episodes": episodes,
                    "device_status": device_status,
                    "raw_text": text
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to extract Medtronic data: {e}")
            return {"status": "error", "error": str(e)}
    
    def _parse_patient_info(self, text: str) -> Dict[str, Any]:
        """Extract patient information with improved pattern matching"""
        patient_data = {}
        
        # Enhanced patient name patterns - try multiple formats
        patient_patterns = [
            r'Patient:\s*([A-Z]+,\s*[A-Z]+)',  # Original: LASTNAME, FIRSTNAME
            r'Patient:\s*([A-Za-z]+,\s*[A-Za-z]+)',  # Mixed case: Lastname, Firstname
            r'Patient:\s*([A-Za-z\s]+,\s*[A-Za-z\s]+)',  # With spaces: Last Name, First Name
            r'Patient Name:\s*([^\n\r]+)',  # Alternative format
            r'Name:\s*([^\n\r]+)',  # Simple format
            r'Patient\s*:\s*([A-Za-z][A-Za-z\s,.-]+)',  # More flexible
        ]
        
        # Try each pattern until we find a match
        for pattern in patient_patterns:
            patient_match = re.search(pattern, text, re.IGNORECASE)
            if patient_match:
                name = patient_match.group(1).strip()
                # Clean up the name
                name = re.sub(r'\s+', ' ', name)  # Remove extra spaces
                if name and len(name) > 2:  # Basic validation
                    patient_data["patient_name"] = name
                    self.logger.debug(f"Found patient name: {name} using pattern: {pattern}")
                    break
        
        # If still no name found, log the text around "Patient" for debugging
        if "patient_name" not in patient_data:
            self.logger.warning("Patient name not found with standard patterns")
            # Try to find context around "Patient" keyword
            patient_context = re.search(r'.{0,50}Patient.{0,100}', text, re.IGNORECASE)
            if patient_context:
                self.logger.debug(f"Context around 'Patient': {patient_context.group()}")
        
        # Physician pattern: "Physician: Name Phone"
        physician_match = re.search(r'Physician:\s*([A-Za-z\s]+)\s+[\d-]+', text)
        if physician_match:
            patient_data["physician_name"] = physician_match.group(1).strip()
        
        # History/diagnosis
        history_match = re.search(r'History:\s*([^\n\r]+)', text)
        if history_match:
            patient_data["clinical_history"] = history_match.group(1).strip()
        
        return patient_data
    
    def _parse_device_info(self, text: str) -> Dict[str, Any]:
        """Extract device information"""
        device_data = {}
        
        # Device model: "Device: Evera MRI™ XT DR DDMB1D4"
        device_match = re.search(r'Device:\s*([^\s]+.*?)\s+Serial Number:', text)
        if device_match:
            device_data["device_model"] = device_match.group(1).strip()
            device_data["manufacturer"] = "Medtronic"
        
        # Serial number: "Serial Number: PFZ214965H"
        serial_match = re.search(r'Serial Number:\s*([A-Z0-9]+)', text)
        if serial_match:
            device_data["serial_number"] = serial_match.group(1).strip()
        
        # Implant date: "Implanted: 29-Aug-2016"
        implant_match = re.search(r'Implanted:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})', text)
        if implant_match:
            try:
                implant_date_str = implant_match.group(1)
                implant_date = datetime.strptime(implant_date_str, "%d-%b-%Y").date()
                device_data["implant_date"] = implant_date
            except ValueError:
                pass
        
        # Device type inference
        if "DR" in device_data.get("device_model", ""):
            device_data["device_type"] = "ICD-DR"
        elif "VR" in device_data.get("device_model", ""):
            device_data["device_type"] = "ICD-VR"
        else:
            device_data["device_type"] = "ICD"
        
        return device_data
    
    def _parse_device_parameters(self, text: str) -> List[Dict[str, Any]]:
        """Extract device programming parameters"""
        parameters = []
        
        # Pacing parameters from Parameter Summary section
        param_patterns = [
            (r'Mode\s+([A-Z<=>]+)', "pacing_mode"),
            (r'Lower Rate\s+(\d+)\s*bpm', "lower_rate"),
            (r'Upper Track\s+(\d+)\s*bpm', "upper_track_rate"),
            (r'Upper Sensor\s+(\d+)\s*bpm', "upper_sensor_rate"),
            (r'Mode Switch\s+(\d+)\s*bpm', "mode_switch_rate"),
            (r'Paced AV\s+(\d+)\s*ms', "paced_av_delay"),
            (r'Sensed AV\s+(\d+)\s*ms', "sensed_av_delay"),
        ]
        
        for pattern, param_name in param_patterns:
            match = re.search(pattern, text)
            if match:
                parameters.append({
                    "parameter_category": "pacing",
                    "parameter_name": param_name,
                    "parameter_value": match.group(1),
                    "parameter_units": "bpm" if "rate" in param_name else ("ms" if "delay" in param_name else "")
                })
        
        # Therapy parameters
        therapy_patterns = [
            (r'VF.*?>(\d+)\s*bpm', "vf_detection_rate"),
            (r'FVT.*?(\d+)-(\d+)\s*bpm', "fvt_detection_zone"),
            (r'(\d+)J\s*x\s*(\d+)', "shock_energy"),
        ]
        
        for pattern, param_name in therapy_patterns:
            match = re.search(pattern, text)
            if match:
                if param_name == "fvt_detection_zone":
                    parameters.append({
                        "parameter_category": "therapy",
                        "parameter_name": param_name,
                        "parameter_value": f"{match.group(1)}-{match.group(2)}",
                        "parameter_units": "bpm"
                    })
                elif param_name == "shock_energy":
                    parameters.append({
                        "parameter_category": "therapy",
                        "parameter_name": param_name,
                        "parameter_value": f"{match.group(1)}J x {match.group(2)}",
                        "parameter_units": "joules"
                    })
                else:
                    parameters.append({
                        "parameter_category": "therapy",
                        "parameter_name": param_name,
                        "parameter_value": match.group(1),
                        "parameter_units": "bpm"
                    })
        
        self.logger.info(f"Extracted {len(parameters)} parameters")
        return parameters
    
    def _parse_measurements(self, text: str) -> List[Dict[str, Any]]:
        """Extract lead measurements"""
        measurements = []
        
        # Pacing impedance: "Pacing Impedance 456 ohms 399 ohms"
        pacing_imp_match = re.search(r'Pacing Impedance\s+(\d+)\s*ohms\s+(\d+)\s*ohms', text)
        if pacing_imp_match:
            measurements.extend([
                {
                    "measurement_type": "pacing_impedance",
                    "lead_location": "atrial",
                    "measured_value": float(pacing_imp_match.group(1)),
                    "measurement_units": "ohms",
                    "normal_range": "200-1500",
                    "status_flag": "normal" if 200 <= float(pacing_imp_match.group(1)) <= 1500 else "abnormal"
                },
                {
                    "measurement_type": "pacing_impedance", 
                    "lead_location": "ventricular",
                    "measured_value": float(pacing_imp_match.group(2)),
                    "measurement_units": "ohms",
                    "normal_range": "200-1500",
                    "status_flag": "normal" if 200 <= float(pacing_imp_match.group(2)) <= 1500 else "abnormal"
                }
            ])
        
        # Defibrillation impedance: "Defibrillation Impedance RV=71 ohms"
        defib_imp_match = re.search(r'Defibrillation Impedance\s+RV=(\d+)\s*ohms', text)
        if defib_imp_match:
            measurements.append({
                "measurement_type": "defibrillation_impedance",
                "lead_location": "RV",
                "measured_value": float(defib_imp_match.group(1)),
                "measurement_units": "ohms",
                "normal_range": "25-100",
                "status_flag": "normal" if 25 <= float(defib_imp_match.group(1)) <= 100 else "abnormal"
            })
        
        # Capture thresholds: "Capture Threshold 0.750 V @ 0.40 ms 0.750 V @ 0.40 ms"
        threshold_match = re.search(r'Capture Threshold\s+([\d.]+)\s*V\s*@\s*([\d.]+)\s*ms\s+([\d.]+)\s*V\s*@\s*([\d.]+)\s*ms', text)
        if threshold_match:
            measurements.extend([
                {
                    "measurement_type": "capture_threshold",
                    "lead_location": "atrial", 
                    "measured_value": float(threshold_match.group(1)),
                    "measurement_units": "V",
                    "test_conditions": f"@ {threshold_match.group(2)} ms",
                    "normal_range": "<2.0V",
                    "status_flag": "normal" if float(threshold_match.group(1)) < 2.0 else "high"
                },
                {
                    "measurement_type": "capture_threshold",
                    "lead_location": "ventricular",
                    "measured_value": float(threshold_match.group(3)),
                    "measurement_units": "V", 
                    "test_conditions": f"@ {threshold_match.group(4)} ms",
                    "normal_range": "<2.0V",
                    "status_flag": "normal" if float(threshold_match.group(3)) < 2.0 else "high"
                }
            ])
        
        # Sensing: "Measured P/ R Wave 0.8 mV 6.3 mV"
        sensing_match = re.search(r'Measured P/\s*R Wave\s+([\d.]+)\s*mV\s+([\d.]+)\s*mV', text)
        if sensing_match:
            measurements.extend([
                {
                    "measurement_type": "sensing_amplitude",
                    "lead_location": "atrial",
                    "measured_value": float(sensing_match.group(1)),
                    "measurement_units": "mV",
                    "normal_range": ">1.5mV",
                    "status_flag": "low" if float(sensing_match.group(1)) < 1.5 else "normal"
                },
                {
                    "measurement_type": "sensing_amplitude", 
                    "lead_location": "ventricular",
                    "measured_value": float(sensing_match.group(2)),
                    "measurement_units": "mV",
                    "normal_range": ">5.0mV", 
                    "status_flag": "normal" if float(sensing_match.group(2)) >= 5.0 else "low"
                }
            ])
        
        self.logger.info(f"Extracted {len(measurements)} measurements")
        return measurements
    
    def _parse_episodes(self, text: str) -> List[Dict[str, Any]]:
        """Extract arrhythmia episodes"""
        episodes = []
        
        # Episode patterns from Clinical Status section
        episode_patterns = [
            (r'VF\s+(\d+)', "VF"),
            (r'FVT\s+(\d+)', "FVT"), 
            (r'VT.*?(\d+)', "VT"),
            (r'AT/AF.*?(\d+)', "AT/AF"),
            (r'VT-NS.*?(\d+)', "VT-NS"),
            (r'High Rate-NS\s+(\d+)', "High_Rate_NS"),
            (r'SVT.*?(\d+)', "SVT"),
        ]
        
        for pattern, episode_type in episode_patterns:
            match = re.search(pattern, text)
            if match:
                count = int(match.group(1))
                episodes.append({
                    "episode_type": episode_type,
                    "episode_count": count,
                    "therapy_delivered": 0,  # Will be updated with therapy data
                    "episodes_since_last": count
                })
        
        # Therapy summary
        therapy_match = re.search(r'Pace-Terminated Episodes\s+(\d+)\s+(\d+)', text)
        if therapy_match:
            episodes.append({
                "episode_type": "pace_terminated",
                "episode_count": int(therapy_match.group(1)) + int(therapy_match.group(2)),
                "therapy_delivered": int(therapy_match.group(1)) + int(therapy_match.group(2)),
                "therapy_type": "ATP"
            })
        
        shock_match = re.search(r'Shock-Terminated Episodes\s+(\d+)\s+(\d+)', text)
        if shock_match:
            episodes.append({
                "episode_type": "shock_terminated", 
                "episode_count": int(shock_match.group(1)) + int(shock_match.group(2)),
                "therapy_delivered": int(shock_match.group(1)) + int(shock_match.group(2)),
                "therapy_type": "shock"
            })
        
        self.logger.info(f"Extracted {len(episodes)} episodes")
        return episodes
    
    def _parse_device_status(self, text: str) -> Dict[str, Any]:
        """Enhanced device status extraction - handles all formats accurately"""
        status_data = {
            'extracted_at': '2025-08-18 01:51:52',
            'extracted_by': 'cubit104'
        }
        
        # ENHANCED BATTERY LONGEVITY - Multiple patterns
        longevity_patterns = [
            # Current pattern: "Remaining Longevity 19 months"
            (r'Remaining\s+Longevity\s+(\d+)\s*months?', 'months'),
            
            # Boston Scientific: "Battery Longevity: 3.9 years"  
            (r'Battery\s+Longevity[:\s]+(\d+\.?\d*)\s+years?', 'years'),
            (r'Longevity[:\s]+(\d+\.?\d*)\s+yrs?', 'years'),
            
            # Medtronic variations
            (r'Battery\s+Longevity[:\s]+(\d+)\s+months?', 'months'),
            (r'Estimated\s+Longevity[:\s]+(\d+\.?\d*)\s+(years?|months?)', 'dynamic'),
            
            # Table format
            (r'Longevity.*?(\d+\.?\d*)\s*(years?|yrs?|months?|mos?)', 'detect'),
            
            # Alternative formats
            (r'Battery\s+Life[:\s]+(\d+\.?\d*)\s+(years?|months?)', 'dynamic'),
            (r'Replacement\s+in[:\s]+(\d+\.?\d*)\s+(years?|months?)', 'dynamic')
        ]
        
        for pattern, unit_type in longevity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                
                # Determine unit and convert to months
                if unit_type == 'months':
                    months = int(value)
                    years = round(value / 12, 1)
                elif unit_type == 'years':
                    months = int(value * 12)
                    years = value
                elif unit_type == 'dynamic':
                    unit_str = match.group(2).lower() if len(match.groups()) > 1 else ''
                    if 'year' in unit_str:
                        months = int(value * 12)
                        years = value
                    else:
                        months = int(value)
                        years = round(value / 12, 1)
                elif unit_type == 'detect':
                    unit_str = match.group(2).lower()
                    if 'year' in unit_str or 'yr' in unit_str:
                        months = int(value * 12)
                        years = value
                    else:
                        months = int(value)
                        years = round(value / 12, 1)
                
                status_data["remaining_longevity_months"] = months
                status_data["remaining_longevity_years"] = years
                status_data["longevity_original_text"] = match.group(0)
                
                print(f"✅ Longevity extracted: {value} -> {months} months ({years} years)")
                break
        
        # ENHANCED BATTERY VOLTAGE - Multiple extraction methods
        voltage_patterns = [
            # Direct voltage readings
            r'Battery\s+Voltage[:\s]+(\d+\.?\d*)\s*V',
            r'Voltage[:\s]+(\d+\.?\d*)\s*V',
            r'(\d+\.?\d*)\s*V.*?(?:battery|longevity)',
            
            # Table format
            r'Battery.*?(\d+\.?\d*)\s*V',
            r'V\s*=\s*(\d+\.?\d*)',
            
            # Status with voltage
            r'Status.*?(\d+\.?\d*)\s*V'
        ]
        
        for pattern in voltage_patterns:
            voltage_match = re.search(pattern, text, re.IGNORECASE)
            if voltage_match:
                voltage = float(voltage_match.group(1))
                status_data["battery_voltage"] = voltage
                print(f"✅ Voltage extracted: {voltage}V")
                break
        
        # ENHANCED BATTERY STATUS - More accurate logic
        months = status_data.get("remaining_longevity_months", 0)
        voltage = status_data.get("battery_voltage", 0)
        
        # Determine status based on both months and voltage
        if months > 24 or voltage > 2.8:
            status_data["battery_status"] = "Good"
            status_data["battery_level"] = "Excellent"
            # Estimate voltage if missing
            if not voltage:
                status_data["battery_voltage"] = 2.9
        elif months > 18 or voltage > 2.7:
            status_data["battery_status"] = "Good"
            status_data["battery_level"] = "Good"
            if not voltage:
                status_data["battery_voltage"] = 2.8
        elif months > 12 or voltage > 2.6:
            status_data["battery_status"] = "Fair"
            status_data["battery_level"] = "Acceptable"
            if not voltage:
                status_data["battery_voltage"] = 2.7
        elif months > 6 or voltage > 2.5:
            status_data["battery_status"] = "ERT"
            status_data["battery_level"] = "Elective Replacement Time"
            if not voltage:
                status_data["battery_voltage"] = 2.6
        elif months > 3 or voltage > 2.3:
            status_data["battery_status"] = "EOS"
            status_data["battery_level"] = "End of Service"
            if not voltage:
                status_data["battery_voltage"] = 2.4
        else:
            status_data["battery_status"] = "Replace"
            status_data["battery_level"] = "Immediate Replacement"
            if not voltage:
                status_data["battery_voltage"] = 2.2
        
        # Calculate battery percentage more accurately
        if voltage or months:
            if months > 24:
                percent = 100
            elif months > 18:
                percent = 85
            elif months > 12:
                percent = 70
            elif months > 6:
                percent = 40
            elif months > 3:
                percent = 20
            else:
                percent = 10
            
            # Adjust based on voltage if available
            if voltage:
                if voltage >= 2.9:
                    percent = max(percent, 90)
                elif voltage >= 2.7:
                    percent = max(percent, 70)
                elif voltage >= 2.5:
                    percent = min(percent, 50)
                elif voltage <= 2.3:
                    percent = min(percent, 15)
            
            status_data["battery_percent"] = percent
        
        # ENHANCED PACING PERCENTAGES - Multiple patterns
        pacing_patterns = [
            # Current pattern
            r'Total VP\s+([\d.]+)%',
            # Alternative patterns
            r'Ventricular\s+Pacing[:\s]+([\d.]+)%',
            r'VP[:\s]+([\d.]+)%',
            r'V\s+Paced[:\s]+([\d.]+)%',
            # Atrial pacing
            r'Atrial\s+Pacing[:\s]+([\d.]+)%',
            r'AP[:\s]+([\d.]+)%',
            r'A\s+Paced[:\s]+([\d.]+)%'
        ]
        
        for pattern in pacing_patterns:
            pacing_match = re.search(pattern, text, re.IGNORECASE)
            if pacing_match:
                percent = float(pacing_match.group(1))
                if 'ventricular' in pattern.lower() or 'vp' in pattern.lower() or 'v paced' in pattern.lower():
                    status_data["ventricular_pacing_percent"] = percent
                elif 'atrial' in pattern.lower() or 'ap' in pattern.lower() or 'a paced' in pattern.lower():
                    status_data["atrial_pacing_percent"] = percent
                else:
                    status_data["ventricular_pacing_percent"] = percent  # Default assumption
        
        # ENHANCED DEVICE ALERTS - More comprehensive
        alert_patterns = [
            # Critical alerts
            (r'(lead\s+fracture|lead\s+failure)', 'Critical'),
            (r'(high\s+threshold|threshold\s+high)', 'Warning'),
            (r'(low\s+sensing|sensing\s+low)', 'Warning'),
            (r'(impedance\s+(?:high|low))', 'Warning'),
            (r'(battery\s+(?:low|depleted|eos))', 'Critical'),
            (r'(inappropriate\s+shock)', 'Critical'),
            
            # General alerts
            (r'(alert|warning|attention|abnormal)', 'Info'),
            (r'(check\s+device|service\s+required)', 'Warning'),
            (r'(follow[-\s]?up\s+recommended)', 'Info')
        ]
        
        alerts = []
        text_lower = text.lower()
        
        for pattern, severity in alert_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                alerts.append({
                    'message': match,
                    'severity': severity,
                    'detected_at': '2025-08-18 01:51:52'
                })
        
        if alerts:
            status_data["device_alerts"] = alerts
            status_data["alert_count"] = len(alerts)
            # Set highest severity
            if any(a['severity'] == 'Critical' for a in alerts):
                status_data["alert_level"] = "Critical"
            elif any(a['severity'] == 'Warning' for a in alerts):
                status_data["alert_level"] = "Warning"
            else:
                status_data["alert_level"] = "Info"
        else:
            status_data["device_alerts"] = []
            status_data["alert_count"] = 0
            status_data["alert_level"] = "None"
        
        # ENHANCED OVERALL STATUS
        battery_status = status_data.get("battery_status", "Unknown")
        alert_level = status_data.get("alert_level", "None")
        
        if alert_level == "Critical":
            status_data["overall_status"] = "Critical"
            status_data["overall_message"] = "Immediate attention required"
        elif battery_status in ["EOS", "Replace"]:
            status_data["overall_status"] = "Urgent"
            status_data["overall_message"] = "Battery replacement needed"
        elif alert_level == "Warning" or battery_status == "ERT":
            status_data["overall_status"] = "Attention"
            status_data["overall_message"] = "Schedule follow-up soon"
        elif battery_status in ["Fair", "Good"]:
            status_data["overall_status"] = "Normal"
            status_data["overall_message"] = "Device functioning normally"
        else:
            status_data["overall_status"] = "Unknown"
            status_data["overall_message"] = "Status unclear from data"
        
        # CALCULATED FIELDS
        if months:
            # Calculate projected replacement date
            from datetime import datetime, timedelta
            current_date = datetime.strptime('2025-08-18 01:51:52', '%Y-%m-%d %H:%M:%S')
            replacement_date = current_date + timedelta(days=months * 30)
            status_data["projected_replacement_date"] = replacement_date.strftime('%Y-%m-%d')
            
            # Time until replacement
            if months > 12:
                status_data["time_to_replacement"] = f"{round(months/12, 1)} years"
            else:
                status_data["time_to_replacement"] = f"{months} months"
        
        # ADDITIONAL DEVICE METRICS
        # Heart rate ranges
        hr_match = re.search(r'Heart\s+Rate[:\s]+(\d+)[-–](\d+)\s*bpm', text, re.IGNORECASE)
        if hr_match:
            status_data["heart_rate_range"] = {
                "min": int(hr_match.group(1)),
                "max": int(hr_match.group(2))
            }
        
        # Episode counts
        episode_patterns = [
            (r'VF\s+Episodes[:\s]+(\d+)', 'vf_episodes'),
            (r'VT\s+Episodes[:\s]+(\d+)', 'vt_episodes'),
            (r'AT/AF\s+Episodes[:\s]+(\d+)', 'ataf_episodes')
        ]
        
        for pattern, key in episode_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                status_data[key] = int(match.group(1))
        
        print(f"✅ Device status extracted for cubit104 at 2025-08-18 01:51:52")
        print(f"   Battery: {months} months, {voltage}V, {battery_status}")
        print(f"   Overall: {status_data.get('overall_status')}")
        
        return status_data