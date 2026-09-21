"""
Enterprise Governance and Policy Management
Advanced governance, risk management, and compliance automation
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from enum import Enum
from pathlib import Path
import hashlib
import re

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

try:
    from jinja2 import Template, Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

logger = logging.getLogger(__name__)

class PolicyType(Enum):
    SECURITY = "security"
    COMPLIANCE = "compliance"
    RESOURCE = "resource"
    ACCESS_CONTROL = "access_control"
    DATA_GOVERNANCE = "data_governance"
    NETWORK = "network"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"

class PolicyEnforcement(Enum):
    ENFORCE = "enforce"  # Block non-compliant actions
    WARN = "warn"       # Log warnings but allow
    AUDIT = "audit"     # Only log for audit purposes
    DRY_RUN = "dry_run" # Evaluate but don't enforce

class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"

class GovernanceScope(Enum):
    GLOBAL = "global"
    ORGANIZATION = "organization"
    PROJECT = "project"
    SERVICE = "service"
    USER = "user"

@dataclass
class PolicyRule:
    rule_id: str
    name: str
    description: str
    policy_type: PolicyType
    scope: GovernanceScope
    enforcement: PolicyEnforcement
    condition: str  # JSONPath or custom expression
    action: str     # Action to take when rule matches
    parameters: Dict[str, Any]
    severity: RiskLevel
    tags: List[str]
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PolicyViolation:
    violation_id: str
    rule_id: str
    resource_id: str
    resource_type: str
    violation_time: datetime
    description: str
    severity: RiskLevel
    enforcement_action: str
    remediation_suggestions: List[str]
    context: Dict[str, Any]
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None

@dataclass
class RiskAssessmentResult:
    assessment_id: str
    target_resource: str
    assessment_time: datetime
    overall_risk_score: float
    risk_level: RiskLevel
    identified_risks: List[Dict[str, Any]]
    mitigation_recommendations: List[str]
    compliance_status: Dict[str, str]
    next_assessment_due: datetime
    assessment_metadata: Dict[str, Any]

@dataclass
class GovernancePolicy:
    policy_id: str
    name: str
    version: str
    description: str
    policy_type: PolicyType
    scope: GovernanceScope
    rules: List[PolicyRule]
    approval_workflow: Dict[str, Any]
    review_schedule: Dict[str, Any]
    effective_date: datetime
    expiration_date: Optional[datetime]
    owner: str
    approvers: List[str]
    tags: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

class PolicyManager:
    """Advanced policy management and enforcement system"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.policies: Dict[str, GovernancePolicy] = {}
        self.violations: Dict[str, PolicyViolation] = {}
        self.policy_cache: Dict[str, Any] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Policy evaluation engine
        self.evaluation_engine = PolicyEvaluationEngine()
        
        # Load existing policies
        asyncio.create_task(self._load_policies())
    
    async def create_policy(self, policy: GovernancePolicy) -> bool:
        """Create new governance policy"""
        try:
            # Validate policy
            if not self._validate_policy(policy):
                return False
            
            # Check for conflicts
            conflicts = await self._check_policy_conflicts(policy)
            if conflicts:
                self.logger.warning(f"Policy conflicts detected: {conflicts}")
            
            # Store policy
            self.policies[policy.policy_id] = policy
            
            # Save to persistent storage
            await self._save_policy(policy)
            
            # Clear cache
            self._clear_policy_cache()
            
            self.logger.info(f"Policy created: {policy.name} ({policy.policy_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Policy creation failed: {e}")
            return False
    
    async def evaluate_policies(self, 
                               resource: Dict[str, Any], 
                               context: Optional[Dict[str, Any]] = None) -> List[PolicyViolation]:
        """Evaluate all applicable policies against a resource"""
        try:
            violations = []
            evaluation_context = context or {}
            
            # Find applicable policies
            applicable_policies = self._find_applicable_policies(resource)
            
            for policy in applicable_policies:
                # Evaluate each rule in the policy
                for rule in policy.rules:
                    if not rule.enabled:
                        continue
                    
                    # Evaluate rule condition
                    violation = await self._evaluate_rule(rule, resource, evaluation_context)
                    
                    if violation:
                        violations.append(violation)
                        
                        # Store violation
                        self.violations[violation.violation_id] = violation
                        
                        # Log violation
                        self.logger.warning(f"Policy violation: {rule.name} - {violation.description}")
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Policy evaluation failed: {e}")
            return []
    
    async def _evaluate_rule(self, 
                            rule: PolicyRule, 
                            resource: Dict[str, Any], 
                            context: Dict[str, Any]) -> Optional[PolicyViolation]:
        """Evaluate a specific policy rule"""
        try:
            # Evaluate condition using the evaluation engine
            condition_result = await self.evaluation_engine.evaluate_condition(
                rule.condition, 
                resource, 
                context
            )
            
            if condition_result:
                # Create violation
                violation = PolicyViolation(
                    violation_id=str(uuid.uuid4()),
                    rule_id=rule.rule_id,
                    resource_id=resource.get('id', 'unknown'),
                    resource_type=resource.get('type', 'unknown'),
                    violation_time=datetime.utcnow(),
                    description=f"Rule '{rule.name}' violated: {rule.description}",
                    severity=rule.severity,
                    enforcement_action=rule.enforcement.value,
                    remediation_suggestions=self._generate_remediation_suggestions(rule, resource),
                    context=context
                )
                
                # Apply enforcement action
                await self._apply_enforcement_action(rule, violation, resource)
                
                return violation
            
            return None
            
        except Exception as e:
            self.logger.error(f"Rule evaluation failed: {e}")
            return None
    
    def _find_applicable_policies(self, resource: Dict[str, Any]) -> List[GovernancePolicy]:
        """Find policies applicable to a resource"""
        applicable = []
        
        for policy in self.policies.values():
            # Check scope
            if self._is_policy_applicable(policy, resource):
                # Check if policy is effective
                now = datetime.utcnow()
                if (policy.effective_date <= now and 
                    (not policy.expiration_date or policy.expiration_date > now)):
                    applicable.append(policy)
        
        return applicable
    
    def _is_policy_applicable(self, policy: GovernancePolicy, resource: Dict[str, Any]) -> bool:
        """Check if policy is applicable to resource"""
        # Simple scope matching logic
        resource_scope = resource.get('scope', 'global')
        
        if policy.scope == GovernanceScope.GLOBAL:
            return True
        elif policy.scope.value == resource_scope:
            return True
        elif policy.scope == GovernanceScope.ORGANIZATION and resource_scope in ['project', 'service']:
            return True
        elif policy.scope == GovernanceScope.PROJECT and resource_scope == 'service':
            return True
        
        return False
    
    async def _apply_enforcement_action(self, 
                                       rule: PolicyRule, 
                                       violation: PolicyViolation, 
                                       resource: Dict[str, Any]):
        """Apply enforcement action for policy violation"""
        try:
            if rule.enforcement == PolicyEnforcement.ENFORCE:
                # Block the action
                raise PolicyViolationError(f"Policy violation: {violation.description}")
            
            elif rule.enforcement == PolicyEnforcement.WARN:
                # Log warning
                self.logger.warning(f"Policy warning: {violation.description}")
            
            elif rule.enforcement in [PolicyEnforcement.AUDIT, PolicyEnforcement.DRY_RUN]:
                # Only log for audit
                self.logger.info(f"Policy audit: {violation.description}")
            
            # Execute custom action if specified
            if rule.action and rule.action != 'log':
                await self._execute_custom_action(rule.action, violation, resource)
                
        except Exception as e:
            self.logger.error(f"Enforcement action failed: {e}")
    
    def _generate_remediation_suggestions(self, 
                                         rule: PolicyRule, 
                                         resource: Dict[str, Any]) -> List[str]:
        """Generate remediation suggestions for policy violations"""
        suggestions = []
        
        # Rule-specific suggestions
        if rule.policy_type == PolicyType.SECURITY:
            suggestions.append("Review security configuration and apply security best practices")
            suggestions.append("Ensure proper encryption and access controls are in place")
        
        elif rule.policy_type == PolicyType.COMPLIANCE:
            suggestions.append("Review compliance requirements and update configuration")
            suggestions.append("Consult with compliance team for guidance")
        
        elif rule.policy_type == PolicyType.RESOURCE:
            suggestions.append("Optimize resource allocation and usage")
            suggestions.append("Consider scaling or resource limits")
        
        # Add rule-specific suggestions from parameters
        if 'remediation_suggestions' in rule.parameters:
            suggestions.extend(rule.parameters['remediation_suggestions'])
        
        return suggestions

