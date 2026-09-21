"""
Custom LORA training interface for creating specialized AI model adapters.
Supports training LORA adapters for image generation, text generation, and other AI models.
"""

import os
import json
import asyncio
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ...database import get_session
from ...database.models import LORATraining, LORATrainingStatus, TrainingDataset, ModelType
from ...settings import settings
from ..compute.optimizer import ComputeOptimizer
from ..cost.estimator import CostEstimator
from ...exceptions import LORATrainingError


class LoraType(Enum):
    STABLE_DIFFUSION_XL = "sdxl"
    STABLE_DIFFUSION_1_5 = "sd15"
    FLUX_DEV = "flux_dev"
    FLUX_SCHNELL = "flux_schnell"
    DREAMBOOTH_SD = "dreambooth_sd"
    TEXTUAL_INVERSION = "textual_inversion"
    CONTROLNET = "controlnet"
    LLM_LORA = "llm_lora"


class TrainingTechnique(Enum):
    LORA = "lora"
    LYCORIS = "lycoris"
    DREAMBOOTH = "dreambooth"
    TEXTUAL_INVERSION = "textual_inversion"
    FULL_FINETUNE = "full_finetune"


class DatasetType(Enum):
    CONCEPT = "concept"          # Person, object, style
    STYLE = "style"              # Art style, photography style
    CHARACTER = "character"      # Fictional character, mascot
    PRODUCT = "product"          # Commercial product
    POSE = "pose"                # Specific poses/positions
    BACKGROUND = "background"    # Environments, scenes
    CLOTHING = "clothing"        # Fashion, outfits
    TEXT_INSTRUCTION = "text_instruction"  # For LLM training


@dataclass
class TrainingConfig:
    lora_type: LoraType
    technique: TrainingTechnique = TrainingTechnique.LORA
    learning_rate: float = 1e-4
    batch_size: int = 1
    num_epochs: int = 10
    gradient_accumulation_steps: int = 4
    mixed_precision: str = "fp16"
    optimizer: str = "adamw"
    lr_scheduler: str = "cosine"
    warmup_steps: int = 100
    max_train_steps: Optional[int] = None
    save_every_n_epochs: int = 1
    resolution: int = 512
    enable_xformers: bool = True
    gradient_checkpointing: bool = True
    prior_loss_weight: float = 1.0
    seed: Optional[int] = None
    network_dim: int = 128        # LORA rank
    network_alpha: int = 64       # LORA alpha
    clip_skip: int = 2
    noise_offset: float = 0.0
    adaptive_noise_scale: float = 0.0
    multires_noise_discount: float = 0.0
    multires_noise_iterations: int = 0
    min_snr_gamma: Optional[float] = None


@dataclass
class TrainingDatasetConfig:
    name: str
    dataset_type: DatasetType
    concept_token: str
    class_token: str
    num_images: int
    flip_aug: bool = False
    color_aug: bool = False
    face_crop_aug_range: Optional[str] = None
    num_repeats: int = 1
    keep_tokens: int = 0


