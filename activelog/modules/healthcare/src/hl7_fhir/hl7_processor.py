"""HL7 message processing with HIPAA compliance"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import hl7
from hl7.containers import Message, Segment
import json
import uuid

from ..core.config import get_healthcare_settings
from ..compliance.hipaa_manager import HIPAAManager
from ..compliance.encryption_manager import EncryptionManager


class HL7Processor:
    """Secure HL7 message processing with PHI protection"""
    
    def __init__(self):
        self.settings = get_healthcare_settings()
        self.hipaa_manager = HIPAAManager()
        self.encryption_manager = EncryptionManager()
        
        # HL7 message types and their PHI risk levels
        self.message_types = {
            "ADT": "high",      # Admission/Discharge/Transfer
            "ORM": "high",      # Order Message
            "ORU": "high",      # Observation Result
            "SIU": "medium",    # Scheduling Information
            "MDM": "high",      # Medical Document Management
            "BAR": "high",      # Billing Account Record
            "DFT": "high",      # Detailed Financial Transaction
            "ACK": "low"        # General Acknowledgment
        }
        
    async def process_hl7_message(
        self, 
        message_text: str, 
        source_system: str,
        user_id: str,
        validate_only: bool = False
    ) -> Dict[str, Any]:
        """
        Process incoming HL7 message with security validation
        
        Args:
            message_text: Raw HL7 message text
            source_system: Identifier of sending system
            user_id: User processing the message
            validate_only: If True, only validate without storing
            
        Returns:
            Processing result with status and extracted data
        """
        try:
            # Parse HL7 message
            message = hl7.parse(message_text)
            
            # Extract message metadata
            message_info = await self._extract_message_info(message)
            message_type = message_info.get("message_type", "UNKNOWN")
            
            # Validate access permissions
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="hl7_message",
                resource_id=f"{source_system}:{message_type}",
                action="process",
                purpose="treatment"
            )
            
            if not access_valid:
                return {
                    "success": False,
                    "error": "Access denied for HL7 message processing",
                    "message_id": message_info.get("message_control_id")
                }
                
            # Validate message structure
            validation_result = await self._validate_message_structure(message)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Message validation failed: {validation_result['errors']}",
                    "message_id": message_info.get("message_control_id")
                }
                
            # Extract and classify PHI
            phi_classification = await self._classify_message_phi(message)
            
            if validate_only:
                return {
                    "success": True,
                    "message_info": message_info,
                    "phi_classification": phi_classification,
                    "validation": validation_result
                }
                
            # Encrypt and store message
            storage_result = await self._store_encrypted_message(
                message, message_info, phi_classification, source_system
            )
            
            # Extract structured data
            structured_data = await self._extract_structured_data(message, message_type)
            
            # Log processing
            await self._log_message_processing(
                message_info, source_system, user_id, "processed"
            )
            
            return {
                "success": True,
                "message_id": message_info.get("message_control_id"),
                "storage_id": storage_result["storage_id"],
                "message_info": message_info,
                "structured_data": structured_data,
                "phi_risk_level": self.message_types.get(message_type, "unknown")
            }
            
        except Exception as e:
            await self._log_message_processing(
                {"error": str(e)}, source_system, user_id, "error"
            )
            return {
                "success": False,
                "error": f"HL7 processing error: {str(e)}"
            }
            
    async def create_hl7_message(
        self,
        message_type: str,
        data: Dict[str, Any],
        sending_application: str,
        receiving_application: str,
        user_id: str
    ) -> Optional[str]:
        """
        Create HL7 message from structured data
        
        Args:
            message_type: HL7 message type (ADT, ORM, etc.)
            data: Structured data to include
            sending_application: Sending system identifier
            receiving_application: Receiving system identifier
            user_id: User creating the message
            
        Returns:
            HL7 message string or None if creation fails
        """
        try:
            # Validate creation permissions
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="hl7_message",
                resource_id=f"create:{message_type}",
                action="create",
                purpose="treatment"
            )
            
            if not access_valid:
                return None
                
            # Create message based on type
            if message_type == "ADT":
                message = await self._create_adt_message(
                    data, sending_application, receiving_application
                )
            elif message_type == "ORM":
                message = await self._create_orm_message(
                    data, sending_application, receiving_application
                )
            elif message_type == "ORU":
                message = await self._create_oru_message(
                    data, sending_application, receiving_application
                )
            else:
                return None
                
            # Convert to string
            message_text = str(message)
            
            # Log message creation
            await self._log_message_processing(
                {"message_type": message_type, "created": True},
                sending_application, user_id, "created"
            )
            
            return message_text
            
        except Exception as e:
            await self._log_message_processing(
                {"error": str(e)}, sending_application, user_id, "creation_error"
            )
            return None
            
    async def get_message_history(
        self,
        patient_id: Optional[str] = None,
        message_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: str = "",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve HL7 message history with filtering
        
        Args:
            patient_id: Filter by patient identifier
            message_type: Filter by HL7 message type
            start_date: Start date for filtering
            end_date: End date for filtering
            user_id: User requesting the history
            limit: Maximum number of messages to return
            
        Returns:
            List of message summaries
        """
        try:
            # Validate access
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="hl7_history",
                resource_id=patient_id or "all",
                action="view",
                purpose="treatment"
            )
            
            if not access_valid:
                return []
                
            # Query message history (placeholder - would use actual database)
            messages = await self._query_message_history(
                patient_id, message_type, start_date, end_date, limit
            )
            
            # Apply data minimization
            minimized_messages = []
            for message in messages:
                minimized = await self.hipaa_manager.minimize_data(
                    message, "treatment", user_id
                )
                minimized_messages.append(minimized)
                
            return minimized_messages
            
        except Exception as e:
            return []
            
    async def _extract_message_info(self, message: Message) -> Dict[str, Any]:
        """Extract basic message information"""
        msh = message.segment("MSH")
        
        return {
            "message_type": str(msh[9][0]) if len(msh) > 9 else "UNKNOWN",
            "trigger_event": str(msh[9][1]) if len(msh) > 9 and len(msh[9]) > 1 else "",
            "message_control_id": str(msh[10]) if len(msh) > 10 else str(uuid.uuid4()),
            "sending_application": str(msh[3]) if len(msh) > 3 else "",
            "receiving_application": str(msh[5]) if len(msh) > 5 else "",
            "timestamp": str(msh[7]) if len(msh) > 7 else "",
            "version": str(msh[12]) if len(msh) > 12 else "2.5"
        }
        
    async def _validate_message_structure(self, message: Message) -> Dict[str, Any]:
        """Validate HL7 message structure"""
        errors = []
        
        try:
            # Check for required MSH segment
            msh = message.segment("MSH")
            if not msh:
                errors.append("Missing required MSH segment")
                
            # Validate required MSH fields
            required_msh_fields = [3, 5, 7, 9, 10, 12]  # Sending app, receiving app, timestamp, etc.
            for field_num in required_msh_fields:
                if len(msh) <= field_num or not str(msh[field_num]).strip():
                    errors.append(f"Missing required MSH field {field_num}")
                    
            # Message type specific validation
            message_type = str(msh[9][0]) if len(msh) > 9 else ""
            if message_type == "ADT":
                errors.extend(await self._validate_adt_message(message))
            elif message_type == "ORM":
                errors.extend(await self._validate_orm_message(message))
            elif message_type == "ORU":
                errors.extend(await self._validate_oru_message(message))
                
        except Exception as e:
            errors.append(f"Structure validation error: {str(e)}")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
        
    async def _classify_message_phi(self, message: Message) -> Dict[str, Any]:
        """Classify PHI content in HL7 message"""
        phi_fields = {
            "direct_identifiers": [],
            "quasi_identifiers": [],
            "sensitive_phi": [],
            "general_phi": []
        }
        
        # Check PID segment for patient identifiers
        pid = message.segment("PID")
        if pid:
            phi_fields["direct_identifiers"].extend([
                "patient_id", "patient_name", "patient_address",
                "patient_phone", "ssn"
            ])
            phi_fields["quasi_identifiers"].extend([
                "birth_date", "gender", "race", "ethnicity"
            ])
            
        # Check other segments for PHI
        for segment in message:
            segment_name = str(segment[0])
            if segment_name in ["PV1", "PV2"]:  # Patient visit
                phi_fields["general_phi"].extend([
                    "admission_date", "discharge_date", "attending_physician"
                ])
            elif segment_name in ["OBX", "NTE"]:  # Observations/Notes
                phi_fields["sensitive_phi"].extend([
                    "test_results", "clinical_notes", "diagnosis"
                ])
                
        return phi_fields
        
    async def _store_encrypted_message(
        self,
        message: Message,
        message_info: Dict[str, Any],
        phi_classification: Dict[str, Any],
        source_system: str
    ) -> Dict[str, Any]:
        """Store HL7 message with encryption"""
        
        # Generate storage ID
        storage_id = str(uuid.uuid4())
        
        # Encrypt message text
        message_text = str(message)
        encrypted_message = await self.encryption_manager.encrypt_data(
            message_text.encode(), "maximum_security"
        )
        
        # Store metadata
        metadata = {
            "storage_id": storage_id,
            "message_info": message_info,
            "phi_classification": phi_classification,
            "source_system": source_system,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "encrypted": True
        }
        
        # Store encrypted message and metadata (placeholder - would use actual storage)
        await self._store_message_data(storage_id, encrypted_message, metadata)
        
        return {"storage_id": storage_id}
        
    async def _extract_structured_data(
        self, 
        message: Message, 
        message_type: str
    ) -> Dict[str, Any]:
        """Extract structured data from HL7 message"""
        
        structured = {"message_type": message_type}
        
        # Extract patient data from PID segment
        pid = message.segment("PID")
        if pid:
            structured["patient"] = {
                "id": str(pid[3]) if len(pid) > 3 else "",
                "name": str(pid[5]) if len(pid) > 5 else "",
                "birth_date": str(pid[7]) if len(pid) > 7 else "",
                "gender": str(pid[8]) if len(pid) > 8 else ""
            }
            
        # Extract visit data from PV1 segment
        pv1 = message.segment("PV1")
        if pv1:
            structured["visit"] = {
                "class": str(pv1[2]) if len(pv1) > 2 else "",
                "location": str(pv1[3]) if len(pv1) > 3 else "",
                "attending_doctor": str(pv1[7]) if len(pv1) > 7 else "",
                "admission_date": str(pv1[44]) if len(pv1) > 44 else ""
            }
            
        # Message type specific extraction
        if message_type == "ORU":  # Lab results
            structured["observations"] = await self._extract_observations(message)
        elif message_type == "ORM":  # Orders
            structured["orders"] = await self._extract_orders(message)
            
        return structured
        
    async def _extract_observations(self, message: Message) -> List[Dict[str, Any]]:
        """Extract observations from ORU message"""
        observations = []
        
        for segment in message:
            if str(segment[0]) == "OBX":
                obs = {
                    "value_type": str(segment[2]) if len(segment) > 2 else "",
                    "identifier": str(segment[3]) if len(segment) > 3 else "",
                    "value": str(segment[5]) if len(segment) > 5 else "",
                    "units": str(segment[6]) if len(segment) > 6 else "",
                    "reference_range": str(segment[7]) if len(segment) > 7 else "",
                    "status": str(segment[11]) if len(segment) > 11 else ""
                }
                observations.append(obs)
                
        return observations
        
    async def _extract_orders(self, message: Message) -> List[Dict[str, Any]]:
        """Extract orders from ORM message"""
        orders = []
        
        for segment in message:
            if str(segment[0]) == "ORC":
                order = {
                    "control": str(segment[1]) if len(segment) > 1 else "",
                    "order_number": str(segment[3]) if len(segment) > 3 else "",
                    "status": str(segment[5]) if len(segment) > 5 else "",
                    "entered_by": str(segment[10]) if len(segment) > 10 else ""
                }
                orders.append(order)
                
        return orders
        
    async def _create_adt_message(
        self,
        data: Dict[str, Any],
        sending_app: str,
        receiving_app: str
    ) -> Message:
        """Create ADT (Admission/Discharge/Transfer) message"""
        
        # Create MSH segment
        msh = f"MSH|^~\\&|{sending_app}|{data.get('sending_facility', '')}|{receiving_app}|{data.get('receiving_facility', '')}|{datetime.now().strftime('%Y%m%d%H%M%S')}||ADT^A01^ADT_A01|{uuid.uuid4()}|P|2.5"
        
        # Create PID segment
        patient = data.get("patient", {})
        pid = f"PID|1||{patient.get('id', '')}^^^MRN||{patient.get('name', '')}||{patient.get('birth_date', '')}|{patient.get('gender', '')}"
        
        # Create PV1 segment
        visit = data.get("visit", {})
        pv1 = f"PV1|1|{visit.get('class', 'I')}|{visit.get('location', '')}||||||{visit.get('attending_doctor', '')}"
        
        message_text = f"{msh}\r{pid}\r{pv1}\r"
        return hl7.parse(message_text)
        
    async def _create_orm_message(
        self,
        data: Dict[str, Any],
        sending_app: str,
        receiving_app: str
    ) -> Message:
        """Create ORM (Order) message"""
        
        msh = f"MSH|^~\\&|{sending_app}|{data.get('sending_facility', '')}|{receiving_app}|{data.get('receiving_facility', '')}|{datetime.now().strftime('%Y%m%d%H%M%S')}||ORM^O01^ORM_O01|{uuid.uuid4()}|P|2.5"
        
        patient = data.get("patient", {})
        pid = f"PID|1||{patient.get('id', '')}^^^MRN||{patient.get('name', '')}||{patient.get('birth_date', '')}|{patient.get('gender', '')}"
        
        order = data.get("order", {})
        orc = f"ORC|{order.get('control', 'NW')}|{order.get('order_number', '')}|||||||||{order.get('entered_by', '')}"
        
        message_text = f"{msh}\r{pid}\r{orc}\r"
        return hl7.parse(message_text)
        
    async def _create_oru_message(
        self,
        data: Dict[str, Any],
        sending_app: str,
        receiving_app: str
    ) -> Message:
        """Create ORU (Observation Result) message"""
        
        msh = f"MSH|^~\\&|{sending_app}|{data.get('sending_facility', '')}|{receiving_app}|{data.get('receiving_facility', '')}|{datetime.now().strftime('%Y%m%d%H%M%S')}||ORU^R01^ORU_R01|{uuid.uuid4()}|P|2.5"
        
        patient = data.get("patient", {})
        pid = f"PID|1||{patient.get('id', '')}^^^MRN||{patient.get('name', '')}||{patient.get('birth_date', '')}|{patient.get('gender', '')}"
        
        message_text = f"{msh}\r{pid}\r"
        
        # Add observations
        for i, obs in enumerate(data.get("observations", [])):
            obx = f"OBX|{i+1}|{obs.get('type', 'ST')}|{obs.get('identifier', '')}||{obs.get('value', '')}|{obs.get('units', '')}|{obs.get('reference_range', '')}|||{obs.get('status', 'F')}"
            message_text += f"{obx}\r"
            
        return hl7.parse(message_text)
        
    async def _validate_adt_message(self, message: Message) -> List[str]:
        """Validate ADT message specific requirements"""
        errors = []
        
        pid = message.segment("PID")
        if not pid:
            errors.append("ADT message missing required PID segment")
            
        pv1 = message.segment("PV1")  
        if not pv1:
            errors.append("ADT message missing required PV1 segment")
            
        return errors
        
    async def _validate_orm_message(self, message: Message) -> List[str]:
        """Validate ORM message specific requirements"""
        errors = []
        
        orc = message.segment("ORC")
        if not orc:
            errors.append("ORM message missing required ORC segment")
            
        return errors
        
    async def _validate_oru_message(self, message: Message) -> List[str]:
        """Validate ORU message specific requirements"""
        errors = []
        
        obx_found = False
        for segment in message:
            if str(segment[0]) == "OBX":
                obx_found = True
                break
                
        if not obx_found:
            errors.append("ORU message missing required OBX segment")
            
        return errors
        
    async def _query_message_history(
        self,
        patient_id: Optional[str],
        message_type: Optional[str],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Query message history from storage"""
        # Placeholder implementation - would query actual database
        return []
        
    async def _store_message_data(
        self,
        storage_id: str,
        encrypted_message: bytes,
        metadata: Dict[str, Any]
    ):
        """Store encrypted message and metadata"""
        # Placeholder implementation - would store in actual database
        pass
        
    async def _log_message_processing(
        self,
        message_info: Dict[str, Any],
        source_system: str,
        user_id: str,
        action: str
    ):
        """Log HL7 message processing activity"""
        await self.hipaa_manager.log_phi_access(
            user_id=user_id,
            action=f"hl7_{action}",
            resource_type="hl7_message",
            resource_id=message_info.get("message_control_id", "unknown"),
            purpose="treatment",
            additional_data={
                "source_system": source_system,
                "message_type": message_info.get("message_type", "unknown")
            }
        )