class PolicyEvaluationEngine:
    """Policy condition evaluation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Custom functions for policy evaluation
        self.functions = {
            'contains': self._func_contains,
            'matches': self._func_matches,
            'greater_than': self._func_greater_than,
            'less_than': self._func_less_than,
            'in_range': self._func_in_range,
            'has_tag': self._func_has_tag,
            'is_encrypted': self._func_is_encrypted,
            'is_public': self._func_is_public
        }
    
    async def evaluate_condition(self, 
                                condition: str, 
                                resource: Dict[str, Any], 
                                context: Dict[str, Any]) -> bool:
        """Evaluate policy condition expression"""
        try:
            # Simple expression evaluation
            # In production, this would use a more sophisticated policy language
            
            # Parse condition
            if '(' in condition and ')' in condition:
                # Function call
                return await self._evaluate_function_call(condition, resource, context)
            else:
                # Simple comparison
                return await self._evaluate_simple_condition(condition, resource, context)
                
        except Exception as e:
            self.logger.error(f"Condition evaluation failed: {e}")
            return False
    
    async def _evaluate_function_call(self, 
                                     condition: str, 
                                     resource: Dict[str, Any], 
                                     context: Dict[str, Any]) -> bool:
        """Evaluate function call in condition"""
        try:
            # Extract function name and arguments
            func_match = re.match(r'(\w+)\((.*)\)', condition)
            if not func_match:
                return False
            
            func_name = func_match.group(1)
            args_str = func_match.group(2)
            
            # Parse arguments
            args = [arg.strip().strip('"\'') for arg in args_str.split(',') if arg.strip()]
            
            # Call function
            if func_name in self.functions:
                return await self.functions[func_name](resource, context, *args)
            else:
                self.logger.warning(f"Unknown function: {func_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Function call evaluation failed: {e}")
            return False
    
    async def _evaluate_simple_condition(self, 
                                        condition: str, 
                                        resource: Dict[str, Any], 
                                        context: Dict[str, Any]) -> bool:
        """Evaluate simple condition expression"""
        try:
            # Handle JSONPath-like expressions
            if '.' in condition and '==' in condition:
                path, expected = condition.split('==', 1)
                path = path.strip()
                expected = expected.strip().strip('"\'')
                
                value = self._get_nested_value(resource, path)
                return str(value) == expected
            
            return False
            
        except Exception as e:
            self.logger.error(f"Simple condition evaluation failed: {e}")
            return False
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    # Custom functions for policy evaluation
    async def _func_contains(self, resource: Dict[str, Any], context: Dict[str, Any], 
                           field: str, value: str) -> bool:
        """Check if field contains value"""
        field_value = self._get_nested_value(resource, field)
        return value in str(field_value) if field_value else False
    
    async def _func_matches(self, resource: Dict[str, Any], context: Dict[str, Any], 
                          field: str, pattern: str) -> bool:
        """Check if field matches regex pattern"""
        field_value = self._get_nested_value(resource, field)
        if not field_value:
            return False
        
        return bool(re.match(pattern, str(field_value)))
    
    async def _func_greater_than(self, resource: Dict[str, Any], context: Dict[str, Any], 
                               field: str, threshold: str) -> bool:
        """Check if field value is greater than threshold"""
        field_value = self._get_nested_value(resource, field)
        try:
            return float(field_value) > float(threshold)
        except (ValueError, TypeError):
            return False
    
    async def _func_has_tag(self, resource: Dict[str, Any], context: Dict[str, Any], 
                          tag_key: str, tag_value: str = None) -> bool:
        """Check if resource has specific tag"""
        tags = resource.get('tags', {})
        if tag_value:
            return tags.get(tag_key) == tag_value
        else:
            return tag_key in tags

class ComplianceFramework:
    """Compliance framework management and automation"""
    
    def __init__(self, policy_manager: PolicyManager):
        self.policy_manager = policy_manager
        self.frameworks: Dict[str, Dict[str, Any]] = {}
        self.compliance_reports: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize standard frameworks
        self._initialize_standard_frameworks()
    
    def _initialize_standard_frameworks(self):
        """Initialize standard compliance frameworks"""
        self.frameworks = {
            'GDPR': {
                'name': 'General Data Protection Regulation',
                'version': '2018',
                'requirements': {
                    'data_encryption': 'Personal data must be encrypted',
                    'consent_management': 'User consent must be tracked and manageable',
                    'data_retention': 'Data retention policies must be enforced',
                    'breach_notification': 'Data breaches must be reported within 72 hours',
                    'right_to_erasure': 'Users must be able to request data deletion'
                },
                'controls': [
                    'encryption_at_rest',
                    'encryption_in_transit',
                    'access_logging',
                    'data_classification',
                    'consent_tracking'
                ]
            },
            'SOC2': {
                'name': 'Service Organization Control 2',
                'version': '2017',
                'requirements': {
                    'security': 'Access controls and security monitoring',
                    'availability': 'System availability and performance',
                    'processing_integrity': 'System processing completeness and accuracy',
                    'confidentiality': 'Information confidentiality protection',
                    'privacy': 'Personal information privacy protection'
                },
                'controls': [
                    'multi_factor_authentication',
                    'continuous_monitoring',
                    'change_management',
                    'incident_response',
                    'vulnerability_management'
                ]
            },
            'ISO27001': {
                'name': 'Information Security Management Systems',
                'version': '2013',
                'requirements': {
                    'risk_management': 'Systematic risk assessment and treatment',
                    'security_policy': 'Information security policies and procedures',
                    'asset_management': 'Information asset inventory and protection',
                    'access_control': 'Access control management',
                    'incident_management': 'Security incident management'
                },
                'controls': [
                    'risk_assessment',
                    'security_training',
                    'asset_inventory',
                    'access_review',
                    'security_monitoring'
                ]
            }
        }
    
    async def assess_compliance(self, 
                               framework_name: str, 
                               target_resources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess compliance against a specific framework"""
        try:
            if framework_name not in self.frameworks:
                raise ValueError(f"Unknown compliance framework: {framework_name}")
            
            framework = self.frameworks[framework_name]
            assessment_results = {
                'framework': framework_name,
                'assessment_time': datetime.utcnow().isoformat(),
                'total_resources': len(target_resources),
                'compliance_score': 0.0,
                'findings': [],
                'recommendations': []
            }
            
            total_checks = 0
            passed_checks = 0
            
            # Evaluate each resource against framework requirements
            for resource in target_resources:
                for requirement, description in framework['requirements'].items():
                    total_checks += 1
                    
                    # Check compliance for this requirement
                    compliance_result = await self._check_framework_requirement(
                        framework_name, requirement, resource
                    )
                    
                    if compliance_result['compliant']:
                        passed_checks += 1
                    else:
                        assessment_results['findings'].append({
                            'resource_id': resource.get('id', 'unknown'),
                            'requirement': requirement,
                            'description': description,
                            'status': 'non_compliant',
                            'details': compliance_result.get('details', '')
                        })
            
            # Calculate compliance score
            if total_checks > 0:
                assessment_results['compliance_score'] = (passed_checks / total_checks) * 100
            
            # Generate recommendations
            assessment_results['recommendations'] = self._generate_compliance_recommendations(
                framework_name, assessment_results['findings']
            )
            
            # Store assessment result
            assessment_id = str(uuid.uuid4())
            self.compliance_reports[assessment_id] = assessment_results
            
            self.logger.info(f"Compliance assessment completed: {framework_name} - {assessment_results['compliance_score']:.1f}%")
            return assessment_results
            
        except Exception as e:
            self.logger.error(f"Compliance assessment failed: {e}")
            return {'error': str(e)}
    
    async def _check_framework_requirement(self, 
                                          framework_name: str, 
                                          requirement: str, 
                                          resource: Dict[str, Any]) -> Dict[str, Any]:
        """Check specific framework requirement against resource"""
        try:
            # This would implement specific checks for each framework requirement
            # For demonstration, we'll use simplified logic
            
            if framework_name == 'GDPR':
                if requirement == 'data_encryption':
                    return {
                        'compliant': resource.get('encrypted', False),
                        'details': 'Encryption status checked'
                    }
                elif requirement == 'consent_management':
                    return {
                        'compliant': 'consent_tracking' in resource.get('features', []),
                        'details': 'Consent tracking feature checked'
                    }
            
            elif framework_name == 'SOC2':
                if requirement == 'security':
                    return {
                        'compliant': resource.get('security_score', 0) >= 80,
                        'details': f"Security score: {resource.get('security_score', 0)}"
                    }
                elif requirement == 'availability':
                    return {
                        'compliant': resource.get('uptime_percentage', 0) >= 99.9,
                        'details': f"Uptime: {resource.get('uptime_percentage', 0)}%"
                    }
            
            # Default to compliant if no specific check
            return {'compliant': True, 'details': 'No specific check implemented'}
            
        except Exception as e:
            self.logger.error(f"Framework requirement check failed: {e}")
            return {'compliant': False, 'details': str(e)}
    
    def _generate_compliance_recommendations(self, 
                                           framework_name: str, 
                                           findings: List[Dict[str, Any]]) -> List[str]:
        """Generate compliance recommendations based on findings"""
        recommendations = set()
        
        for finding in findings:
            requirement = finding['requirement']
            
            if framework_name == 'GDPR':
                if requirement == 'data_encryption':
                    recommendations.add('Implement encryption at rest and in transit for all personal data')
                elif requirement == 'consent_management':
                    recommendations.add('Deploy consent management system to track user preferences')
                elif requirement == 'data_retention':
                    recommendations.add('Implement automated data retention and deletion policies')
            
            elif framework_name == 'SOC2':
                if requirement == 'security':
                    recommendations.add('Enhance security controls and monitoring systems')
                elif requirement == 'availability':
                    recommendations.add('Implement high availability architecture and monitoring')
            
            elif framework_name == 'ISO27001':
                if requirement == 'risk_management':
                    recommendations.add('Conduct comprehensive risk assessment and implement treatment plans')
                elif requirement == 'access_control':
                    recommendations.add('Review and strengthen access control mechanisms')
        
        return list(recommendations)

