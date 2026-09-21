"""FHIR R4 client with HIPAA compliance and PHI protection"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
import json
import uuid
from pathlib import Path
import aiohttp
from fhirpy import AsyncFHIRClient
from fhirpy.base.exceptions import ResourceNotFound, OperationOutcome

from ..core.config import get_healthcare_settings
from ..compliance.hipaa_manager import HIPAAManager
from ..compliance.encryption_manager import EncryptionManager


class FHIRClient:
    """Secure FHIR R4 client with comprehensive PHI protection"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.settings = get_healthcare_settings()
        self.hipaa_manager = HIPAAManager()
        self.encryption_manager = EncryptionManager()
        
        # FHIR server configuration
        self.base_url = base_url or self.settings.FHIR_SERVER_URL
        self.client: Optional[AsyncFHIRClient] = None
        
        # FHIR resource PHI risk levels
        self.resource_phi_levels = {
            "Patient": "maximum",
            "Person": "maximum", 
            "RelatedPerson": "high",
            "Practitioner": "medium",
            "PractitionerRole": "medium",
            "Organization": "low",
            "Location": "low",
            "Encounter": "high",
            "EpisodeOfCare": "high",
            "Observation": "high",
            "DiagnosticReport": "high",
            "Condition": "high",
            "Procedure": "high",
            "MedicationStatement": "high",
            "MedicationRequest": "high",
            "Immunization": "medium",
            "AllergyIntolerance": "high",
            "DocumentReference": "high",
            "Media": "high",
            "Coverage": "high",
            "Claim": "high"
        }
        
    async def initialize(self, auth_token: Optional[str] = None):
        """Initialize FHIR client with authentication"""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
                
            self.client = AsyncFHIRClient(
                self.base_url,
                extra_headers=headers
            )
            
            # Test connectivity
            await self.client.resources("CapabilityStatement").search().fetch()
            
        except Exception as e:
            raise ConnectionError(f"Failed to initialize FHIR client: {str(e)}")
            
    async def get_patient(
        self, 
        patient_id: str, 
        user_id: str,
        include_phi: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve patient resource with PHI protection
        
        Args:
            patient_id: FHIR Patient resource ID
            user_id: User requesting the patient data
            include_phi: Whether to include PHI fields
            
        Returns:
            Patient resource or None if access denied
        """
        try:
            # Validate access permissions
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="patient",
                resource_id=patient_id,
                action="read",
                purpose="treatment"
            )
            
            if not access_valid:
                return None
                
            # Fetch patient resource
            patient = await self.client.resources("Patient").search(
                _id=patient_id
            ).first()
            
            if not patient:
                return None
                
            patient_dict = patient.serialize()
            
            # Apply PHI filtering based on access level
            if not include_phi:
                patient_dict = await self._filter_patient_phi(patient_dict)
                
            # Apply data minimization
            minimized_patient = await self.hipaa_manager.minimize_data(
                patient_dict, "treatment", user_id
            )
            
            # Log access
            await self._log_fhir_access(
                user_id, "read", "Patient", patient_id, "treatment"
            )
            
            return minimized_patient
            
        except ResourceNotFound:
            return None
        except Exception as e:
            await self._log_fhir_error(user_id, "read", "Patient", patient_id, str(e))
            return None
            
    async def search_patients(
        self,
        search_params: Dict[str, Any],
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search patients with privacy protection
        
        Args:
            search_params: FHIR search parameters
            user_id: User performing the search
            limit: Maximum number of results
            
        Returns:
            List of patient resources
        """
        try:
            # Validate search permissions
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="patient",
                resource_id="search",
                action="search",
                purpose="treatment"
            )
            
            if not access_valid:
                return []
                
            # Perform search with limit
            search_params["_count"] = min(limit, 100)  # Server-side limit
            
            patients = await self.client.resources("Patient").search(
                **search_params
            ).fetch()
            
            # Process and minimize each patient
            processed_patients = []
            for patient in patients:
                patient_dict = patient.serialize()
                
                # Apply data minimization
                minimized = await self.hipaa_manager.minimize_data(
                    patient_dict, "treatment", user_id
                )
                processed_patients.append(minimized)
                
            # Log search activity
            await self._log_fhir_access(
                user_id, "search", "Patient", f"params:{search_params}", "treatment"
            )
            
            return processed_patients
            
        except Exception as e:
            await self._log_fhir_error(
                user_id, "search", "Patient", str(search_params), str(e)
            )
            return []
            
    async def create_patient(
        self,
        patient_data: Dict[str, Any],
        user_id: str
    ) -> Optional[str]:
        """
        Create new patient resource with PHI encryption
        
        Args:
            patient_data: Patient resource data
            user_id: User creating the patient
            
        Returns:
            Created patient ID or None if failed
        """
        try:
            # Validate creation permissions
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="patient", 
                resource_id="new",
                action="create",
                purpose="treatment"
            )
            
            if not access_valid:
                return None
                
            # Validate patient data structure
            validation_result = await self._validate_patient_resource(patient_data)
            if not validation_result["valid"]:
                return None
                
            # Encrypt sensitive PHI fields
            encrypted_data = await self._encrypt_patient_phi(patient_data)
            
            # Create patient resource
            patient_resource = self.client.resource("Patient", **encrypted_data)
            patient = await patient_resource.save()
            
            patient_id = patient["id"]
            
            # Store encryption keys securely
            await self._store_patient_encryption_keys(patient_id, encrypted_data)
            
            # Log creation
            await self._log_fhir_access(
                user_id, "create", "Patient", patient_id, "treatment"
            )
            
            return patient_id
            
        except Exception as e:
            await self._log_fhir_error(
                user_id, "create", "Patient", "new", str(e)
            )
            return None
            
    async def get_patient_observations(
        self,
        patient_id: str,
        user_id: str,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get patient observations with date filtering
        
        Args:
            patient_id: Patient identifier
            user_id: User requesting observations
            category: Observation category filter
            start_date: Start date for filtering
            end_date: End date for filtering
            limit: Maximum number of observations
            
        Returns:
            List of observation resources
        """
        try:
            # Validate access
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="observation",
                resource_id=f"patient:{patient_id}",
                action="read",
                purpose="treatment"
            )
            
            if not access_valid:
                return []
                
            # Build search parameters
            search_params = {
                "patient": patient_id,
                "_count": min(limit, 200)
            }
            
            if category:
                search_params["category"] = category
                
            if start_date:
                date_filter = start_date.strftime("%Y-%m-%d")
                if end_date:
                    date_filter += f",{end_date.strftime('%Y-%m-%d')}"
                search_params["date"] = date_filter
                
            # Search observations
            observations = await self.client.resources("Observation").search(
                **search_params
            ).fetch()
            
            # Process observations
            processed_observations = []
            for obs in observations:
                obs_dict = obs.serialize()
                
                # Apply data minimization
                minimized = await self.hipaa_manager.minimize_data(
                    obs_dict, "treatment", user_id
                )
                processed_observations.append(minimized)
                
            # Log access
            await self._log_fhir_access(
                user_id, "read", "Observation", f"patient:{patient_id}", "treatment"
            )
            
            return processed_observations
            
        except Exception as e:
            await self._log_fhir_error(
                user_id, "read", "Observation", f"patient:{patient_id}", str(e)
            )
            return []
            
    async def create_observation(
        self,
        observation_data: Dict[str, Any],
        user_id: str
    ) -> Optional[str]:
        """
        Create observation resource with PHI protection
        
        Args:
            observation_data: Observation resource data
            user_id: User creating the observation
            
        Returns:
            Created observation ID or None if failed
        """
        try:
            # Validate creation permissions
            patient_id = observation_data.get("subject", {}).get("reference", "").split("/")[-1]
            
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="observation",
                resource_id=f"patient:{patient_id}",
                action="create",
                purpose="treatment"
            )
            
            if not access_valid:
                return None
                
            # Validate observation data
            validation_result = await self._validate_observation_resource(observation_data)
            if not validation_result["valid"]:
                return None
                
            # Encrypt sensitive fields
            encrypted_data = await self._encrypt_observation_phi(observation_data)
            
            # Create observation
            obs_resource = self.client.resource("Observation", **encrypted_data)
            observation = await obs_resource.save()
            
            obs_id = observation["id"]
            
            # Log creation
            await self._log_fhir_access(
                user_id, "create", "Observation", obs_id, "treatment"
            )
            
            return obs_id
            
        except Exception as e:
            await self._log_fhir_error(
                user_id, "create", "Observation", "new", str(e)
            )
            return None
            
    async def get_patient_encounters(
        self,
        patient_id: str,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get patient encounters with filtering"""
        try:
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="encounter",
                resource_id=f"patient:{patient_id}",
                action="read",
                purpose="treatment"
            )
            
            if not access_valid:
                return []
                
            search_params = {
                "patient": patient_id,
                "_count": min(limit, 100)
            }
            
            if status:
                search_params["status"] = status
                
            encounters = await self.client.resources("Encounter").search(
                **search_params
            ).fetch()
            
            processed_encounters = []
            for encounter in encounters:
                enc_dict = encounter.serialize()
                minimized = await self.hipaa_manager.minimize_data(
                    enc_dict, "treatment", user_id
                )
                processed_encounters.append(minimized)
                
            await self._log_fhir_access(
                user_id, "read", "Encounter", f"patient:{patient_id}", "treatment"
            )
            
            return processed_encounters
            
        except Exception as e:
            await self._log_fhir_error(
                user_id, "read", "Encounter", f"patient:{patient_id}", str(e)
            )
            return []
            
    async def bulk_export(
        self,
        resource_type: str,
        user_id: str,
        since: Optional[datetime] = None,
        patient_filter: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Initiate FHIR bulk data export with PHI protection
        
        Args:
            resource_type: FHIR resource type to export
            user_id: User requesting export
            since: Export data since this date
            patient_filter: List of patient IDs to filter by
            
        Returns:
            Export job ID or None if failed
        """
        try:
            # Validate bulk export permissions
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type=resource_type.lower(),
                resource_id="bulk_export",
                action="export",
                purpose="operations"
            )
            
            if not access_valid:
                return None
                
            # Build export parameters
            export_params = {
                "_type": resource_type
            }
            
            if since:
                export_params["_since"] = since.isoformat()
                
            if patient_filter:
                export_params["patient"] = ",".join(patient_filter)
                
            # Initiate export (placeholder - actual implementation would depend on server)
            export_id = str(uuid.uuid4())
            
            # Log export initiation
            await self._log_fhir_access(
                user_id, "export", resource_type, "bulk", "operations"
            )
            
            return export_id
            
        except Exception as e:
            await self._log_fhir_error(
                user_id, "export", resource_type, "bulk", str(e)
            )
            return None
            
    async def _filter_patient_phi(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove PHI from patient data for non-authorized access"""
        
        # Remove direct identifiers
        filtered_data = patient_data.copy()
        
        phi_fields = [
            "name", "telecom", "address", "photo", 
            "contact", "identifier"
        ]
        
        for field in phi_fields:
            if field in filtered_data:
                del filtered_data[field]
                
        # Keep only essential clinical data
        safe_fields = [
            "id", "gender", "birthDate", "deceasedBoolean",
            "maritalStatus", "extension", "meta"
        ]
        
        return {k: v for k, v in filtered_data.items() if k in safe_fields}
        
    async def _encrypt_patient_phi(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt PHI fields in patient data"""
        
        encrypted_data = patient_data.copy()
        
        # Encrypt sensitive string fields
        sensitive_fields = ["name", "address", "telecom"]
        
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                field_str = json.dumps(encrypted_data[field])
                encrypted_value = await self.encryption_manager.encrypt_field(
                    field_str, "maximum_security", field
                )
                encrypted_data[f"{field}_encrypted"] = encrypted_value
                del encrypted_data[field]
                
        return encrypted_data
        
    async def _encrypt_observation_phi(self, obs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt PHI fields in observation data"""
        
        encrypted_data = obs_data.copy()
        
        # Encrypt note and comment fields
        if "note" in encrypted_data:
            note_str = json.dumps(encrypted_data["note"])
            encrypted_note = await self.encryption_manager.encrypt_field(
                note_str, "high_security", "note"
            )
            encrypted_data["note_encrypted"] = encrypted_note
            del encrypted_data["note"]
            
        return encrypted_data
        
    async def _validate_patient_resource(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate patient resource structure"""
        
        errors = []
        
        # Check required fields
        if not patient_data.get("resourceType") == "Patient":
            errors.append("Invalid resourceType, must be 'Patient'")
            
        # Validate identifier structure
        identifiers = patient_data.get("identifier", [])
        if not identifiers:
            errors.append("Patient must have at least one identifier")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
        
    async def _validate_observation_resource(self, obs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate observation resource structure"""
        
        errors = []
        
        if not obs_data.get("resourceType") == "Observation":
            errors.append("Invalid resourceType, must be 'Observation'")
            
        if not obs_data.get("status"):
            errors.append("Observation must have status")
            
        if not obs_data.get("code"):
            errors.append("Observation must have code")
            
        if not obs_data.get("subject"):
            errors.append("Observation must have subject reference")
            
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
        
    async def _store_patient_encryption_keys(
        self, 
        patient_id: str, 
        encrypted_data: Dict[str, Any]
    ):
        """Store encryption keys for patient data"""
        # Placeholder - would store keys in secure key management system
        pass
        
    async def _log_fhir_access(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        purpose: str
    ):
        """Log FHIR resource access"""
        await self.hipaa_manager.log_phi_access(
            user_id=user_id,
            action=f"fhir_{action}",
            resource_type=f"fhir_{resource_type.lower()}",
            resource_id=resource_id,
            purpose=purpose
        )
        
    async def _log_fhir_error(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        error: str
    ):
        """Log FHIR access errors"""
        await self.hipaa_manager.log_phi_access(
            user_id=user_id,
            action=f"fhir_{action}_error",
            resource_type=f"fhir_{resource_type.lower()}",
            resource_id=resource_id,
            purpose="error_logging",
            additional_data={"error": error}
        )