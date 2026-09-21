"""
Security Advanced Services Module
Comprehensive advanced security, privacy, and cryptographic systems
"""

from .homomorphic_encryption import (
    HomomorphicComputationEngine,
    HomomorphicCiphertext,
    HomomorphicKeyPair,
    ComputationResult,
    HomomorphicScheme,
    SecurityLevel,
    create_homomorphic_engine
)

from .differential_privacy import (
    DifferentialPrivacyEngine,
    PrivacyMechanism,
    NoiseDistribution,
    PrivacyParameters,
    DPQuery,
    DPQueryResult,
    PrivacyBudget,
    SensitivityAnalyzer,
    create_differential_privacy_engine
)

from .secure_multiparty_computation import (
    SMPCEngine,
    SMPCProtocol,
    SecretShare,
    SMPCParty,
    SMPCComputation,
    SMPCResult,
    create_smpc_engine
)

from .federated_learning import (
    FederatedLearningServer,
    FederatedLearningClient,
    FederatedRound,
    ClientUpdate,
    AggregatedModel,
    FederatedAlgorithm,
    AggregationMethod,
    ClientSelectionStrategy,
    create_federated_server,
    create_federated_client
)

from .record_linkage import (
    PrivacyPreservingRecordLinkage,
    LinkageMethod,
    MatchingStrategy,
    PrivacyLevel,
    RecordIdentifier,
    LinkageField,
    LinkageMatch,
    LinkageResult,
    BloomFilterConfig,
    create_record_linkage_engine
)

from .secure_enclaves import (
    SecureEnclaveManager,
    EnclaveType,
    EnclaveState,
    AttestationType,
    SecurityLevel as EnclaveSecurityLevel,
    EnclaveConfiguration,
    EnclaveIdentity,
    AttestationEvidence,
    SecureComputationRequest,
    SecureComputationResult,
    create_secure_enclave_manager
)

from .anonymous_credentials import (
    AttributeBasedCredentialSystem,
    CredentialType,
    AttributeType,
    ProofType,
    CredentialStatus,
    AnonymousCredential,
    CredentialRequest,
    CredentialProof,
    PresentationRequest,
    CredentialPresentation,
    create_anonymous_credential_system
)

from .decoy_data import (
    DecoyDataGenerator,
    DecoyType,
    DetectionMethod,
    DecoyStatus,
    RealisticLevel,
    DecoyMetadata,
    DecoyDetection,
    SyntheticProfile,
    CanaryToken,
    create_decoy_data_generator
)

from .behavioral_authentication import (
    BehavioralAuthenticationSystem,
    BehavioralMetric,
    AuthenticationDecision,
    ThreatLevel,
    BehavioralProfile,
    BehavioralSample,
    AuthenticationAttempt,
    AnomalyDetection,
    create_behavioral_authentication_system
)

from .quantum_safe_encryption import (
    QuantumSafeCryptoSystem,
    QuantumSafeAlgorithm,
    CryptoFunction,
    MigrationStatus,
    SecurityLevel as QuantumSecurityLevel,
    CryptoAsset,
    MigrationPlan,
    HybridKeyPair,
    QuantumThreatAssessment,
    create_quantum_safe_crypto_system
)

from .privacy_budget_management import (
    PrivacyBudgetManager,
    BudgetType,
    BudgetScope,
    PrivacyMechanism as BudgetPrivacyMechanism,
    BudgetStatus,
    AllocationStrategy,
    PrivacyBudget,
    BudgetConsumption,
    BudgetAllocation,
    PrivacyAccountingRecord,
    BudgetAlert,
    create_privacy_budget_manager
)

from .data_sovereignty import (
    DataSovereigntySystem,
    JurisdictionType,
    DataClassification,
    TransferMechanism,
    ComplianceRegime,
    ViolationType,
    GeographicLocation,
    DataResidencyRule,
    DataAsset,
    TransferRequest,
    TransferApproval,
    ComplianceViolation,
    create_data_sovereignty_system
)