class LORATrainer:
    def __init__(self):
        self.compute_optimizer = ComputeOptimizer()
        self.cost_estimator = CostEstimator()
        self.supported_base_models = {
            LoraType.STABLE_DIFFUSION_XL: [
                "stabilityai/stable-diffusion-xl-base-1.0",
                "stabilityai/stable-diffusion-xl-refiner-1.0"
            ],
            LoraType.STABLE_DIFFUSION_1_5: [
                "runwayml/stable-diffusion-v1-5",
                "stablediffusionapi/realistic-vision-v5"
            ],
            LoraType.FLUX_DEV: [
                "black-forest-labs/FLUX.1-dev"
            ],
            LoraType.FLUX_SCHNELL: [
                "black-forest-labs/FLUX.1-schnell"
            ],
            LoraType.LLM_LORA: [
                "meta-llama/Llama-2-7b-hf",
                "meta-llama/Llama-2-13b-hf",
                "microsoft/DialoGPT-medium"
            ]
        }
    
    async def create_training_job(
        self,
        user_id: str,
        dataset_path: str,
        config: TrainingConfig,
        dataset_config: TrainingDatasetConfig,
        base_model: Optional[str] = None,
        output_name: Optional[str] = None
    ) -> str:
        """Create a new LORA training job."""
        
        # Validate inputs
        await self._validate_training_request(config, dataset_config, dataset_path)
        
        # Auto-select base model if not specified
        if not base_model:
            base_model = self.supported_base_models[config.lora_type][0]
        
        # Estimate cost and time
        cost_estimate = await self._estimate_training_cost(config, dataset_config)
        time_estimate = await self._estimate_training_time(config, dataset_config)
        
        # Create training record
        async with get_session() as session:
            # Create dataset record
            dataset = TrainingDataset(
                name=dataset_config.name,
                dataset_type=dataset_config.dataset_type.value,
                concept_token=dataset_config.concept_token,
                class_token=dataset_config.class_token,
                num_images=dataset_config.num_images,
                dataset_path=dataset_path,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            session.add(dataset)
            await session.flush()
            
            # Create training record
            training = LORATraining(
                user_id=user_id,
                dataset_id=dataset.id,
                lora_type=config.lora_type.value,
                technique=config.technique.value,
                base_model=base_model,
                output_name=output_name or f"{dataset_config.name}_lora",
                config=self._config_to_dict(config),
                status=LORATrainingStatus.QUEUED,
                estimated_cost_cc=cost_estimate,
                estimated_duration_minutes=time_estimate,
                created_at=datetime.utcnow()
            )
            
            session.add(training)
            await session.commit()
            await session.refresh(training)
            
            return training.id
    
    async def start_training(self, training_id: str) -> Dict[str, Any]:
        """Start a LORA training job."""
        async with get_session() as session:
            result = await session.execute(
                select(LORATraining, TrainingDataset)
                .join(TrainingDataset)
                .where(LORATraining.id == training_id)
            )
            row = result.first()
            
            if not row:
                raise LORATrainingError(f"Training job {training_id} not found")
            
            training, dataset = row
            
            if training.status != LORATrainingStatus.QUEUED:
                raise LORATrainingError(f"Training job {training_id} is not queued")
            
            # Update status
            training.status = LORATrainingStatus.PREPARING
            training.started_at = datetime.utcnow()
            await session.commit()
            
            # Start training process
            training_task = asyncio.create_task(
                self._run_training_process(training, dataset)
            )
            
            return {
                "training_id": training_id,
                "status": "started",
                "estimated_completion": training.started_at + timedelta(minutes=training.estimated_duration_minutes)
            }
    
    async def get_training_status(self, training_id: str) -> Dict[str, Any]:
        """Get the current status of a training job."""
        async with get_session() as session:
            result = await session.execute(
                select(LORATraining, TrainingDataset)
                .join(TrainingDataset)
                .where(LORATraining.id == training_id)
            )
            row = result.first()
            
            if not row:
                raise LORATrainingError(f"Training job {training_id} not found")
            
            training, dataset = row
            
            return {
                "id": training.id,
                "status": training.status.value,
                "progress": training.progress,
                "current_epoch": training.current_epoch,
                "total_epochs": training.config.get("num_epochs", 0),
                "current_step": training.current_step,
                "total_steps": training.total_steps,
                "loss": training.current_loss,
                "learning_rate": training.current_lr,
                "estimated_cost_cc": training.estimated_cost_cc,
                "actual_cost_cc": training.actual_cost_cc,
                "started_at": training.started_at,
                "completed_at": training.completed_at,
                "model_path": training.output_path,
                "preview_images": training.preview_images or [],
                "error_message": training.error_message
            }
    
    async def cancel_training(self, training_id: str, user_id: str) -> bool:
        """Cancel a running training job."""
        async with get_session() as session:
            result = await session.execute(
                select(LORATraining)
                .where(LORATraining.id == training_id)
                .where(LORATraining.user_id == user_id)
            )
            training = result.scalar_one_or_none()
            
            if not training:
                return False
            
            if training.status in [LORATrainingStatus.COMPLETED, LORATrainingStatus.FAILED]:
                return False
            
            training.status = LORATrainingStatus.CANCELLED
            training.completed_at = datetime.utcnow()
            await session.commit()
            
            return True
    
    async def _validate_training_request(
        self,
        config: TrainingConfig,
        dataset_config: TrainingDatasetConfig,
        dataset_path: str
    ):
        """Validate the training request parameters."""
        
        # Check if dataset path exists and is accessible
        if not os.path.exists(dataset_path):
            raise LORATrainingError(f"Dataset path does not exist: {dataset_path}")
        
        # Validate image count
        if dataset_config.num_images < 3:
            raise LORATrainingError("Dataset must contain at least 3 images")
        
        if dataset_config.num_images > 1000:
            raise LORATrainingError("Dataset cannot contain more than 1000 images")
        
        # Validate config parameters
        if config.learning_rate <= 0 or config.learning_rate > 1:
            raise LORATrainingError("Learning rate must be between 0 and 1")
        
        if config.batch_size < 1 or config.batch_size > 8:
            raise LORATrainingError("Batch size must be between 1 and 8")
        
        if config.num_epochs < 1 or config.num_epochs > 100:
            raise LORATrainingError("Number of epochs must be between 1 and 100")
        
        if config.network_dim < 16 or config.network_dim > 1024:
            raise LORATrainingError("Network dimension must be between 16 and 1024")
        
        # Validate concept and class tokens
        if not dataset_config.concept_token.strip():
            raise LORATrainingError("Concept token cannot be empty")
        
        if not dataset_config.class_token.strip():
            raise LORATrainingError("Class token cannot be empty")
    
    async def _estimate_training_cost(
        self,
        config: TrainingConfig,
        dataset_config: TrainingDatasetConfig
    ) -> Decimal:
        """Estimate the cost of training."""
        
        # Base cost calculation
        base_cost_per_hour = Decimal("0.50")  # Base GPU cost per hour
        
        # Adjust based on model complexity
        if config.lora_type in [LoraType.STABLE_DIFFUSION_XL, LoraType.FLUX_DEV]:
            base_cost_per_hour *= Decimal("2.0")
        elif config.lora_type == LoraType.LLM_LORA:
            base_cost_per_hour *= Decimal("1.5")
        
        # Calculate estimated hours
        steps_per_epoch = dataset_config.num_images * dataset_config.num_repeats // config.batch_size
        total_steps = steps_per_epoch * config.num_epochs
        
        # Estimate time based on steps (rough approximation)
        estimated_hours = max(0.5, total_steps / 1000)  # 1000 steps per hour baseline
        
        # Adjust for resolution
        if config.resolution >= 1024:
            estimated_hours *= 1.5
        
        total_cost = base_cost_per_hour * Decimal(str(estimated_hours))
        
        # Convert to CC
        return total_cost / settings.compute_credits.cc_to_usd_rate
    
    async def _estimate_training_time(
        self,
        config: TrainingConfig,
        dataset_config: TrainingDatasetConfig
    ) -> int:
        """Estimate training time in minutes."""
        
        steps_per_epoch = dataset_config.num_images * dataset_config.num_repeats // config.batch_size
        total_steps = steps_per_epoch * config.num_epochs
        
        # Base time per step (seconds)
        base_time_per_step = 2.0
        
        # Adjust for model complexity
        if config.lora_type in [LoraType.STABLE_DIFFUSION_XL, LoraType.FLUX_DEV]:
            base_time_per_step *= 3.0
        elif config.lora_type == LoraType.LLM_LORA:
            base_time_per_step *= 2.0
        
        # Adjust for resolution
        if config.resolution >= 1024:
            base_time_per_step *= 2.0
        
        # Adjust for batch size
        base_time_per_step *= config.batch_size
        
        total_minutes = max(30, (total_steps * base_time_per_step) / 60)
        
        return int(total_minutes)
    
    async def _run_training_process(
        self,
        training: LORATraining,
        dataset: TrainingDataset
    ):
        """Run the actual training process."""
        try:
            # Update status to training
            async with get_session() as session:
                training.status = LORATrainingStatus.TRAINING
                await session.commit()
            
            # Get compute recommendation
            compute_rec = await self.compute_optimizer.optimize_for_operation(
                "lora_training",
                {"lora_type": training.lora_type, "config": training.config}
            )
            
            if compute_rec["use_local"]:
                result = await self._train_local(training, dataset)
            else:
                result = await self._train_cloud(training, dataset)
            
            # Update completion
            async with get_session() as session:
                training.status = LORATrainingStatus.COMPLETED
                training.completed_at = datetime.utcnow()
                training.output_path = result["model_path"]
                training.actual_cost_cc = result["actual_cost_cc"]
                training.progress = 100
                await session.commit()
            
        except Exception as e:
            # Update failure
            async with get_session() as session:
                training.status = LORATrainingStatus.FAILED
                training.error_message = str(e)
                training.completed_at = datetime.utcnow()
                await session.commit()
    
    async def _train_local(
        self,
        training: LORATraining,
        dataset: TrainingDataset
    ) -> Dict[str, Any]:
        """Train LORA locally using available GPU."""
        
        if training.lora_type in [
            LoraType.STABLE_DIFFUSION_XL.value,
            LoraType.STABLE_DIFFUSION_1_5.value
        ]:
            return await self._train_stable_diffusion_lora(training, dataset)
        elif training.lora_type == LoraType.LLM_LORA.value:
            return await self._train_llm_lora(training, dataset)
        else:
            raise LORATrainingError(f"Local training not supported for {training.lora_type}")
    
    async def _train_stable_diffusion_lora(
        self,
        training: LORATraining,
        dataset: TrainingDataset
    ) -> Dict[str, Any]:
        """Train Stable Diffusion LORA using local GPU."""
        try:
            import subprocess
            import tempfile
            
            # Create temporary directory for training
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = os.path.join(temp_dir, "output")
                os.makedirs(output_dir, exist_ok=True)
                
                # Prepare training script arguments
                config = training.config
                script_args = [
                    "python", "-m", "diffusers.examples.dreambooth.train_dreambooth_lora",
                    f"--pretrained_model_name_or_path={training.base_model}",
                    f"--instance_data_dir={dataset.dataset_path}",
                    f"--output_dir={output_dir}",
                    f"--instance_prompt={dataset.concept_token} {dataset.class_token}",
                    f"--resolution={config.get('resolution', 512)}",
                    f"--train_batch_size={config.get('batch_size', 1)}",
                    f"--gradient_accumulation_steps={config.get('gradient_accumulation_steps', 4)}",
                    f"--learning_rate={config.get('learning_rate', 1e-4)}",
                    f"--lr_scheduler={config.get('lr_scheduler', 'cosine')}",
                    f"--lr_warmup_steps={config.get('warmup_steps', 100)}",
                    f"--num_train_epochs={config.get('num_epochs', 10)}",
                    f"--rank={config.get('network_dim', 128)}",
                    "--use_8bit_adam",
                    "--mixed_precision=fp16",
                    "--enable_xformers_memory_efficient_attention",
                    "--gradient_checkpointing"
                ]
                
                if config.get('seed'):
                    script_args.append(f"--seed={config['seed']}")
                
                # Run training
                process = await asyncio.create_subprocess_exec(
                    *script_args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=temp_dir
                )
                
                # Monitor progress
                while True:
                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(), timeout=1.0
                        )
                        break
                    except asyncio.TimeoutError:
                        # Update progress periodically
                        await self._update_training_progress(training.id)
                        continue
                
                if process.returncode != 0:
                    raise LORATrainingError(f"Training failed: {stderr.decode()}")
                
                # Find and move output files
                lora_files = [f for f in os.listdir(output_dir) if f.endswith('.safetensors')]
                if not lora_files:
                    raise LORATrainingError("No LORA files generated")
                
                # Move to permanent storage
                final_path = f"/storage/lora_models/{training.id}/{lora_files[0]}"
                os.makedirs(os.path.dirname(final_path), exist_ok=True)
                os.rename(os.path.join(output_dir, lora_files[0]), final_path)
                
                return {
                    "model_path": final_path,
                    "actual_cost_cc": training.estimated_cost_cc
                }
                
        except Exception as e:
            raise LORATrainingError(f"Local SD LORA training failed: {str(e)}")
    
    async def _train_llm_lora(
        self,
        training: LORATraining,
        dataset: TrainingDataset
    ) -> Dict[str, Any]:
        """Train LLM LORA using local resources."""
        try:
            import subprocess
            import tempfile
            
            # This would use libraries like PEFT (Parameter Efficient Fine-Tuning)
            # For now, return a placeholder
            
            final_path = f"/storage/lora_models/{training.id}/adapter_model.bin"
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            # Placeholder file creation
            with open(final_path, 'w') as f:
                f.write("# LLM LORA adapter placeholder\n")
            
            return {
                "model_path": final_path,
                "actual_cost_cc": training.estimated_cost_cc
            }
            
        except Exception as e:
            raise LORATrainingError(f"Local LLM LORA training failed: {str(e)}")
    
    async def _train_cloud(
        self,
        training: LORATraining,
        dataset: TrainingDataset
    ) -> Dict[str, Any]:
        """Train LORA using cloud services."""
        # This would integrate with cloud training services like:
        # - RunPod
        # - Vast.ai
        # - Lambda Labs
        # - AWS SageMaker
        
        # Placeholder implementation
        final_path = f"https://cloud-storage.example.com/lora_models/{training.id}/model.safetensors"
        
        return {
            "model_path": final_path,
            "actual_cost_cc": training.estimated_cost_cc * Decimal("1.2")  # Cloud markup
        }
    
    async def _update_training_progress(self, training_id: str):
        """Update training progress in database."""
        async with get_session() as session:
            # This would parse logs and update progress
            # For now, just increment progress
            result = await session.execute(
                select(LORATraining).where(LORATraining.id == training_id)
            )
            training = result.scalar_one_or_none()
            
            if training and training.status == LORATrainingStatus.TRAINING:
                # Simple progress increment
                training.progress = min(95, training.progress + 5)
                await session.commit()
    
    def _config_to_dict(self, config: TrainingConfig) -> Dict[str, Any]:
        """Convert TrainingConfig to dictionary for storage."""
        return {
            "lora_type": config.lora_type.value,
            "technique": config.technique.value,
            "learning_rate": config.learning_rate,
            "batch_size": config.batch_size,
            "num_epochs": config.num_epochs,
            "gradient_accumulation_steps": config.gradient_accumulation_steps,
            "mixed_precision": config.mixed_precision,
            "optimizer": config.optimizer,
            "lr_scheduler": config.lr_scheduler,
            "warmup_steps": config.warmup_steps,
            "max_train_steps": config.max_train_steps,
            "save_every_n_epochs": config.save_every_n_epochs,
            "resolution": config.resolution,
            "enable_xformers": config.enable_xformers,
            "gradient_checkpointing": config.gradient_checkpointing,
            "prior_loss_weight": config.prior_loss_weight,
            "seed": config.seed,
            "network_dim": config.network_dim,
            "network_alpha": config.network_alpha,
            "clip_skip": config.clip_skip,
            "noise_offset": config.noise_offset,
            "adaptive_noise_scale": config.adaptive_noise_scale,
            "multires_noise_discount": config.multires_noise_discount,
            "multires_noise_iterations": config.multires_noise_iterations,
            "min_snr_gamma": config.min_snr_gamma
        }
    
    async def get_user_models(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all LORA models created by a user."""
        async with get_session() as session:
            result = await session.execute(
                select(LORATraining, TrainingDataset)
                .join(TrainingDataset)
                .where(LORATraining.user_id == user_id)
                .where(LORATraining.status == LORATrainingStatus.COMPLETED)
                .order_by(LORATraining.completed_at.desc())
            )
            
            models = []
            for training, dataset in result:
                models.append({
                    "id": training.id,
                    "name": training.output_name,
                    "lora_type": training.lora_type,
                    "technique": training.technique,
                    "base_model": training.base_model,
                    "dataset_name": dataset.name,
                    "concept_token": dataset.concept_token,
                    "model_path": training.output_path,
                    "cost_cc": training.actual_cost_cc,
                    "created_at": training.created_at,
                    "completed_at": training.completed_at
                })
            
            return models
    
    async def download_model(self, training_id: str, user_id: str) -> str:
        """Get download URL for a trained model."""
        async with get_session() as session:
            result = await session.execute(
                select(LORATraining)
                .where(LORATraining.id == training_id)
                .where(LORATraining.user_id == user_id)
                .where(LORATraining.status == LORATrainingStatus.COMPLETED)
            )
            training = result.scalar_one_or_none()
            
            if not training:
                raise LORATrainingError("Model not found or not accessible")
            
            return training.output_path
    
    async def get_training_templates(self) -> List[Dict[str, Any]]:
        """Get predefined training configuration templates."""
        return [
            {
                "name": "Portrait Style",
                "description": "Train a LORA for portrait photography style",
                "config": {
                    "lora_type": "sdxl",
                    "technique": "lora",
                    "learning_rate": 1e-4,
                    "num_epochs": 15,
                    "batch_size": 1,
                    "resolution": 1024,
                    "network_dim": 64,
                    "network_alpha": 32
                },
                "dataset_requirements": {
                    "min_images": 10,
                    "max_images": 50,
                    "recommended_concept": "portrait of [person]",
                    "recommended_class": "portrait"
                }
            },
            {
                "name": "Art Style",
                "description": "Train a LORA to replicate an artistic style",
                "config": {
                    "lora_type": "sdxl",
                    "technique": "lora",
                    "learning_rate": 8e-5,
                    "num_epochs": 20,
                    "batch_size": 2,
                    "resolution": 1024,
                    "network_dim": 128,
                    "network_alpha": 64
                },
                "dataset_requirements": {
                    "min_images": 15,
                    "max_images": 100,
                    "recommended_concept": "in the style of [artist]",
                    "recommended_class": "artwork"
                }
            },
            {
                "name": "Character",
                "description": "Train a LORA for a specific character or person",
                "config": {
                    "lora_type": "sdxl",
                    "technique": "dreambooth",
                    "learning_rate": 5e-6,
                    "num_epochs": 25,
                    "batch_size": 1,
                    "resolution": 1024,
                    "network_dim": 128,
                    "network_alpha": 64,
                    "prior_loss_weight": 1.0
                },
                "dataset_requirements": {
                    "min_images": 8,
                    "max_images": 30,
                    "recommended_concept": "[character name]",
                    "recommended_class": "person"
                }
            }
        ]


# Global instance
lora_trainer = LORATrainer()