class RiskAssessment:
    """Enterprise risk assessment and management"""
    
    def __init__(self):
        self.risk_models: Dict[str, Dict[str, Any]] = {}
        self.assessment_history: List[RiskAssessmentResult] = []
        self.risk_thresholds = {
            'critical': 90,
            'high': 70,
            'medium': 40,
            'low': 20
        }
        self.logger = logging.getLogger(__name__)
    
    async def conduct_risk_assessment(self, 
                                     target_resource: str, 
                                     assessment_context: Dict[str, Any]) -> RiskAssessmentResult:
        """Conduct comprehensive risk assessment"""
        try:
            self.logger.info(f"Conducting risk assessment for: {target_resource}")
            
            # Collect risk factors
            risk_factors = await self._collect_risk_factors(target_resource, assessment_context)
            
            # Calculate risk scores
            risk_scores = await self._calculate_risk_scores(risk_factors)
            
            # Determine overall risk level
            overall_score = sum(risk_scores.values()) / len(risk_scores) if risk_scores else 0
            risk_level = self._determine_risk_level(overall_score)
            
            # Identify specific risks
            identified_risks = await self._identify_specific_risks(risk_factors, risk_scores)
            
            # Generate mitigation recommendations
            mitigation_recommendations = self._generate_mitigation_recommendations(identified_risks)
            
            # Check compliance status
            compliance_status = await self._check_compliance_status(target_resource)
            
            # Create assessment result
            result = RiskAssessmentResult(
                assessment_id=str(uuid.uuid4()),
                target_resource=target_resource,
                assessment_time=datetime.utcnow(),
                overall_risk_score=overall_score,
                risk_level=risk_level,
                identified_risks=identified_risks,
                mitigation_recommendations=mitigation_recommendations,
                compliance_status=compliance_status,
                next_assessment_due=datetime.utcnow() + timedelta(days=90),
                assessment_metadata=assessment_context
            )
            
            # Store assessment
            self.assessment_history.append(result)
            
            self.logger.info(f"Risk assessment completed: {risk_level.value} risk level")
            return result
            
        except Exception as e:
            self.logger.error(f"Risk assessment failed: {e}")
            # Return minimal result with error
            return RiskAssessmentResult(
                assessment_id=str(uuid.uuid4()),
                target_resource=target_resource,
                assessment_time=datetime.utcnow(),
                overall_risk_score=100.0,  # Assume high risk on error
                risk_level=RiskLevel.CRITICAL,
                identified_risks=[{'type': 'assessment_error', 'description': str(e)}],
                mitigation_recommendations=['Fix assessment system errors'],
                compliance_status={'status': 'unknown'},
                next_assessment_due=datetime.utcnow() + timedelta(days=7),
                assessment_metadata={'error': str(e)}
            )
    
    async def _collect_risk_factors(self, 
                                   target_resource: str, 
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect risk factors for assessment"""
        risk_factors = {
            'security_vulnerabilities': [],
            'compliance_gaps': [],
            'operational_risks': [],
            'technical_debt': [],
            'external_dependencies': [],
            'data_sensitivity': 'unknown',
            'user_access_level': 'unknown',
            'network_exposure': 'unknown'
        }
        
        # This would integrate with various security and monitoring tools
        # For demonstration, we'll use mock data
        
        return risk_factors
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level based on score"""
        if risk_score >= self.risk_thresholds['critical']:
            return RiskLevel.CRITICAL
        elif risk_score >= self.risk_thresholds['high']:
            return RiskLevel.HIGH
        elif risk_score >= self.risk_thresholds['medium']:
            return RiskLevel.MEDIUM
        elif risk_score >= self.risk_thresholds['low']:
            return RiskLevel.LOW
        else:
            return RiskLevel.INFORMATIONAL

class SecurityGovernance:
    """Security governance and automation"""
    
    def __init__(self, policy_manager: PolicyManager):
        self.policy_manager = policy_manager
        self.security_controls: Dict[str, Dict[str, Any]] = {}
        self.security_incidents: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(__name__)
    
    async def enforce_security_policies(self, 
                                       resource: Dict[str, Any]) -> List[PolicyViolation]:
        """Enforce security policies on resource"""
        try:
            # Add security context
            security_context = {
                'security_scan_time': datetime.utcnow().isoformat(),
                'scanner': 'security_governance',
                'scan_type': 'policy_enforcement'
            }
            
            # Evaluate security policies
            violations = await self.policy_manager.evaluate_policies(resource, security_context)
            
            # Filter security-related violations
            security_violations = [v for v in violations if 'security' in v.context.get('policy_type', '')]
            
            # Handle critical security violations
            for violation in security_violations:
                if violation.severity == RiskLevel.CRITICAL:
                    await self._handle_critical_security_violation(violation, resource)
            
            return security_violations
            
        except Exception as e:
            self.logger.error(f"Security policy enforcement failed: {e}")
            return []
    
    async def _handle_critical_security_violation(self, 
                                                 violation: PolicyViolation, 
                                                 resource: Dict[str, Any]):
        """Handle critical security policy violations"""
        try:
            # Log security incident
            incident = {
                'incident_id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'critical_policy_violation',
                'resource_id': resource.get('id', 'unknown'),
                'violation_id': violation.violation_id,
                'description': violation.description,
                'status': 'open'
            }
            
            self.security_incidents.append(incident)
            
            # Immediate containment actions
            await self._execute_containment_actions(violation, resource)
            
            # Alert security team
            await self._alert_security_team(incident)
            
            self.logger.critical(f"Critical security violation handled: {violation.violation_id}")
            
        except Exception as e:
            self.logger.error(f"Critical security violation handling failed: {e}")

class GovernanceEngine:
    """Main governance engine orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize components
        storage_path = config.get('storage_path', './governance_data')
        self.policy_manager = PolicyManager(storage_path)
        self.compliance_framework = ComplianceFramework(self.policy_manager)
        self.risk_assessment = RiskAssessment()
        self.security_governance = SecurityGovernance(self.policy_manager)
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize governance engine"""
        try:
            self.logger.info("Initializing enterprise governance engine...")
            
            # Load default policies
            await self._load_default_policies()
            
            # Initialize compliance frameworks
            await self._initialize_compliance_monitoring()
            
            # Start automated governance tasks
            await self._start_automated_governance()
            
            self.logger.info("Enterprise governance engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Governance engine initialization failed: {e}")
            return False
    
    async def evaluate_resource_governance(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive governance evaluation of a resource"""
        try:
            results = {
                'resource_id': resource.get('id', 'unknown'),
                'evaluation_time': datetime.utcnow().isoformat(),
                'policy_violations': [],
                'risk_assessment': None,
                'compliance_status': {},
                'recommendations': []
            }
            
            # Policy evaluation
            violations = await self.policy_manager.evaluate_policies(resource)
            results['policy_violations'] = [asdict(v) for v in violations]
            
            # Risk assessment
            risk_result = await self.risk_assessment.conduct_risk_assessment(
                resource.get('id', 'unknown'), 
                {'resource': resource}
            )
            results['risk_assessment'] = asdict(risk_result)
            
            # Security governance
            security_violations = await self.security_governance.enforce_security_policies(resource)
            
            # Generate consolidated recommendations
            all_violations = violations + security_violations
            results['recommendations'] = self._generate_governance_recommendations(all_violations, risk_result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Resource governance evaluation failed: {e}")
            return {'error': str(e)}
    
    def _generate_governance_recommendations(self, 
                                           violations: List[PolicyViolation], 
                                           risk_result: RiskAssessmentResult) -> List[str]:
        """Generate consolidated governance recommendations"""
        recommendations = set()
        
        # Policy-based recommendations
        for violation in violations:
            recommendations.update(violation.remediation_suggestions)
        
        # Risk-based recommendations
        recommendations.update(risk_result.mitigation_recommendations)
        
        # Priority recommendations for critical issues
        critical_violations = [v for v in violations if v.severity == RiskLevel.CRITICAL]
        if critical_violations:
            recommendations.add("URGENT: Address critical policy violations immediately")
        
        if risk_result.risk_level == RiskLevel.CRITICAL:
            recommendations.add("URGENT: Implement critical risk mitigation measures")
        
        return list(recommendations)

# Exception classes
class PolicyViolationError(Exception):
    """Raised when a policy violation blocks an action"""
    pass

class GovernanceError(Exception):
    """General governance system error"""
    pass