#!/usr/bin/env python3
"""
ActiveLog Jetson AI Agent
Specialized agent for AI inference at the edge with CUDA acceleration
"""

import asyncio
import json
import logging
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

import psutil
import requests
import numpy as np
from collections import deque

# Add the virtual environment to Python path
venv_path = Path.home() / "activelog-ai-venv" / "lib" / "python3.11" / "site-packages"
if venv_path.exists():
    sys.path.insert(0, str(venv_path))

try:
    import torch
    import torchvision.transforms as transforms
    import cv2
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit
    from ultralytics import YOLO
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some AI dependencies not available: {e}")
    TORCH_AVAILABLE = False

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

class ModelManager:
    """Manages AI models with optimization and caching"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.models = {}
        self.model_cache = {}
        self.cache_size = config.get("ai", {}).get("model_cache_size", 2048)
        self.max_models = config.get("ai", {}).get("max_models_loaded", 5)
        self.models_dir = Path(config.get("models", {}).get("model_dir", "/var/lib/activelog/models"))
        self.cache_dir = Path(config.get("models", {}).get("cache_dir", "/var/lib/activelog/cache"))
        
        # Performance tracking
        self.inference_times = deque(maxlen=100)
        self.memory_usage = deque(maxlen=100)
        
        self.logger = logging.getLogger(__name__)

    async def load_model(self, model_name: str, model_type: str, model_path: str) -> bool:
        """Load a model with automatic optimization"""
        try:
            if model_name in self.models:
                self.logger.info(f"Model {model_name} already loaded")
                return True
            
            # Check if we need to free memory
            if len(self.models) >= self.max_models:
                await self.unload_least_used_model()
            
            self.logger.info(f"Loading model {model_name} of type {model_type}")
            
            # Load model based on type
            if model_type == "pytorch":
                model = await self._load_pytorch_model(model_path)
            elif model_type == "tensorflow":
                model = await self._load_tensorflow_model(model_path)
            elif model_type == "tensorrt":
                model = await self._load_tensorrt_model(model_path)
            elif model_type == "onnx":
                model = await self._load_onnx_model(model_path)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            if model:
                self.models[model_name] = {
                    "model": model,
                    "type": model_type,
                    "path": model_path,
                    "loaded_at": time.time(),
                    "usage_count": 0,
                    "last_used": time.time()
                }
                
                self.logger.info(f"Successfully loaded model {model_name}")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            return False

    async def _load_pytorch_model(self, model_path: str):
        """Load PyTorch model with CUDA optimization"""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")
        
        # Load model
        model = torch.load(model_path, map_location='cuda' if torch.cuda.is_available() else 'cpu')
        
        if hasattr(model, 'eval'):
            model.eval()
        
        # Optimize with TorchScript if possible
        if hasattr(model, 'forward') and torch.cuda.is_available():
            try:
                # Create example input for tracing
                example_input = torch.randn(1, 3, 224, 224).cuda()
                traced_model = torch.jit.trace(model, example_input)
                traced_model.eval()
                return traced_model
            except:
                self.logger.warning("Failed to create TorchScript model, using standard model")
                return model
        
        return model

    async def _load_tensorflow_model(self, model_path: str):
        """Load TensorFlow model with GPU optimization"""
        if not TF_AVAILABLE:
            raise RuntimeError("TensorFlow not available")
        
        # Configure GPU memory growth
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError:
                pass
        
        # Load model
        model = tf.keras.models.load_model(model_path)
        return model

    async def _load_tensorrt_model(self, model_path: str):
        """Load TensorRT optimized model"""
        try:
            # Load TensorRT engine
            with open(model_path, 'rb') as f:
                engine_data = f.read()
            
            logger = trt.Logger(trt.Logger.WARNING)
            runtime = trt.Runtime(logger)
            engine = runtime.deserialize_cuda_engine(engine_data)
            
            # Create execution context
            context = engine.create_execution_context()
            
            return {
                "engine": engine,
                "context": context,
                "logger": logger
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load TensorRT model: {e}")
            raise

    async def _load_onnx_model(self, model_path: str):
        """Load ONNX model with optimization"""
        try:
            import onnxruntime as ort
            
            # Create session with GPU provider
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            session = ort.InferenceSession(model_path, providers=providers)
            
            return session
            
        except ImportError:
            self.logger.error("ONNX Runtime not available")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load ONNX model: {e}")
            raise

    async def predict(self, model_name: str, input_data: Any, **kwargs) -> Dict:
        """Run inference on a loaded model"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not loaded")
        
        model_info = self.models[model_name]
        model = model_info["model"]
        model_type = model_info["type"]
        
        # Update usage statistics
        model_info["usage_count"] += 1
        model_info["last_used"] = time.time()
        
        start_time = time.time()
        
        try:
            # Run inference based on model type
            if model_type == "pytorch":
                result = await self._predict_pytorch(model, input_data, **kwargs)
            elif model_type == "tensorflow":
                result = await self._predict_tensorflow(model, input_data, **kwargs)
            elif model_type == "tensorrt":
                result = await self._predict_tensorrt(model, input_data, **kwargs)
            elif model_type == "onnx":
                result = await self._predict_onnx(model, input_data, **kwargs)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            
            # Monitor GPU memory
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.memory_allocated() / 1024**2  # MB
                self.memory_usage.append(gpu_memory)
            
            return {
                "result": result,
                "inference_time": inference_time,
                "model_name": model_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Inference failed for model {model_name}: {e}")
            raise

    async def _predict_pytorch(self, model, input_data, **kwargs):
        """PyTorch inference"""
        with torch.no_grad():
            if isinstance(input_data, np.ndarray):
                tensor = torch.from_numpy(input_data).float()
            else:
                tensor = input_data
            
            if torch.cuda.is_available():
                tensor = tensor.cuda()
                if hasattr(model, 'cuda'):
                    model = model.cuda()
            
            output = model(tensor)
            
            if isinstance(output, torch.Tensor):
                return output.cpu().numpy().tolist()
            else:
                return [o.cpu().numpy().tolist() if isinstance(o, torch.Tensor) else o for o in output]

    async def _predict_tensorflow(self, model, input_data, **kwargs):
        """TensorFlow inference"""
        if isinstance(input_data, list):
            input_data = np.array(input_data)
        
        with tf.device('/GPU:0' if tf.test.is_gpu_available() else '/CPU:0'):
            output = model(input_data)
            
            if isinstance(output, tf.Tensor):
                return output.numpy().tolist()
            else:
                return [o.numpy().tolist() if isinstance(o, tf.Tensor) else o for o in output]

    async def _predict_tensorrt(self, model_dict, input_data, **kwargs):
        """TensorRT inference"""
        engine = model_dict["engine"]
        context = model_dict["context"]
        
        # Allocate GPU memory
        inputs = []
        outputs = []
        bindings = []
        
        for binding in engine:
            size = trt.volume(engine.get_binding_shape(binding)) * engine.max_batch_size
            dtype = trt.nptype(engine.get_binding_dtype(binding))
            
            # Allocate host and device buffers
            host_mem = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            
            bindings.append(int(device_mem))
            
            if engine.binding_is_input(binding):
                inputs.append({'host': host_mem, 'device': device_mem})
            else:
                outputs.append({'host': host_mem, 'device': device_mem})
        
        # Copy input data to GPU
        inputs[0]['host'][:] = input_data.flatten()
        cuda.memcpy_htod(inputs[0]['device'], inputs[0]['host'])
        
        # Run inference
        context.execute(bindings=bindings)
        
        # Copy output back to CPU
        cuda.memcpy_dtoh(outputs[0]['host'], outputs[0]['device'])
        
        return outputs[0]['host'].tolist()

    async def _predict_onnx(self, session, input_data, **kwargs):
        """ONNX Runtime inference"""
        input_name = session.get_inputs()[0].name
        
        if isinstance(input_data, list):
            input_data = np.array(input_data, dtype=np.float32)
        
        result = session.run(None, {input_name: input_data})
        return [r.tolist() if isinstance(r, np.ndarray) else r for r in result]

    async def unload_model(self, model_name: str):
        """Unload a specific model"""
        if model_name in self.models:
            del self.models[model_name]
            
            # Clear GPU cache if using PyTorch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info(f"Unloaded model {model_name}")

    async def unload_least_used_model(self):
        """Unload the least recently used model"""
        if not self.models:
            return
        
        # Find least recently used model
        oldest_model = min(self.models.items(), key=lambda x: x[1]["last_used"])
        await self.unload_model(oldest_model[0])

    def get_model_stats(self) -> Dict:
        """Get model performance statistics"""
        return {
            "loaded_models": len(self.models),
            "model_details": {
                name: {
                    "type": info["type"],
                    "usage_count": info["usage_count"],
                    "last_used": info["last_used"],
                    "loaded_at": info["loaded_at"]
                }
                for name, info in self.models.items()
            },
            "avg_inference_time": np.mean(self.inference_times) if self.inference_times else 0,
            "avg_gpu_memory": np.mean(self.memory_usage) if self.memory_usage else 0,
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate model cache hit rate"""
        total_requests = sum(info["usage_count"] for info in self.models.values())
        if total_requests == 0:
            return 0.0
        
        # Simplified cache hit calculation
        cache_hits = total_requests - len(self.models)
        return max(0.0, cache_hits / total_requests)


class JetsonAIAgent:
    """Main AI agent for Jetson devices"""
    
    def __init__(self, config_path: str = "/etc/activelog/edge.conf"):
        self.config_path = config_path
        self.config = self.load_config()
        self.device_id = self.config.get("device", {}).get("id")
        self.running = False
        
        # Initialize logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.model_manager = ModelManager(self.config)
        self.performance_monitor = PerformanceMonitor()
        self.camera = None
        
        # Inference queue for batching
        self.inference_queue = asyncio.Queue()
        self.batch_processor = None
        
        self.logger.info(f"JetsonAIAgent initialized for device {self.device_id}")

    def load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = {}
                current_section = None
                
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                        config[current_section] = {}
                    elif '=' in line and current_section:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Convert boolean and numeric values
                        if value.lower() in ('true', 'false'):
                            value = value.lower() == 'true'
                        elif value.isdigit():
                            value = int(value)
                        elif value.replace('.', '').isdigit():
                            value = float(value)
                        
                        config[current_section][key] = value
                
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}

    def setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO"))
        log_file = log_config.get("file_path", "/var/log/activelog/jetson-edge.log")
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    async def start(self):
        """Start the Jetson AI agent"""
        self.logger.info("Starting ActiveLog Jetson AI Agent")
        self.running = True
        
        try:
            # Initialize hardware
            await self.initialize_hardware()
            
            # Load default models
            await self.load_default_models()
            
            # Start batch processor
            self.batch_processor = asyncio.create_task(self.batch_inference_loop())
            
            # Start monitoring tasks
            tasks = [
                asyncio.create_task(self.performance_monitor_loop()),
                asyncio.create_task(self.thermal_monitor_loop()),
                asyncio.create_task(self.model_optimization_loop()),
                asyncio.create_task(self.health_check_loop())
            ]
            
            self.logger.info("Jetson AI agent started successfully")
            
            # Wait for shutdown
            await self.wait_for_shutdown()
            
        except Exception as e:
            self.logger.error(f"Error starting Jetson AI agent: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the Jetson AI agent"""
        self.logger.info("Stopping Jetson AI Agent")
        self.running = False
        
        if self.batch_processor:
            self.batch_processor.cancel()
        
        if self.camera:
            self.camera.release()
        
        self.logger.info("Jetson AI agent stopped")

    async def initialize_hardware(self):
        """Initialize Jetson hardware"""
        # Initialize camera if enabled
        ai_config = self.config.get("ai", {})
        if ai_config.get("enable_camera", True):
            try:
                self.camera = cv2.VideoCapture(0)
                if self.camera.isOpened():
                    self.logger.info("Camera initialized")
                else:
                    self.logger.warning("Camera not available")
            except Exception as e:
                self.logger.warning(f"Camera initialization failed: {e}")
        
        # Verify CUDA availability
        if torch.cuda.is_available():
            self.logger.info(f"CUDA available with {torch.cuda.device_count()} GPU(s)")
            self.logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.logger.warning("CUDA not available")

    async def load_default_models(self):
        """Load default AI models"""
        models_dir = Path(self.config.get("models", {}).get("model_dir", "/var/lib/activelog/models"))
        
        # Load YOLOv5 for object detection
        yolo_path = models_dir / "pytorch" / "yolov5s.pt"
        if yolo_path.exists():
            await self.model_manager.load_model("yolov5s", "pytorch", str(yolo_path))
        
        # Load other common models
        for model_file in models_dir.glob("**/*.pt"):
            model_name = model_file.stem
            if model_name not in self.model_manager.models:
                await self.model_manager.load_model(model_name, "pytorch", str(model_file))

    async def batch_inference_loop(self):
        """Process inference requests in batches for efficiency"""
        batch_size = self.config.get("inference", {}).get("batch_size", 1)
        max_delay = self.config.get("inference", {}).get("max_batch_delay", 10)
        
        while self.running:
            batch = []
            start_time = time.time()
            
            try:
                # Collect requests for batching
                while len(batch) < batch_size and (time.time() - start_time) < max_delay:
                    try:
                        request = await asyncio.wait_for(
                            self.inference_queue.get(), 
                            timeout=max_delay - (time.time() - start_time)
                        )
                        batch.append(request)
                    except asyncio.TimeoutError:
                        break
                
                # Process batch if we have requests
                if batch:
                    await self.process_inference_batch(batch)
                
            except Exception as e:
                self.logger.error(f"Batch processing error: {e}")
                await asyncio.sleep(1)

    async def process_inference_batch(self, batch: List[Dict]):
        """Process a batch of inference requests"""
        # Group by model for efficient processing
        model_batches = {}
        for request in batch:
            model_name = request["model_name"]
            if model_name not in model_batches:
                model_batches[model_name] = []
            model_batches[model_name].append(request)
        
        # Process each model batch
        for model_name, requests in model_batches.items():
            try:
                # Combine inputs if possible
                if len(requests) == 1:
                    request = requests[0]
                    result = await self.model_manager.predict(
                        model_name, 
                        request["input_data"],
                        **request.get("kwargs", {})
                    )
                    request["callback"](result)
                else:
                    # Process individual requests (could be optimized for true batching)
                    for request in requests:
                        result = await self.model_manager.predict(
                            model_name,
                            request["input_data"],
                            **request.get("kwargs", {})
                        )
                        request["callback"](result)
                        
            except Exception as e:
                self.logger.error(f"Batch inference error for model {model_name}: {e}")
                # Call error callbacks
                for request in requests:
                    request["callback"]({"error": str(e)})

    async def queue_inference(self, model_name: str, input_data: Any, callback, **kwargs) -> None:
        """Queue an inference request"""
        request = {
            "model_name": model_name,
            "input_data": input_data,
            "callback": callback,
            "kwargs": kwargs,
            "timestamp": time.time()
        }
        
        await self.inference_queue.put(request)

    async def performance_monitor_loop(self):
        """Monitor system performance"""
        while self.running:
            try:
                stats = self.get_performance_stats()
                
                # Log performance if there are issues
                gpu_usage = stats.get("gpu_usage", 0)
                if gpu_usage > 90:
                    self.logger.warning(f"High GPU usage: {gpu_usage}%")
                
                memory_usage = stats.get("gpu_memory_usage", 0)
                if memory_usage > 90:
                    self.logger.warning(f"High GPU memory usage: {memory_usage}%")
                
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(30)

    def get_performance_stats(self) -> Dict:
        """Get comprehensive performance statistics"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.device_id
        }
        
        # CPU stats
        stats.update({
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        })
        
        # GPU stats (NVIDIA)
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # GPU utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            stats["gpu_usage"] = util.gpu
            stats["gpu_memory_usage"] = util.memory
            
            # GPU memory
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            stats["gpu_memory_total"] = mem_info.total / 1024**2  # MB
            stats["gpu_memory_used"] = mem_info.used / 1024**2   # MB
            stats["gpu_memory_free"] = mem_info.free / 1024**2   # MB
            
            # GPU temperature
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            stats["gpu_temperature"] = temp
            
        except Exception:
            # Fallback to nvidia-smi or other methods
            pass
        
        # Model manager stats
        stats["models"] = self.model_manager.get_model_stats()
        
        return stats

    async def thermal_monitor_loop(self):
        """Monitor thermal conditions and throttle if necessary"""
        while self.running:
            try:
                # Check temperatures
                temps = self.get_thermal_status()
                max_temp = max(temps.values()) if temps else 0
                
                thermal_limit = self.config.get("power", {}).get("thermal_limit", 80)
                
                if max_temp > thermal_limit:
                    self.logger.warning(f"Thermal throttling activated: {max_temp}°C")
                    await self.reduce_performance()
                elif max_temp < (thermal_limit - 5):  # Hysteresis
                    await self.restore_performance()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Thermal monitoring error: {e}")
                await asyncio.sleep(10)

    def get_thermal_status(self) -> Dict[str, float]:
        """Get thermal sensor readings"""
        temps = {}
        
        # CPU thermal zones
        thermal_zones = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/class/thermal/thermal_zone1/temp"
        ]
        
        for i, zone in enumerate(thermal_zones):
            try:
                with open(zone, 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
                    temps[f"cpu_zone_{i}"] = temp
            except:
                continue
        
        # GPU temperature (if available)
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            temps["gpu"] = gpu_temp
        except:
            pass
        
        return temps

    async def reduce_performance(self):
        """Reduce performance to manage thermals"""
        # Reduce batch size
        self.config.setdefault("inference", {})["batch_size"] = 1
        
        # Unload some models
        if len(self.model_manager.models) > 2:
            await self.model_manager.unload_least_used_model()

    async def restore_performance(self):
        """Restore normal performance"""
        # Restore normal batch size
        self.config.setdefault("inference", {})["batch_size"] = 4

    async def model_optimization_loop(self):
        """Periodically optimize models"""
        while self.running:
            try:
                # Run optimization every hour
                await asyncio.sleep(3600)
                
                if self.config.get("models", {}).get("auto_optimize", True):
                    await self.optimize_models()
                    
            except Exception as e:
                self.logger.error(f"Model optimization error: {e}")

    async def optimize_models(self):
        """Optimize loaded models for better performance"""
        for model_name, model_info in self.model_manager.models.items():
            try:
                if model_info["type"] == "pytorch":
                    await self.optimize_pytorch_model(model_name, model_info)
                    
            except Exception as e:
                self.logger.error(f"Failed to optimize model {model_name}: {e}")

    async def optimize_pytorch_model(self, model_name: str, model_info: Dict):
        """Optimize PyTorch model with TensorRT"""
        if not self.config.get("ai", {}).get("enable_optimization", True):
            return
        
        # Check if TensorRT version exists
        tensorrt_path = Path(self.config.get("models", {}).get("model_dir", "/var/lib/activelog/models")) / "tensorrt" / f"{model_name}.trt"
        
        if tensorrt_path.exists():
            return  # Already optimized
        
        self.logger.info(f"Optimizing model {model_name} with TensorRT")
        
        # Implementation would involve:
        # 1. Convert PyTorch model to ONNX
        # 2. Optimize ONNX model with TensorRT
        # 3. Save optimized model
        # 4. Update model manager to use optimized version

    async def health_check_loop(self):
        """Background health monitoring"""
        while self.running:
            try:
                health_status = self.get_health_status()
                
                if health_status["status"] != "healthy":
                    self.logger.warning(f"Health check issues: {health_status['issues']}")
                
                await asyncio.sleep(120)
                
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(120)

    def get_health_status(self) -> Dict:
        """Get agent health status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.device_id,
            "status": "healthy",
            "issues": []
        }
        
        # Check GPU availability
        if not torch.cuda.is_available():
            status["issues"].append("CUDA not available")
            status["status"] = "degraded"
        
        # Check model loading
        if len(self.model_manager.models) == 0:
            status["issues"].append("No models loaded")
            status["status"] = "degraded"
        
        # Check thermal status
        temps = self.get_thermal_status()
        if temps:
            max_temp = max(temps.values())
            if max_temp > 85:
                status["issues"].append(f"Critical temperature: {max_temp}°C")
                status["status"] = "critical"
            elif max_temp > 75:
                status["issues"].append(f"High temperature: {max_temp}°C")
                if status["status"] == "healthy":
                    status["status"] = "warning"
        
        return status

    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        import signal
        
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while self.running:
            await asyncio.sleep(1)


class PerformanceMonitor:
    """Monitor AI inference performance"""
    
    def __init__(self):
        self.metrics = {
            "inference_times": deque(maxlen=1000),
            "throughput": deque(maxlen=100),
            "memory_usage": deque(maxlen=100),
            "gpu_utilization": deque(maxlen=100)
        }

    def record_inference(self, duration: float, model_name: str):
        """Record inference performance"""
        self.metrics["inference_times"].append({
            "duration": duration,
            "model": model_name,
            "timestamp": time.time()
        })

    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        if not self.metrics["inference_times"]:
            return {}
        
        recent_times = [m["duration"] for m in self.metrics["inference_times"]]
        
        return {
            "avg_inference_time": np.mean(recent_times),
            "min_inference_time": np.min(recent_times),
            "max_inference_time": np.max(recent_times),
            "p95_inference_time": np.percentile(recent_times, 95),
            "total_inferences": len(recent_times),
            "throughput_fps": 1.0 / np.mean(recent_times) if recent_times else 0
        }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Jetson AI Agent")
    parser.add_argument("--config", default="/etc/activelog/edge.conf",
                        help="Configuration file path")
    
    args = parser.parse_args()
    
    # Create and run the agent
    agent = JetsonAIAgent(args.config)
    
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("Agent stopped by user")
    except Exception as e:
        print(f"Agent error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()