__all__ = [
    # Homomorphic Encryption
    'HomomorphicComputationEngine',
    'HomomorphicCiphertext',
    'HomomorphicKeyPair',
    'ComputationResult',
    'HomomorphicScheme',
    'SecurityLevel',
    'create_homomorphic_engine',
    
    # Differential Privacy
    'DifferentialPrivacyEngine',
    'PrivacyMechanism',
    'NoiseDistribution',
    'PrivacyParameters',
    'DPQuery',
    'DPQueryResult',
    'PrivacyBudget',
    'SensitivityAnalyzer',
    'create_differential_privacy_engine',
    
    # Secure Multi-Party Computation
    'SMPCEngine',
    'SMPCProtocol',
    'SecretShare',
    'SMPCParty',
    'SMPCComputation',
    'SMPCResult',
    'create_smpc_engine',
    
    # Federated Learning
    'FederatedLearningServer',
    'FederatedLearningClient',
    'FederatedRound',
    'ClientUpdate',
    'AggregatedModel',
    'FederatedAlgorithm',
    'AggregationMethod',
    'ClientSelectionStrategy',
    'create_federated_server',
    'create_federated_client',
    
    # Privacy-Preserving Record Linkage
    'PrivacyPreservingRecordLinkage',
    'LinkageMethod',
    'MatchingStrategy',
    'PrivacyLevel',
    'RecordIdentifier',
    'LinkageField',
    'LinkageMatch',
    'LinkageResult',
    'BloomFilterConfig',
    'create_record_linkage_engine',
    
    # Secure Enclaves
    'SecureEnclaveManager',
    'EnclaveType',
    'EnclaveState',
    'AttestationType',
    'EnclaveSecurityLevel',
    'EnclaveConfiguration',
    'EnclaveIdentity',
    'AttestationEvidence',
    'SecureComputationRequest',
    'SecureComputationResult',
    'create_secure_enclave_manager',
    
    # Anonymous Credentials
    'AttributeBasedCredentialSystem',
    'CredentialType',
    'AttributeType',
    'ProofType',
    'CredentialStatus',
    'AnonymousCredential',
    'CredentialRequest',
    'CredentialProof',
    'PresentationRequest',
    'CredentialPresentation',
    'create_anonymous_credential_system',
    
    # Decoy Data Generation
    'DecoyDataGenerator',
    'DecoyType',
    'DetectionMethod',
    'DecoyStatus',
    'RealisticLevel',
    'DecoyMetadata',
    'DecoyDetection',
    'SyntheticProfile',
    'CanaryToken',
    'create_decoy_data_generator',
    
    # Behavioral Authentication
    'BehavioralAuthenticationSystem',
    'BehavioralMetric',
    'AuthenticationDecision',
    'ThreatLevel',
    'BehavioralProfile',
    'BehavioralSample',
    'AuthenticationAttempt',
    'AnomalyDetection',
    'create_behavioral_authentication_system',
    
    # Quantum-Safe Encryption
    'QuantumSafeCryptoSystem',
    'QuantumSafeAlgorithm',
    'CryptoFunction',
    'MigrationStatus',
    'QuantumSecurityLevel',
    'CryptoAsset',
    'MigrationPlan',
    'HybridKeyPair',
    'QuantumThreatAssessment',
    'create_quantum_safe_crypto_system',
    
    # Privacy Budget Management
    'PrivacyBudgetManager',
    'BudgetType',
    'BudgetScope',
    'BudgetPrivacyMechanism',
    'BudgetStatus',
    'AllocationStrategy',
    'PrivacyBudget',
    'BudgetConsumption',
    'BudgetAllocation',
    'PrivacyAccountingRecord',
    'BudgetAlert',
    'create_privacy_budget_manager',
    
    # Data Sovereignty
    'DataSovereigntySystem',
    'JurisdictionType',
    'DataClassification',
    'TransferMechanism',
    'ComplianceRegime',
    'ViolationType',
    'GeographicLocation',
    'DataResidencyRule',
    'DataAsset',
    'TransferRequest',
    'TransferApproval',
    'ComplianceViolation',
    'create_data_sovereignty_system'
]