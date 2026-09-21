"""
Advanced ML-Based Device Classification System
Uses machine learning to intelligently classify and categorize unknown devices
"""

import asyncio
import logging
import json
import re
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import hashlib

from core.udp_core import DeviceManifest, DeviceCapability

logger = logging.getLogger(__name__)

@dataclass
class DeviceSignature:
    """Device signature for ML classification"""
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    device_class: Optional[str] = None
    interface_descriptors: List[str] = None
    manufacturer_string: Optional[str] = None
    product_string: Optional[str] = None
    serial_number: Optional[str] = None
    capabilities: List[str] = None
    protocol_fingerprint: Dict[str, Any] = None
    power_characteristics: Dict[str, float] = None
    communication_patterns: Dict[str, Any] = None

class DeviceClassifier:
    """Advanced ML-based device classification system"""
    
    def __init__(self):
        self.device_database = {}
        self.classification_rules = {}
        self.ml_model = None
        self.feature_extractors = {}
        self.confidence_thresholds = {
            "high": 0.9,
            "medium": 0.7,
            "low": 0.5
        }
        self.classification_history = []
        self.learning_enabled = True
        
        # Initialize classification database
        self._initialize_device_database()
        self._initialize_classification_rules()
        self._initialize_feature_extractors()
    
    def _initialize_device_database(self):
        """Initialize comprehensive device database with known signatures"""
        self.device_database = {
            # Camera devices
            "cameras": {
                "usb_webcam": {
                    "signatures": [
                        {"vendor_id": "046d", "product_id": "082d", "manufacturer": "Logitech"},
                        {"vendor_id": "0ac8", "manufacturer": "Z-Star"},
                        {"device_class": "14", "interface_class": "0e"}  # Video class
                    ],
                    "type": "webcam",
                    "category": "input_device",
                    "capabilities": ["video_capture", "image_capture", "streaming"]
                },
                "thermal_camera": {
                    "signatures": [
                        {"manufacturer": "FLIR", "product_string": "thermal"},
                        {"product_string": "infrared", "capabilities": ["thermal_imaging"]}
                    ],
                    "type": "thermal_camera",
                    "category": "input_device",
                    "capabilities": ["thermal_imaging", "temperature_measurement"]
                }
            },
            
            # Storage devices  
            "storage": {
                "usb_drive": {
                    "signatures": [
                        {"device_class": "08", "interface_class": "08", "protocol": "50"},
                        {"product_string": "usb.*drive", "device_class": "00"}
                    ],
                    "type": "usb_storage",
                    "category": "storage_device",
                    "capabilities": ["mass_storage", "removable_media"]
                },
                "ssd_drive": {
                    "signatures": [
                        {"product_string": "ssd", "interface": "sata"},
                        {"manufacturer": "Samsung.*SSD", "capabilities": ["high_speed_storage"]}
                    ],
                    "type": "ssd",
                    "category": "storage_device", 
                    "capabilities": ["mass_storage", "high_speed", "non_volatile"]
                }
            },
            
            # Sensors
            "sensors": {
                "temperature_sensor": {
                    "signatures": [
                        {"product_string": "temperature", "capabilities": ["temperature_measurement"]},
                        {"manufacturer": "Sensirion", "product_string": "SHT"}
                    ],
                    "type": "temperature_sensor",
                    "category": "input_device",
                    "capabilities": ["temperature_measurement", "environmental_sensing"]
                },
                "accelerometer": {
                    "signatures": [
                        {"product_string": "accelerometer|accel|gyro", "capabilities": ["motion_sensing"]},
                        {"manufacturer": "ST.*LSM", "device_class": "03"}
                    ],
                    "type": "motion_sensor",
                    "category": "input_device", 
                    "capabilities": ["motion_sensing", "orientation", "vibration_detection"]
                }
            },
            
            # Audio devices
            "audio": {
                "usb_microphone": {
                    "signatures": [
                        {"device_class": "01", "interface_class": "01", "subclass": "02"},
                        {"product_string": "microphone|mic", "capabilities": ["audio_capture"]}
                    ],
                    "type": "usb_microphone",
                    "category": "input_device",
                    "capabilities": ["audio_capture", "voice_recording", "streaming"]
                },
                "usb_speaker": {
                    "signatures": [
                        {"device_class": "01", "interface_class": "01", "subclass": "01"},
                        {"product_string": "speaker|audio.*out", "capabilities": ["audio_output"]}
                    ],
                    "type": "usb_speaker", 
                    "category": "output_device",
                    "capabilities": ["audio_output", "sound_reproduction"]
                }
            },
            
            # Network devices
            "network": {
                "wifi_adapter": {
                    "signatures": [
                        {"device_class": "02", "interface_class": "02"},
                        {"product_string": "wifi|wireless|802.11", "capabilities": ["wireless_communication"]}
                    ],
                    "type": "wifi_adapter",
                    "category": "communication_device", 
                    "capabilities": ["wireless_communication", "network_access", "internet_connectivity"]
                },
                "ethernet_adapter": {
                    "signatures": [
                        {"product_string": "ethernet|eth.*adapter", "capabilities": ["wired_communication"]},
                        {"interface_class": "02", "protocol": "00"}
                    ],
                    "type": "ethernet_adapter",
                    "category": "communication_device",
                    "capabilities": ["wired_communication", "network_access", "high_speed_data"]
                }
            }
        }
    
    def _initialize_classification_rules(self):
        """Initialize rule-based classification logic"""
        self.classification_rules = {
            "usb_device_class": {
                "01": "audio_device",      # Audio
                "02": "communication_device", # CDC (Communications)
                "03": "hid_device",        # Human Interface Device  
                "06": "imaging_device",    # Still Image Capture
                "07": "printer",           # Printer
                "08": "mass_storage",      # Mass Storage
                "09": "hub_device",        # Hub
                "0A": "cdc_data",         # CDC-Data
                "0B": "smart_card",       # Chip/Smart Card
                "0D": "security_device",   # Content Security
                "0E": "video_device",      # Video
                "0F": "healthcare_device", # Personal Healthcare
                "10": "audio_video",       # Audio/Video Devices
                "11": "billboard_device",  # Billboard Device
                "DC": "diagnostic_device", # Diagnostic Device
                "E0": "wireless_controller", # Wireless Controller
                "EF": "miscellaneous",     # Miscellaneous
                "FE": "application_specific", # Application Specific
                "FF": "vendor_specific"    # Vendor Specific
            },
            
            "manufacturer_patterns": {
                r"logitech": "peripheral_device",
                r"microsoft": "computer_accessory",
                r"apple": "consumer_electronics",
                r"samsung": "electronics_device",
                r"intel": "computing_component",
                r"nvidia": "graphics_device",
                r"amd": "processor_device",
                r"raspberry.*pi": "embedded_computer",
                r"arduino": "microcontroller",
                r"texas.*instruments": "electronic_component",
                r"st.*micro": "microcontroller",
                r"analog.*devices": "analog_component"
            },
            
            "product_patterns": {
                r"keyboard": "keyboard",
                r"mouse": "mouse", 
                r"webcam|camera": "camera",
                r"printer": "printer",
                r"scanner": "scanner",
                r"monitor|display": "display",
                r"speaker|audio": "audio_device",
                r"microphone|mic": "microphone",
                r"hub": "usb_hub",
                r"drive|storage": "storage_device",
                r"adapter|dongle": "adapter",
                r"sensor": "sensor_device",
                r"controller|gamepad": "game_controller"
            }
        }
    
    def _initialize_feature_extractors(self):
        """Initialize feature extraction functions"""
        self.feature_extractors = {
            "usb_features": self._extract_usb_features,
            "network_features": self._extract_network_features,
            "protocol_features": self._extract_protocol_features,
            "string_features": self._extract_string_features,
            "capability_features": self._extract_capability_features,
            "power_features": self._extract_power_features
        }
    
    async def classify_device(self, device: DeviceManifest) -> str:
        """Main device classification method"""
        try:
            logger.info(f"Classifying device: {device.device_id}")
            
            # Extract device signature
            signature = await self._extract_device_signature(device)
            
            # Try exact match first
            exact_match = await self._find_exact_match(signature)
            if exact_match:
                confidence = 0.95
                await self._record_classification(device.device_id, exact_match, confidence, "exact_match")
                return exact_match
            
            # Try rule-based classification
            rule_match = await self._classify_by_rules(signature)
            if rule_match:
                confidence = 0.85
                await self._record_classification(device.device_id, rule_match, confidence, "rule_based")
                return rule_match
            
            # Try ML-based classification
            ml_match = await self._classify_by_ml(signature)
            if ml_match:
                confidence = ml_match.get("confidence", 0.7)
                device_type = ml_match.get("type", "unknown")
                await self._record_classification(device.device_id, device_type, confidence, "ml_based")
                return device_type
            
            # Try pattern matching
            pattern_match = await self._classify_by_patterns(signature)
            if pattern_match:
                confidence = 0.6
                await self._record_classification(device.device_id, pattern_match, confidence, "pattern_match")
                return pattern_match
            
            # Fallback to generic classification
            generic_type = await self._generic_classification(signature)
            confidence = 0.3
            await self._record_classification(device.device_id, generic_type, confidence, "generic")
            return generic_type
            
        except Exception as e:
            logger.error(f"Error classifying device {device.device_id}: {e}")
            return "unknown"
    
    async def _extract_device_signature(self, device: DeviceManifest) -> DeviceSignature:
        """Extract comprehensive device signature for classification"""
        signature = DeviceSignature()
        
        # Extract basic identifiers
        signature.vendor_id = device.attributes.get("vendor_id")
        signature.product_id = device.attributes.get("product_id")
        signature.device_class = device.attributes.get("device_class")
        signature.manufacturer_string = device.manufacturer
        signature.product_string = device.model
        signature.serial_number = device.serial_number
        
        # Extract capabilities
        signature.capabilities = [cap.capability_id for cap in device.capabilities]
        
        # Extract protocol information
        signature.protocol_fingerprint = {
            "supported_protocols": device.supported_protocols,
            "connection_type": device.connection_info.get("type"),
            "address": device.connection_info.get("address")
        }
        
        # Extract power characteristics
        signature.power_characteristics = {
            "power_consumption": device.attributes.get("power_consumption", 0),
            "voltage": device.attributes.get("voltage", 0),
            "current": device.attributes.get("current", 0)
        }
        
        return signature
    
    async def _find_exact_match(self, signature: DeviceSignature) -> Optional[str]:
        """Find exact match in device database"""
        for category, devices in self.device_database.items():
            for device_type, device_info in devices.items():
                for sig in device_info["signatures"]:
                    if await self._matches_signature(signature, sig):
                        return device_info["type"]
        return None
    
    async def _matches_signature(self, device_sig: DeviceSignature, db_sig: Dict[str, Any]) -> bool:
        """Check if device signature matches database signature"""
        # Check vendor/product ID match
        if "vendor_id" in db_sig and device_sig.vendor_id:
            if db_sig["vendor_id"].lower() != device_sig.vendor_id.lower():
                return False
        
        if "product_id" in db_sig and device_sig.product_id:
            if db_sig["product_id"].lower() != device_sig.product_id.lower():
                return False
        
        # Check device class match
        if "device_class" in db_sig and device_sig.device_class:
            if db_sig["device_class"] != device_sig.device_class:
                return False
        
        # Check manufacturer string match
        if "manufacturer" in db_sig and device_sig.manufacturer_string:
            pattern = db_sig["manufacturer"].lower()
            manufacturer = device_sig.manufacturer_string.lower()
            if not re.search(pattern, manufacturer):
                return False
        
        # Check product string match  
        if "product_string" in db_sig and device_sig.product_string:
            pattern = db_sig["product_string"].lower()
            product = device_sig.product_string.lower()
            if not re.search(pattern, product):
                return False
        
        # Check capabilities match
        if "capabilities" in db_sig and device_sig.capabilities:
            required_caps = db_sig["capabilities"]
            device_caps = device_sig.capabilities
            if not any(cap in device_caps for cap in required_caps):
                return False
        
        return True
    
    async def _classify_by_rules(self, signature: DeviceSignature) -> Optional[str]:
        """Classify using rule-based approach"""
        # USB device class classification
        if signature.device_class and signature.device_class in self.classification_rules["usb_device_class"]:
            return self.classification_rules["usb_device_class"][signature.device_class]
        
        # Manufacturer pattern matching
        if signature.manufacturer_string:
            manufacturer = signature.manufacturer_string.lower()
            for pattern, device_type in self.classification_rules["manufacturer_patterns"].items():
                if re.search(pattern, manufacturer):
                    return device_type
        
        # Product pattern matching
        if signature.product_string:
            product = signature.product_string.lower()
            for pattern, device_type in self.classification_rules["product_patterns"].items():
                if re.search(pattern, product):
                    return device_type
        
        return None
    
    async def _classify_by_ml(self, signature: DeviceSignature) -> Optional[Dict[str, Any]]:
        """Classify using machine learning model"""
        try:
            # Extract feature vector
            features = await self._extract_feature_vector(signature)
            
            # Simple ML classification using feature matching
            # In a real implementation, this would use a trained ML model
            classification_scores = {}
            
            # Score based on feature similarity
            for category, devices in self.device_database.items():
                for device_type, device_info in devices.items():
                    score = await self._calculate_similarity_score(features, device_info)
                    classification_scores[device_info["type"]] = score
            
            # Find best match
            if classification_scores:
                best_match = max(classification_scores.items(), key=lambda x: x[1])
                if best_match[1] > self.confidence_thresholds["low"]:
                    return {
                        "type": best_match[0],
                        "confidence": best_match[1],
                        "scores": classification_scores
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"ML classification error: {e}")
            return None
    
    async def _extract_feature_vector(self, signature: DeviceSignature) -> np.ndarray:
        """Extract numerical feature vector for ML classification"""
        features = []
        
        # Vendor/Product ID features (hash to numbers)
        if signature.vendor_id:
            features.append(int(signature.vendor_id, 16) % 1000)
        else:
            features.append(0)
            
        if signature.product_id:
            features.append(int(signature.product_id, 16) % 1000)  
        else:
            features.append(0)
        
        # Device class feature
        if signature.device_class:
            features.append(int(signature.device_class, 16))
        else:
            features.append(0)
        
        # String features (hash to numbers)
        if signature.manufacturer_string:
            features.append(abs(hash(signature.manufacturer_string)) % 1000)
        else:
            features.append(0)
            
        if signature.product_string:
            features.append(abs(hash(signature.product_string)) % 1000)
        else:
            features.append(0)
        
        # Capability count
        features.append(len(signature.capabilities) if signature.capabilities else 0)
        
        # Protocol count  
        protocol_count = len(signature.protocol_fingerprint.get("supported_protocols", []))
        features.append(protocol_count)
        
        # Power features
        features.append(signature.power_characteristics.get("power_consumption", 0))
        
        return np.array(features)
    
    async def _calculate_similarity_score(self, features: np.ndarray, device_info: Dict[str, Any]) -> float:
        """Calculate similarity score between feature vector and known device"""
        # Simple similarity calculation
        # In practice, this would use a trained model or more sophisticated similarity metrics
        
        base_score = 0.5
        
        # Boost score if capabilities match
        device_caps = device_info.get("capabilities", [])
        if len(device_caps) > 0 and features[5] > 0:  # features[5] is capability count
            base_score += 0.2
        
        # Boost score based on category
        if device_info.get("category") == "input_device" and features[6] > 0:  # features[6] is protocol count
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    async def _classify_by_patterns(self, signature: DeviceSignature) -> Optional[str]:
        """Classify using string pattern matching"""
        # Combine all string information
        text_data = []
        if signature.manufacturer_string:
            text_data.append(signature.manufacturer_string.lower())
        if signature.product_string:
            text_data.append(signature.product_string.lower())
        
        combined_text = " ".join(text_data)
        
        # Look for common device patterns
        device_patterns = {
            r"camera|webcam|video": "camera",
            r"keyboard": "keyboard", 
            r"mouse": "mouse",
            r"printer": "printer",
            r"scanner": "scanner",
            r"display|monitor": "display",
            r"speaker|audio.*out": "speaker",
            r"microphone|mic": "microphone",
            r"storage|drive|disk": "storage_device",
            r"network|wifi|ethernet": "network_device",
            r"sensor": "sensor_device",
            r"controller|gamepad": "controller",
            r"hub": "usb_hub",
            r"adapter|dongle": "adapter"
        }
        
        for pattern, device_type in device_patterns.items():
            if re.search(pattern, combined_text):
                return device_type
        
        return None
    
    async def _generic_classification(self, signature: DeviceSignature) -> str:
        """Fallback generic classification"""
        # Classify based on basic characteristics
        if signature.capabilities:
            caps = signature.capabilities
            if any("audio" in cap for cap in caps):
                return "audio_device"
            elif any("video" in cap for cap in caps):
                return "video_device"
            elif any("storage" in cap for cap in caps):
                return "storage_device"
            elif any("network" in cap for cap in caps):
                return "network_device"
            elif any("sensor" in cap for cap in caps):
                return "sensor_device"
        
        # Classify based on protocol
        if signature.protocol_fingerprint:
            protocols = signature.protocol_fingerprint.get("supported_protocols", [])
            if "usb" in protocols:
                return "usb_device"
            elif "ethernet" in protocols:
                return "network_device"
            elif "bluetooth" in protocols:
                return "bluetooth_device"
            elif "wifi" in protocols:
                return "wifi_device"
        
        return "unknown_device"
    
    async def _record_classification(self, device_id: str, device_type: str, confidence: float, method: str):
        """Record classification result for learning and analytics"""
        record = {
            "device_id": device_id,
            "classified_type": device_type,
            "confidence": confidence,
            "method": method,
            "timestamp": datetime.now()
        }
        
        self.classification_history.append(record)
        
        # Keep only last 1000 classifications
        if len(self.classification_history) > 1000:
            self.classification_history.pop(0)
        
        logger.info(f"Classified {device_id} as {device_type} (confidence: {confidence:.3f}, method: {method})")
    
    async def get_classification_confidence(self, device: DeviceManifest) -> float:
        """Get confidence score for device classification"""
        signature = await self._extract_device_signature(device)
        
        # Check for exact match (highest confidence)
        if await self._find_exact_match(signature):
            return 0.95
        
        # Check rule-based match
        if await self._classify_by_rules(signature):
            return 0.85
        
        # Check ML-based classification
        ml_result = await self._classify_by_ml(signature)
        if ml_result:
            return ml_result.get("confidence", 0.7)
        
        # Check pattern match
        if await self._classify_by_patterns(signature):
            return 0.6
        
        # Generic classification has low confidence
        return 0.3
    
    async def learn_from_feedback(self, device_id: str, correct_type: str, user_feedback: Dict[str, Any]):
        """Learn from user feedback to improve classification"""
        if not self.learning_enabled:
            return
        
        # Find the original classification
        original_classification = None
        for record in reversed(self.classification_history):
            if record["device_id"] == device_id:
                original_classification = record
                break
        
        if not original_classification:
            logger.warning(f"No original classification found for device {device_id}")
            return
        
        # Record feedback
        feedback_record = {
            "device_id": device_id,
            "original_type": original_classification["classified_type"],
            "correct_type": correct_type,
            "original_confidence": original_classification["confidence"],
            "original_method": original_classification["method"],
            "user_feedback": user_feedback,
            "timestamp": datetime.now()
        }
        
        # Update classification database if needed
        if user_feedback.get("add_to_database", False):
            await self._add_to_database(device_id, correct_type, user_feedback)
        
        logger.info(f"Learning from feedback: {device_id} should be {correct_type}")
    
    async def _add_to_database(self, device_id: str, device_type: str, feedback: Dict[str, Any]):
        """Add new device signature to database based on feedback"""
        # This would typically update the ML model or add to the signature database
        # For now, just log the learning opportunity
        logger.info(f"Adding {device_id} as {device_type} to classification database")
    
    async def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification statistics and performance metrics"""
        if not self.classification_history:
            return {"total_classifications": 0}
        
        total = len(self.classification_history)
        method_counts = {}
        confidence_distribution = {"high": 0, "medium": 0, "low": 0}
        type_distribution = {}
        
        for record in self.classification_history:
            # Method distribution
            method = record["method"]
            method_counts[method] = method_counts.get(method, 0) + 1
            
            # Confidence distribution
            confidence = record["confidence"]
            if confidence >= self.confidence_thresholds["high"]:
                confidence_distribution["high"] += 1
            elif confidence >= self.confidence_thresholds["medium"]:
                confidence_distribution["medium"] += 1
            else:
                confidence_distribution["low"] += 1
            
            # Type distribution
            device_type = record["classified_type"]
            type_distribution[device_type] = type_distribution.get(device_type, 0) + 1
        
        return {
            "total_classifications": total,
            "method_distribution": method_counts,
            "confidence_distribution": confidence_distribution,
            "type_distribution": type_distribution,
            "average_confidence": sum(r["confidence"] for r in self.classification_history) / total,
            "success_rate_estimate": confidence_distribution["high"] / total if total > 0 else 0
        }
    
    # Feature extraction methods
    async def _extract_usb_features(self, signature: DeviceSignature) -> Dict[str, Any]:
        """Extract USB-specific features"""
        return {
            "vendor_id": signature.vendor_id,
            "product_id": signature.product_id,
            "device_class": signature.device_class,
            "has_serial": bool(signature.serial_number)
        }
    
    async def _extract_network_features(self, signature: DeviceSignature) -> Dict[str, Any]:
        """Extract network-specific features"""
        protocols = signature.protocol_fingerprint.get("supported_protocols", [])
        return {
            "has_wifi": "wifi" in protocols,
            "has_ethernet": "ethernet" in protocols,
            "has_bluetooth": "bluetooth" in protocols,
            "protocol_count": len(protocols)
        }
    
    async def _extract_protocol_features(self, signature: DeviceSignature) -> Dict[str, Any]:
        """Extract protocol-specific features"""
        return {
            "supported_protocols": signature.protocol_fingerprint.get("supported_protocols", []),
            "connection_type": signature.protocol_fingerprint.get("connection_type"),
            "has_address": bool(signature.protocol_fingerprint.get("address"))
        }
    
    async def _extract_string_features(self, signature: DeviceSignature) -> Dict[str, Any]:
        """Extract string-based features"""
        return {
            "manufacturer_length": len(signature.manufacturer_string) if signature.manufacturer_string else 0,
            "product_length": len(signature.product_string) if signature.product_string else 0,
            "has_manufacturer": bool(signature.manufacturer_string),
            "has_product": bool(signature.product_string),
            "has_serial": bool(signature.serial_number)
        }
    
    async def _extract_capability_features(self, signature: DeviceSignature) -> Dict[str, Any]:
        """Extract capability-based features"""
        caps = signature.capabilities or []
        return {
            "capability_count": len(caps),
            "has_audio": any("audio" in cap for cap in caps),
            "has_video": any("video" in cap for cap in caps), 
            "has_storage": any("storage" in cap for cap in caps),
            "has_network": any("network" in cap for cap in caps),
            "has_sensor": any("sensor" in cap for cap in caps)
        }
    
    async def _extract_power_features(self, signature: DeviceSignature) -> Dict[str, Any]:
        """Extract power-related features"""
        power = signature.power_characteristics or {}
        return {
            "power_consumption": power.get("power_consumption", 0),
            "voltage": power.get("voltage", 0),
            "current": power.get("current", 0),
            "is_high_power": power.get("power_consumption", 0) > 500,  # > 0.5W
            "is_bus_powered": power.get("voltage", 0) == 5.0  # USB bus power
        }