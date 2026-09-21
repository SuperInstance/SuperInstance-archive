"""
Federated Learning Infrastructure for Privacy-Preserving Machine Learning
Distributed ML system that trains models across multiple parties without centralizing data
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import secrets
import math
from abc import ABC, abstractmethod
from collections import defaultdict
import pickle
import gzip

logger = logging.getLogger(__name__)

class FederatedAlgorithm(Enum):
    """Types of federated learning algorithms"""
    FEDERATED_AVERAGING = "fed_avg"        # FedAvg (McMahan et al.)
    FEDERATED_SGD = "fed_sgd"             # Simple federated SGD
    FEDERATED_PROXIMAL = "fed_prox"       # FedProx with proximal term
    FEDERATED_NOVA = "fed_nova"           # FedNova with normalized averaging
    SCAFFOLD = "scaffold"                  # SCAFFOLD with control variates
    FEDERATED_OPT = "fed_opt"             # FedOpt with server optimization
    PERSONALIZED_FL = "personalized"      # Personalized federated learning
    HIERARCHICAL_FL = "hierarchical"      # Multi-tier federated learning

class AggregationMethod(Enum):
    """Methods for aggregating model updates"""
    SIMPLE_AVERAGE = "simple_avg"
    WEIGHTED_AVERAGE = "weighted_avg"
    MEDIAN_AGGREGATION = "median"
    TRIMMED_MEAN = "trimmed_mean"
    GEOMETRIC_MEDIAN = "geometric_median"
    COORDINATE_WISE_MEDIAN = "coord_median"
    BYZANTINE_ROBUST = "byzantine_robust"

class ClientSelectionStrategy(Enum):
    """Strategies for selecting clients in each round"""
    RANDOM_SELECTION = "random"
    ROUND_ROBIN = "round_robin"
    AVAILABILITY_BASED = "availability"
    DATA_SIZE_WEIGHTED = "data_weighted"
    LOSS_BASED = "loss_based"
    STALENESS_AWARE = "staleness_aware"

class PrivacyMechanism(Enum):
    """Privacy mechanisms for federated learning"""
    NO_PRIVACY = "none"
    DIFFERENTIAL_PRIVACY = "dp"
    SECURE_AGGREGATION = "secure_agg"
    HOMOMORPHIC_ENCRYPTION = "he"
    MULTI_PARTY_COMPUTATION = "mpc"
    LOCAL_DIFFERENTIAL_PRIVACY = "ldp"

@dataclass
class ModelParameters:
    """Model parameters/weights"""
    parameters: Dict[str, np.ndarray]
    parameter_count: int
    layer_info: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.parameter_count:
            self.parameter_count = sum(param.size for param in self.parameters.values())
    
    def to_vector(self) -> np.ndarray:
        """Flatten parameters to a single vector"""
        return np.concatenate([param.flatten() for param in self.parameters.values()])
    
    def from_vector(self, vector: np.ndarray, shapes: Dict[str, Tuple]):
        """Reconstruct parameters from vector"""
        idx = 0
        for name, shape in shapes.items():
            size = np.prod(shape)
            self.parameters[name] = vector[idx:idx+size].reshape(shape)
            idx += size

@dataclass
class ClientUpdate:
    """Update from a federated learning client"""
    client_id: str
    round_number: int
    model_update: ModelParameters
    local_epochs: int
    data_samples: int
    training_loss: float
    training_accuracy: Optional[float] = None
    computation_time: float = 0.0
    communication_cost: int = 0
    privacy_budget_used: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class FederatedRound:
    """Information about a federated learning round"""
    round_number: int
    selected_clients: List[str]
    global_model: ModelParameters
    client_updates: List[ClientUpdate] = field(default_factory=list)
    aggregated_update: Optional[ModelParameters] = None
    round_metrics: Dict[str, float] = field(default_factory=dict)
    privacy_cost: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

@dataclass
class FederatedClient:
    """Federated learning client"""
    client_id: str
    data_samples: int
    model_architecture: Dict[str, Any]
    privacy_budget: float
    compute_capacity: float = 1.0
    network_bandwidth: float = 1.0
    availability_schedule: Optional[Dict[str, bool]] = None
    local_model: Optional[ModelParameters] = None
    personalization_data: Dict[str, Any] = field(default_factory=dict)
    client_stats: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_available(self) -> bool:
        """Check if client is currently available"""
        if self.availability_schedule is None:
            return True
        current_hour = datetime.now().hour
        return self.availability_schedule.get(str(current_hour), True)

@dataclass
class FederatedLearningConfig:
    """Configuration for federated learning"""
    algorithm: FederatedAlgorithm
    aggregation_method: AggregationMethod
    client_selection: ClientSelectionStrategy
    privacy_mechanism: PrivacyMechanism
    total_rounds: int
    clients_per_round: int
    local_epochs: int
    learning_rate: float
    privacy_epsilon: float = 1.0
    convergence_threshold: float = 1e-6
    max_staleness: int = 5
    byzantine_tolerance: float = 0.1  # Fraction of malicious clients to tolerate

class FederatedModelTrainer(ABC):
    """Abstract base class for federated model trainers"""
    
    @abstractmethod
    async def local_train(self, client_id: str, global_model: ModelParameters, 
                         local_epochs: int) -> ClientUpdate:
        """Perform local training on client"""
        pass
    
    @abstractmethod
    async def evaluate_model(self, model: ModelParameters, 
                           client_id: Optional[str] = None) -> Dict[str, float]:
        """Evaluate model performance"""
        pass

class LinearModelTrainer(FederatedModelTrainer):
    """Trainer for linear models (logistic regression, linear regression)"""
    
    def __init__(self, feature_dim: int, num_classes: int = 1):
        self.feature_dim = feature_dim
        self.num_classes = num_classes
        self.client_datasets = {}  # Simulated client data
        
    async def initialize_client_data(self, client_id: str, X: np.ndarray, y: np.ndarray):
        """Initialize training data for a client"""
        self.client_datasets[client_id] = {'X': X, 'y': y}
        
    async def local_train(self, client_id: str, global_model: ModelParameters, 
                         local_epochs: int) -> ClientUpdate:
        """Perform local SGD training"""
        if client_id not in self.client_datasets:
            raise ValueError(f"No data found for client {client_id}")
        
        start_time = datetime.now()
        data = self.client_datasets[client_id]
        X, y = data['X'], data['y']
        n_samples = X.shape[0]
        
        # Initialize with global model parameters
        if 'weights' in global_model.parameters:
            weights = global_model.parameters['weights'].copy()
            bias = global_model.parameters.get('bias', np.zeros(self.num_classes))
        else:
            weights = np.random.normal(0, 0.01, (self.feature_dim, self.num_classes))
            bias = np.zeros(self.num_classes)
        
        learning_rate = 0.01
        losses = []
        
        # Local training loop
        for epoch in range(local_epochs):
            # Shuffle data
            indices = np.random.permutation(n_samples)
            X_shuffled, y_shuffled = X[indices], y[indices]
            
            epoch_loss = 0.0
            batch_size = min(32, n_samples)
            
            for i in range(0, n_samples, batch_size):
                batch_X = X_shuffled[i:i+batch_size]
                batch_y = y_shuffled[i:i+batch_size]
                
                # Forward pass
                if self.num_classes == 1:
                    # Linear regression
                    predictions = batch_X @ weights + bias
                    loss = np.mean((predictions.flatten() - batch_y) ** 2)
                    
                    # Backward pass
                    grad_weights = 2 * batch_X.T @ (predictions.flatten() - batch_y) / len(batch_y)
                    grad_bias = 2 * np.mean(predictions.flatten() - batch_y)
                    
                else:
                    # Logistic regression
                    logits = batch_X @ weights + bias
                    predictions = self._softmax(logits)
                    loss = self._cross_entropy_loss(predictions, batch_y)
                    
                    # Backward pass
                    grad_logits = predictions - self._one_hot(batch_y, self.num_classes)
                    grad_weights = batch_X.T @ grad_logits / len(batch_y)
                    grad_bias = np.mean(grad_logits, axis=0)
                
                # Update parameters
                weights -= learning_rate * grad_weights
                bias -= learning_rate * grad_bias
                epoch_loss += loss
            
            losses.append(epoch_loss / (n_samples // batch_size))
        
        # Create model update
        updated_model = ModelParameters(
            parameters={'weights': weights, 'bias': bias},
            parameter_count=weights.size + bias.size
        )
        
        training_time = (datetime.now() - start_time).total_seconds()
        final_loss = losses[-1] if losses else 0.0
        
        return ClientUpdate(
            client_id=client_id,
            round_number=0,  # Will be set by server
            model_update=updated_model,
            local_epochs=local_epochs,
            data_samples=n_samples,
            training_loss=final_loss,
            computation_time=training_time,
            communication_cost=updated_model.parameter_count * 4  # Assume 4 bytes per parameter
        )
    
    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax activation function"""
        exp_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return exp_x / np.sum(exp_x, axis=1, keepdims=True)
    
    def _cross_entropy_loss(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Cross-entropy loss function"""
        targets_one_hot = self._one_hot(targets, self.num_classes)
        return -np.mean(np.sum(targets_one_hot * np.log(predictions + 1e-15), axis=1))
    
    def _one_hot(self, targets: np.ndarray, num_classes: int) -> np.ndarray:
        """Convert targets to one-hot encoding"""
        one_hot = np.zeros((len(targets), num_classes))
        one_hot[np.arange(len(targets)), targets.astype(int)] = 1
        return one_hot
    
    async def evaluate_model(self, model: ModelParameters, 
                           client_id: Optional[str] = None) -> Dict[str, float]:
        """Evaluate model on client data or global test set"""
        if client_id and client_id in self.client_datasets:
            data = self.client_datasets[client_id]
            X, y = data['X'], data['y']
        else:
            # Would use global test set in practice
            return {'accuracy': 0.0, 'loss': 0.0}
        
        weights = model.parameters['weights']
        bias = model.parameters.get('bias', np.zeros(self.num_classes))
        
        if self.num_classes == 1:
            # Linear regression
            predictions = X @ weights + bias
            mse = np.mean((predictions.flatten() - y) ** 2)
            return {'mse': mse, 'rmse': np.sqrt(mse)}
        else:
            # Logistic regression
            logits = X @ weights + bias
            predictions = self._softmax(logits)
            predicted_classes = np.argmax(predictions, axis=1)
            accuracy = np.mean(predicted_classes == y)
            loss = self._cross_entropy_loss(predictions, y)
            return {'accuracy': accuracy, 'loss': loss}

class ModelAggregator:
    """Aggregates model updates from multiple clients"""
    
    def __init__(self, aggregation_method: AggregationMethod):
        self.aggregation_method = aggregation_method
        
    async def aggregate_updates(self, client_updates: List[ClientUpdate], 
                              global_model: ModelParameters) -> ModelParameters:
        """Aggregate client updates into new global model"""
        
        if not client_updates:
            return global_model
        
        if self.aggregation_method == AggregationMethod.SIMPLE_AVERAGE:
            return await self._simple_average(client_updates)
        
        elif self.aggregation_method == AggregationMethod.WEIGHTED_AVERAGE:
            return await self._weighted_average(client_updates)
        
        elif self.aggregation_method == AggregationMethod.MEDIAN_AGGREGATION:
            return await self._median_aggregation(client_updates)
        
        elif self.aggregation_method == AggregationMethod.TRIMMED_MEAN:
            return await self._trimmed_mean_aggregation(client_updates)
        
        elif self.aggregation_method == AggregationMethod.BYZANTINE_ROBUST:
            return await self._byzantine_robust_aggregation(client_updates)
        
        else:
            return await self._simple_average(client_updates)
    
    async def _simple_average(self, client_updates: List[ClientUpdate]) -> ModelParameters:
        """Simple averaging of model parameters"""
        if not client_updates:
            raise ValueError("No client updates provided")
        
        # Initialize aggregated parameters
        first_update = client_updates[0].model_update
        aggregated_params = {}
        
        for param_name in first_update.parameters:
            param_shape = first_update.parameters[param_name].shape
            aggregated_params[param_name] = np.zeros(param_shape)
        
        # Sum all parameters
        for update in client_updates:
            for param_name, param_value in update.model_update.parameters.items():
                aggregated_params[param_name] += param_value
        
        # Average
        num_clients = len(client_updates)
        for param_name in aggregated_params:
            aggregated_params[param_name] /= num_clients
        
        return ModelParameters(
            parameters=aggregated_params,
            parameter_count=sum(param.size for param in aggregated_params.values())
        )
    
    async def _weighted_average(self, client_updates: List[ClientUpdate]) -> ModelParameters:
        """Weighted averaging based on number of data samples"""
        if not client_updates:
            raise ValueError("No client updates provided")
        
        # Calculate weights based on data samples
        total_samples = sum(update.data_samples for update in client_updates)
        weights = [update.data_samples / total_samples for update in client_updates]
        
        # Initialize aggregated parameters
        first_update = client_updates[0].model_update
        aggregated_params = {}
        
        for param_name in first_update.parameters:
            param_shape = first_update.parameters[param_name].shape
            aggregated_params[param_name] = np.zeros(param_shape)
        
        # Weighted sum
        for update, weight in zip(client_updates, weights):
            for param_name, param_value in update.model_update.parameters.items():
                aggregated_params[param_name] += weight * param_value
        
        return ModelParameters(
            parameters=aggregated_params,
            parameter_count=sum(param.size for param in aggregated_params.values())
        )
    
    async def _median_aggregation(self, client_updates: List[ClientUpdate]) -> ModelParameters:
        """Coordinate-wise median aggregation (Byzantine-robust)"""
        if not client_updates:
            raise ValueError("No client updates provided")
        
        # Stack all parameter vectors
        param_vectors = []
        for update in client_updates:
            param_vectors.append(update.model_update.to_vector())
        
        param_matrix = np.stack(param_vectors, axis=0)  # Shape: (num_clients, num_params)
        
        # Compute coordinate-wise median
        median_vector = np.median(param_matrix, axis=0)
        
        # Reconstruct parameter structure
        first_update = client_updates[0].model_update
        shapes = {name: param.shape for name, param in first_update.parameters.items()}
        
        aggregated_model = ModelParameters(parameters={}, parameter_count=len(median_vector))
        aggregated_model.from_vector(median_vector, shapes)
        
        return aggregated_model
    
    async def _trimmed_mean_aggregation(self, client_updates: List[ClientUpdate], 
                                      trim_ratio: float = 0.1) -> ModelParameters:
        """Trimmed mean aggregation (removes outliers)"""
        if not client_updates:
            raise ValueError("No client updates provided")
        
        # Stack parameter vectors
        param_vectors = []
        for update in client_updates:
            param_vectors.append(update.model_update.to_vector())
        
        param_matrix = np.stack(param_vectors, axis=0)
        
        # Calculate trimmed mean coordinate-wise
        num_clients = param_matrix.shape[0]
        trim_count = int(num_clients * trim_ratio)
        
        trimmed_mean = np.zeros(param_matrix.shape[1])
        
        for i in range(param_matrix.shape[1]):
            sorted_values = np.sort(param_matrix[:, i])
            trimmed_values = sorted_values[trim_count:num_clients-trim_count]
            trimmed_mean[i] = np.mean(trimmed_values)
        
        # Reconstruct parameter structure
        first_update = client_updates[0].model_update
        shapes = {name: param.shape for name, param in first_update.parameters.items()}
        
        aggregated_model = ModelParameters(parameters={}, parameter_count=len(trimmed_mean))
        aggregated_model.from_vector(trimmed_mean, shapes)
        
        return aggregated_model
    
    async def _byzantine_robust_aggregation(self, client_updates: List[ClientUpdate]) -> ModelParameters:
        """Byzantine-robust aggregation using coordinate-wise median"""
        # For simplicity, use median aggregation as Byzantine-robust method
        return await self._median_aggregation(client_updates)

class ClientSelector:
    """Selects clients for each federated learning round"""
    
    def __init__(self, selection_strategy: ClientSelectionStrategy):
        self.selection_strategy = selection_strategy
        self.selection_history = []
        
    async def select_clients(self, available_clients: List[FederatedClient], 
                           num_clients: int, round_number: int) -> List[str]:
        """Select clients for the current round"""
        
        if num_clients > len(available_clients):
            num_clients = len(available_clients)
        
        if self.selection_strategy == ClientSelectionStrategy.RANDOM_SELECTION:
            selected = await self._random_selection(available_clients, num_clients)
        
        elif self.selection_strategy == ClientSelectionStrategy.ROUND_ROBIN:
            selected = await self._round_robin_selection(available_clients, num_clients, round_number)
        
        elif self.selection_strategy == ClientSelectionStrategy.DATA_SIZE_WEIGHTED:
            selected = await self._data_weighted_selection(available_clients, num_clients)
        
        elif self.selection_strategy == ClientSelectionStrategy.AVAILABILITY_BASED:
            selected = await self._availability_based_selection(available_clients, num_clients)
        
        else:
            selected = await self._random_selection(available_clients, num_clients)
        
        self.selection_history.append({
            'round': round_number,
            'selected_clients': selected,
            'strategy': self.selection_strategy.value
        })
        
        return selected
    
    async def _random_selection(self, clients: List[FederatedClient], num_clients: int) -> List[str]:
        """Random client selection"""
        available_clients = [c for c in clients if c.is_available]
        selected_indices = np.random.choice(len(available_clients), size=num_clients, replace=False)
        return [available_clients[i].client_id for i in selected_indices]
    
    async def _round_robin_selection(self, clients: List[FederatedClient], 
                                   num_clients: int, round_number: int) -> List[str]:
        """Round-robin client selection"""
        available_clients = [c for c in clients if c.is_available]
        start_idx = (round_number * num_clients) % len(available_clients)
        selected_clients = []
        
        for i in range(num_clients):
            idx = (start_idx + i) % len(available_clients)
            selected_clients.append(available_clients[idx].client_id)
        
        return selected_clients
    
    async def _data_weighted_selection(self, clients: List[FederatedClient], 
                                     num_clients: int) -> List[str]:
        """Select clients weighted by their data size"""
        available_clients = [c for c in clients if c.is_available]
        data_sizes = np.array([c.data_samples for c in available_clients])
        
        # Probability proportional to data size
        probabilities = data_sizes / np.sum(data_sizes)
        
        selected_indices = np.random.choice(
            len(available_clients), 
            size=num_clients, 
            replace=False, 
            p=probabilities
        )
        
        return [available_clients[i].client_id for i in selected_indices]
    
    async def _availability_based_selection(self, clients: List[FederatedClient], 
                                          num_clients: int) -> List[str]:
        """Select clients based on availability and compute capacity"""
        available_clients = [c for c in clients if c.is_available]
        
        # Score based on compute capacity and network bandwidth
        scores = []
        for client in available_clients:
            score = client.compute_capacity * client.network_bandwidth
            scores.append(score)
        
        scores = np.array(scores)
        probabilities = scores / np.sum(scores)
        
        selected_indices = np.random.choice(
            len(available_clients), 
            size=num_clients, 
            replace=False, 
            p=probabilities
        )
        
        return [available_clients[i].client_id for i in selected_indices]

class PrivacyPreservingFL:
    """Privacy-preserving mechanisms for federated learning"""
    
    @staticmethod
    async def apply_differential_privacy(model_update: ModelParameters, 
                                       epsilon: float, delta: float = 1e-6) -> ModelParameters:
        """Apply differential privacy to model updates"""
        # Calculate noise scale based on model sensitivity and privacy parameters
        sensitivity = 1.0  # Simplified; would calculate based on model and data
        noise_scale = sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / epsilon
        
        # Add Gaussian noise to parameters
        noisy_params = {}
        for param_name, param_value in model_update.parameters.items():
            noise = np.random.normal(0, noise_scale, param_value.shape)
            noisy_params[param_name] = param_value + noise
        
        return ModelParameters(
            parameters=noisy_params,
            parameter_count=model_update.parameter_count,
            metadata={**model_update.metadata, 'dp_applied': True, 'epsilon': epsilon}
        )
    
    @staticmethod
    async def secure_aggregation_simulation(client_updates: List[ClientUpdate]) -> ModelParameters:
        """Simulate secure aggregation (simplified implementation)"""
        if not client_updates:
            raise ValueError("No client updates provided")
        
        # In real secure aggregation, this would use cryptographic protocols
        # Here we simulate by adding small random masks that cancel out
        
        num_clients = len(client_updates)
        first_update = client_updates[0].model_update
        
        # Generate random masks for each client pair
        masks = {}
        for i in range(num_clients):
            masks[i] = {}
            for param_name, param_value in first_update.parameters.items():
                masks[i][param_name] = np.random.normal(0, 0.001, param_value.shape)
        
        # Apply masks (in practice, each client would only know their own masks)
        masked_updates = []
        for i, update in enumerate(client_updates):
            masked_params = {}
            for param_name, param_value in update.model_update.parameters.items():
                masked_params[param_name] = param_value + masks[i][param_name]
            
            masked_update = ModelParameters(
                parameters=masked_params,
                parameter_count=update.model_update.parameter_count
            )
            masked_updates.append(masked_update)
        
        # Server aggregates masked updates
        aggregated_params = {}
        for param_name in first_update.parameters:
            param_shape = first_update.parameters[param_name].shape
            aggregated_params[param_name] = np.zeros(param_shape)
        
        for masked_update in masked_updates:
            for param_name, param_value in masked_update.parameters.items():
                aggregated_params[param_name] += param_value
        
        # Average (masks should approximately cancel out)
        for param_name in aggregated_params:
            aggregated_params[param_name] /= num_clients
        
        return ModelParameters(
            parameters=aggregated_params,
            parameter_count=sum(param.size for param in aggregated_params.values()),
            metadata={'secure_aggregation': True}
        )

class FederatedLearningServer:
    """Main federated learning server coordinator"""
    
    def __init__(self, config: FederatedLearningConfig, model_trainer: FederatedModelTrainer):
        self.config = config
        self.model_trainer = model_trainer
        self.aggregator = ModelAggregator(config.aggregation_method)
        self.client_selector = ClientSelector(config.client_selection)
        
        self.registered_clients = {}
        self.global_model = None
        self.training_history = []
        self.current_round = 0
        
    async def register_client(self, client: FederatedClient):
        """Register a client with the server"""
        self.registered_clients[client.client_id] = client
        logger.info(f"Registered client {client.client_id} with {client.data_samples} samples")
    
    async def initialize_global_model(self, initial_model: ModelParameters):
        """Initialize the global model"""
        self.global_model = initial_model
        logger.info(f"Initialized global model with {initial_model.parameter_count} parameters")
    
    async def run_federated_training(self) -> List[FederatedRound]:
        """Run the complete federated training process"""
        if not self.global_model:
            raise ValueError("Global model not initialized")
        
        logger.info(f"Starting federated training for {self.config.total_rounds} rounds")
        
        for round_num in range(self.config.total_rounds):
            self.current_round = round_num
            
            # Run single round
            round_result = await self._run_single_round(round_num)
            self.training_history.append(round_result)
            
            # Check convergence
            if await self._check_convergence(round_result):
                logger.info(f"Converged after {round_num + 1} rounds")
                break
            
            # Log progress
            if round_num % 10 == 0:
                logger.info(f"Completed round {round_num + 1}/{self.config.total_rounds}")
        
        logger.info("Federated training completed")
        return self.training_history
    
    async def _run_single_round(self, round_number: int) -> FederatedRound:
        """Run a single round of federated learning"""
        round_start_time = datetime.now()
        
        # Select clients for this round
        available_clients = [c for c in self.registered_clients.values() if c.is_available]
        selected_client_ids = await self.client_selector.select_clients(
            available_clients, self.config.clients_per_round, round_number
        )
        
        federated_round = FederatedRound(
            round_number=round_number,
            selected_clients=selected_client_ids,
            global_model=self.global_model,
            start_time=round_start_time
        )
        
        # Collect client updates
        client_updates = []
        
        for client_id in selected_client_ids:
            try:
                # Client performs local training
                update = await self.model_trainer.local_train(
                    client_id, self.global_model, self.config.local_epochs
                )
                update.round_number = round_number
                
                # Apply privacy mechanisms if enabled
                if self.config.privacy_mechanism == PrivacyMechanism.DIFFERENTIAL_PRIVACY:
                    update.model_update = await PrivacyPreservingFL.apply_differential_privacy(
                        update.model_update, self.config.privacy_epsilon
                    )
                    update.privacy_budget_used = self.config.privacy_epsilon
                
                client_updates.append(update)
                
            except Exception as e:
                logger.error(f"Error in local training for client {client_id}: {e}")
        
        federated_round.client_updates = client_updates
        
        if client_updates:
            # Aggregate updates
            if self.config.privacy_mechanism == PrivacyMechanism.SECURE_AGGREGATION:
                aggregated_model = await PrivacyPreservingFL.secure_aggregation_simulation(client_updates)
            else:
                aggregated_model = await self.aggregator.aggregate_updates(client_updates, self.global_model)
            
            federated_round.aggregated_update = aggregated_model
            
            # Update global model
            self.global_model = aggregated_model
            
            # Calculate round metrics
            round_metrics = await self._calculate_round_metrics(client_updates)
            federated_round.round_metrics = round_metrics
        
        federated_round.end_time = datetime.now()
        
        return federated_round
    
    async def _calculate_round_metrics(self, client_updates: List[ClientUpdate]) -> Dict[str, float]:
        """Calculate metrics for the current round"""
        if not client_updates:
            return {}
        
        metrics = {
            'num_clients': len(client_updates),
            'avg_training_loss': np.mean([u.training_loss for u in client_updates]),
            'total_data_samples': sum(u.data_samples for u in client_updates),
            'avg_computation_time': np.mean([u.computation_time for u in client_updates]),
            'total_communication_cost': sum(u.communication_cost for u in client_updates)
        }
        
        # Add accuracy if available
        accuracies = [u.training_accuracy for u in client_updates if u.training_accuracy is not None]
        if accuracies:
            metrics['avg_training_accuracy'] = np.mean(accuracies)
        
        return metrics
    
    async def _check_convergence(self, current_round: FederatedRound) -> bool:
        """Check if training has converged"""
        if len(self.training_history) < 2:
            return False
        
        # Simple convergence check based on loss improvement
        prev_round = self.training_history[-2]
        
        if 'avg_training_loss' in current_round.round_metrics and 'avg_training_loss' in prev_round.round_metrics:
            loss_improvement = abs(
                prev_round.round_metrics['avg_training_loss'] - 
                current_round.round_metrics['avg_training_loss']
            )
            
            return loss_improvement < self.config.convergence_threshold
        
        return False
    
    async def evaluate_global_model(self, test_clients: List[str] = None) -> Dict[str, float]:
        """Evaluate the global model"""
        if not self.global_model:
            raise ValueError("No global model to evaluate")
        
        if test_clients:
            # Evaluate on specific clients
            client_results = []
            for client_id in test_clients:
                if client_id in self.registered_clients:
                    result = await self.model_trainer.evaluate_model(self.global_model, client_id)
                    client_results.append(result)
            
            # Average results across clients
            if client_results:
                avg_results = {}
                for key in client_results[0].keys():
                    avg_results[f'avg_{key}'] = np.mean([r[key] for r in client_results])
                return avg_results
        
        # Global evaluation (would use global test set in practice)
        return await self.model_trainer.evaluate_model(self.global_model)
    
    def get_training_statistics(self) -> Dict[str, Any]:
        """Get comprehensive training statistics"""
        if not self.training_history:
            return {}
        
        total_rounds = len(self.training_history)
        total_clients = len(self.registered_clients)
        
        # Calculate overall metrics
        all_losses = []
        all_accuracies = []
        
        for round_info in self.training_history:
            if 'avg_training_loss' in round_info.round_metrics:
                all_losses.append(round_info.round_metrics['avg_training_loss'])
            if 'avg_training_accuracy' in round_info.round_metrics:
                all_accuracies.append(round_info.round_metrics['avg_training_accuracy'])
        
        stats = {
            'total_rounds_completed': total_rounds,
            'total_registered_clients': total_clients,
            'algorithm_used': self.config.algorithm.value,
            'aggregation_method': self.config.aggregation_method.value,
            'privacy_mechanism': self.config.privacy_mechanism.value
        }
        
        if all_losses:
            stats.update({
                'final_avg_loss': all_losses[-1],
                'initial_avg_loss': all_losses[0],
                'loss_improvement': all_losses[0] - all_losses[-1],
                'min_loss_achieved': min(all_losses)
            })
        
        if all_accuracies:
            stats.update({
                'final_avg_accuracy': all_accuracies[-1],
                'max_accuracy_achieved': max(all_accuracies)
            })
        
        return stats

# Factory functions
async def create_federated_server(config: FederatedLearningConfig, 
                                model_trainer: FederatedModelTrainer) -> FederatedLearningServer:
    """Factory function to create federated learning server"""
    return FederatedLearningServer(config, model_trainer)

async def create_linear_trainer(feature_dim: int, num_classes: int = 1) -> LinearModelTrainer:
    """Factory function to create linear model trainer"""
    return LinearModelTrainer(feature_dim, num_classes)

# Example usage
async def main():
    """Example usage of federated learning system"""
    
    # Configuration
    config = FederatedLearningConfig(
        algorithm=FederatedAlgorithm.FEDERATED_AVERAGING,
        aggregation_method=AggregationMethod.WEIGHTED_AVERAGE,
        client_selection=ClientSelectionStrategy.RANDOM_SELECTION,
        privacy_mechanism=PrivacyMechanism.DIFFERENTIAL_PRIVACY,
        total_rounds=50,
        clients_per_round=3,
        local_epochs=5,
        learning_rate=0.01,
        privacy_epsilon=1.0
    )
    
    # Create model trainer
    trainer = await create_linear_trainer(feature_dim=10, num_classes=2)  # Binary classification
    
    # Create server
    server = await create_federated_server(config, trainer)
    
    # Create and register clients with simulated data
    clients = []
    for i in range(5):
        client = FederatedClient(
            client_id=f"client_{i}",
            data_samples=1000,
            model_architecture={'type': 'linear', 'features': 10, 'classes': 2},
            privacy_budget=10.0,
            compute_capacity=1.0,
            network_bandwidth=1.0
        )
        clients.append(client)
        
        # Create synthetic training data for each client
        X = np.random.randn(1000, 10)  # 1000 samples, 10 features
        y = (X @ np.random.randn(10) + np.random.randn(1000) * 0.1 > 0).astype(int)  # Binary labels
        
        await trainer.initialize_client_data(client.client_id, X, y)
        await server.register_client(client)
    
    # Initialize global model
    initial_model = ModelParameters(
        parameters={
            'weights': np.random.normal(0, 0.01, (10, 2)),
            'bias': np.zeros(2)
        },
        parameter_count=22
    )
    await server.initialize_global_model(initial_model)
    
    # Run federated training
    training_history = await server.run_federated_training()
    
    # Evaluate final model
    evaluation_results = await server.evaluate_global_model()
    
    # Get training statistics
    stats = server.get_training_statistics()
    
    print(f"Federated Learning Results:")
    print(f"  Rounds completed: {stats['total_rounds_completed']}")
    print(f"  Final loss: {stats.get('final_avg_loss', 'N/A'):.4f}")
    print(f"  Loss improvement: {stats.get('loss_improvement', 'N/A'):.4f}")
    print(f"  Privacy mechanism: {stats['privacy_mechanism']}")
    print(f"  Final evaluation: {evaluation_results}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())