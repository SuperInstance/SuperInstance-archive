"""
Video transcoding and optimization service
"""
import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

import ffmpeg
import structlog

from config.settings import settings
from services.storage import storage_service

logger = structlog.get_logger()


class TranscodingService:
    """
    Advanced video transcoding service with multiple format and quality options
    """
    
    def __init__(self):
        self.supported_formats = settings.transcode_formats
        self.supported_resolutions = settings.transcode_resolutions
        self.bitrate_mappings = settings.transcode_bitrates
        
    async def transcode_video(
        self,
        input_path: str,
        output_path: str,
        target_format: str = "mp4",
        target_resolution: str = "720p",
        quality: str = "medium",
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """
        Transcode a video to specified format and quality
        
        Args:
            input_path: Path to input video file
            output_path: Path for output video file
            target_format: Target format (mp4, webm, etc.)
            target_resolution: Target resolution (480p, 720p, 1080p, etc.)
            quality: Quality preset (fast, medium, slow)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Transcoding result with metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate inputs
            if not os.path.exists(input_path):
                raise ValueError(f"Input file does not exist: {input_path}")
                
            if target_format not in self.supported_formats:
                raise ValueError(f"Unsupported format: {target_format}")
                
            if target_resolution not in self.supported_resolutions:
                raise ValueError(f"Unsupported resolution: {target_resolution}")
                
            # Get input video info
            input_info = await self._get_video_info(input_path)
            
            # Build transcoding parameters
            transcode_params = self._build_transcode_params(
                target_format=target_format,
                target_resolution=target_resolution,
                quality=quality,
                input_info=input_info
            )
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Run transcoding with progress monitoring
            await self._run_ffmpeg_transcode(
                input_path=input_path,
                output_path=output_path,
                params=transcode_params,
                progress_callback=progress_callback,
                total_duration=input_info.get("duration", 0)
            )
            
            # Get output video info
            output_info = await self._get_video_info(output_path)
            
            # Calculate processing time and compression ratio
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            compression_ratio = input_size / output_size if output_size > 0 else 0
            
            result = {
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "target_format": target_format,
                "target_resolution": target_resolution,
                "quality": quality,
                "input_info": input_info,
                "output_info": output_info,
                "processing_time_seconds": processing_time,
                "input_size_bytes": input_size,
                "output_size_bytes": output_size,
                "compression_ratio": compression_ratio,
                "size_reduction_percent": ((input_size - output_size) / input_size * 100) if input_size > 0 else 0,
                "transcode_params": transcode_params,
                "created_at": start_time.isoformat(),
                "completed_at": end_time.isoformat()
            }
            
            logger.info("Video transcoding completed successfully",
                       input_path=input_path,
                       output_path=output_path,
                       target_format=target_format,
                       target_resolution=target_resolution,
                       processing_time=processing_time,
                       compression_ratio=compression_ratio)
            
            return result
            
        except Exception as e:
            logger.error("Video transcoding failed",
                        input_path=input_path,
                        output_path=output_path,
                        error=str(e))
            
            return {
                "success": False,
                "error": str(e),
                "input_path": input_path,
                "output_path": output_path,
                "target_format": target_format,
                "target_resolution": target_resolution,
                "created_at": start_time.isoformat()
            }

    async def transcode_multiple_variants(
        self,
        input_path: str,
        output_dir: str,
        variants: List[Dict[str, str]],
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Transcode video into multiple variants simultaneously
        
        Args:
            input_path: Path to input video
            output_dir: Directory for output variants
            variants: List of variant configurations
            progress_callback: Optional callback for progress updates
            
        Returns:
            Results for all variants
        """
        start_time = datetime.utcnow()
        results = []
        
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Process each variant
            tasks = []
            for i, variant in enumerate(variants):
                output_filename = self._generate_variant_filename(
                    input_path, variant, i
                )
                output_path = os.path.join(output_dir, output_filename)
                
                # Create progress callback for this variant
                variant_progress_callback = None
                if progress_callback:
                    variant_id = f"{variant.get('format', 'mp4')}_{variant.get('resolution', '720p')}"
                    variant_progress_callback = lambda progress, vid=variant_id: progress_callback(vid, progress)
                
                # Create transcoding task
                task = self.transcode_video(
                    input_path=input_path,
                    output_path=output_path,
                    target_format=variant.get("format", "mp4"),
                    target_resolution=variant.get("resolution", "720p"),
                    quality=variant.get("quality", "medium"),
                    progress_callback=variant_progress_callback
                )
                tasks.append(task)
                
            # Execute all transcoding tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_variants = []
            failed_variants = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_variants.append({
                        "variant": variants[i],
                        "error": str(result)
                    })
                elif result.get("success", False):
                    successful_variants.append(result)
                else:
                    failed_variants.append({
                        "variant": variants[i],
                        "error": result.get("error", "Unknown error")
                    })
                    
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            summary = {
                "success": len(failed_variants) == 0,
                "input_path": input_path,
                "output_dir": output_dir,
                "total_variants": len(variants),
                "successful_variants": len(successful_variants),
                "failed_variants": len(failed_variants),
                "processing_time_seconds": processing_time,
                "results": successful_variants,
                "errors": failed_variants,
                "created_at": start_time.isoformat(),
                "completed_at": end_time.isoformat()
            }
            
            logger.info("Multi-variant transcoding completed",
                       input_path=input_path,
                       total_variants=len(variants),
                       successful=len(successful_variants),
                       failed=len(failed_variants),
                       processing_time=processing_time)
            
            return summary
            
        except Exception as e:
            logger.error("Multi-variant transcoding failed",
                        input_path=input_path,
                        error=str(e))
            return {
                "success": False,
                "error": str(e),
                "input_path": input_path,
                "output_dir": output_dir,
                "created_at": start_time.isoformat()
            }

    async def optimize_for_web(
        self,
        input_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """
        Optimize video specifically for web delivery
        """
        try:
            # Get input video info
            input_info = await self._get_video_info(input_path)
            
            # Build web optimization parameters
            params = {
                "video_codec": "libx264",
                "audio_codec": "aac",
                "format": "mp4",
                "preset": "medium",
                "crf": 23,  # Constant Rate Factor for good quality/size balance
                "profile": "high",
                "level": "4.0",
                "movflags": "+faststart",  # Enable streaming
                "pixel_format": "yuv420p",  # Maximum compatibility
                "audio_bitrate": "128k",
                "audio_sample_rate": 48000,
                "max_muxing_queue_size": 1024
            }
            
            # Adjust based on input resolution
            input_width = input_info.get("width", 0)
            input_height = input_info.get("height", 0)
            
            if input_width > 1920 or input_height > 1080:
                # Scale down to 1080p max
                params["scale"] = "1920:1080"
                params["video_bitrate"] = "4000k"
            elif input_width > 1280 or input_height > 720:
                # Scale down to 720p
                params["scale"] = "1280:720" 
                params["video_bitrate"] = "2500k"
            else:
                # Keep original resolution
                params["video_bitrate"] = "1500k"
                
            # Run optimization
            result = await self._run_ffmpeg_optimize(
                input_path=input_path,
                output_path=output_path,
                params=params,
                progress_callback=progress_callback,
                total_duration=input_info.get("duration", 0)
            )
            
            return result
            
        except Exception as e:
            logger.error("Web optimization failed",
                        input_path=input_path,
                        error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    async def create_video_preview(
        self,
        input_path: str,
        output_path: str,
        duration: int = 30,
        start_offset: int = 10,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """
        Create a short preview/trailer from the original video
        """
        try:
            # Get input video info
            input_info = await self._get_video_info(input_path)
            total_duration = input_info.get("duration", 0)
            
            if total_duration < duration + start_offset:
                # Video is too short, adjust parameters
                start_offset = 0
                duration = min(duration, int(total_duration))
                
            # Create preview using ffmpeg
            (
                ffmpeg
                .input(input_path, ss=start_offset, t=duration)
                .output(
                    output_path,
                    vcodec="libx264",
                    acodec="aac",
                    preset="fast",
                    crf=28,
                    vf="scale=854:480",  # 480p resolution
                    movflags="+faststart"
                )
                .overwrite_output()
                .run_async()
            )
            
            return {
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "preview_duration": duration,
                "start_offset": start_offset
            }
            
        except Exception as e:
            logger.error("Preview creation failed",
                        input_path=input_path,
                        error=str(e))
            return {
                "success": False,
                "error": str(e)
            }

    def _build_transcode_params(
        self,
        target_format: str,
        target_resolution: str,
        quality: str,
        input_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build FFmpeg parameters for transcoding"""
        params = {}
        
        # Video codec selection
        if target_format == "mp4":
            params["video_codec"] = "libx264"
            params["audio_codec"] = "aac"
        elif target_format == "webm":
            params["video_codec"] = "libvp9"
            params["audio_codec"] = "libopus"
        else:
            params["video_codec"] = "libx264"
            params["audio_codec"] = "aac"
            
        # Resolution and bitrate
        if target_resolution in self.bitrate_mappings:
            params["video_bitrate"] = self.bitrate_mappings[target_resolution]
            
        # Quality preset
        quality_presets = {
            "fast": {"preset": "fast", "crf": 28},
            "medium": {"preset": "medium", "crf": 23},
            "slow": {"preset": "slow", "crf": 20}
        }
        
        if quality in quality_presets:
            params.update(quality_presets[quality])
        else:
            params.update(quality_presets["medium"])
            
        # Resolution scaling
        resolution_map = {
            "480p": "854:480",
            "720p": "1280:720",
            "1080p": "1920:1080"
        }
        
        if target_resolution in resolution_map:
            params["scale"] = resolution_map[target_resolution]
            
        # Audio settings
        params["audio_bitrate"] = "128k"
        params["audio_sample_rate"] = 48000
        
        # Format-specific optimizations
        if target_format == "mp4":
            params["movflags"] = "+faststart"
            params["pixel_format"] = "yuv420p"
        elif target_format == "webm":
            params["deadline"] = "good"
            params["cpu_used"] = 2
            
        return params

    async def _run_ffmpeg_transcode(
        self,
        input_path: str,
        output_path: str,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[float], None]],
        total_duration: float
    ) -> None:
        """Run FFmpeg transcoding with progress monitoring"""
        try:
            # Build FFmpeg input
            input_stream = ffmpeg.input(input_path)
            
            # Build output stream with parameters
            output_args = {}
            
            if "video_codec" in params:
                output_args["vcodec"] = params["video_codec"]
            if "audio_codec" in params:
                output_args["acodec"] = params["audio_codec"]
            if "video_bitrate" in params:
                output_args["video_bitrate"] = params["video_bitrate"]
            if "audio_bitrate" in params:
                output_args["audio_bitrate"] = params["audio_bitrate"]
            if "preset" in params:
                output_args["preset"] = params["preset"]
            if "crf" in params:
                output_args["crf"] = params["crf"]
            if "scale" in params:
                output_args["vf"] = f"scale={params['scale']}"
            if "movflags" in params:
                output_args["movflags"] = params["movflags"]
            if "pixel_format" in params:
                output_args["pix_fmt"] = params["pixel_format"]
                
            output_stream = ffmpeg.output(input_stream, output_path, **output_args)
            
            # Run with progress monitoring if callback provided
            if progress_callback and total_duration > 0:
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg.compile(output_stream.overwrite_output()),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Monitor progress through stderr
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break
                        
                    line = line.decode('utf-8').strip()
                    if 'time=' in line:
                        # Extract current time
                        time_match = line.split('time=')[1].split()[0]
                        try:
                            current_time = self._parse_time_to_seconds(time_match)
                            progress = min(current_time / total_duration * 100, 100)
                            progress_callback(progress)
                        except:
                            pass
                            
                await process.wait()
                
                if process.returncode != 0:
                    stderr = await process.stderr.read()
                    raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")
            else:
                # Run without progress monitoring
                ffmpeg.run(output_stream.overwrite_output(), quiet=True)
                
        except Exception as e:
            logger.error("FFmpeg transcoding failed",
                        input_path=input_path,
                        output_path=output_path,
                        error=str(e))
            raise

    async def _run_ffmpeg_optimize(
        self,
        input_path: str,
        output_path: str,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[float], None]],
        total_duration: float
    ) -> Dict[str, Any]:
        """Run FFmpeg optimization with parameters"""
        start_time = datetime.utcnow()
        
        try:
            # Build FFmpeg command
            cmd = ["ffmpeg", "-i", input_path, "-y"]
            
            # Add video parameters
            if "video_codec" in params:
                cmd.extend(["-c:v", params["video_codec"]])
            if "audio_codec" in params:
                cmd.extend(["-c:a", params["audio_codec"]])
            if "preset" in params:
                cmd.extend(["-preset", params["preset"]])
            if "crf" in params:
                cmd.extend(["-crf", str(params["crf"])])
            if "profile" in params:
                cmd.extend(["-profile:v", params["profile"]])
            if "level" in params:
                cmd.extend(["-level", params["level"]])
            if "pixel_format" in params:
                cmd.extend(["-pix_fmt", params["pixel_format"]])
            if "scale" in params:
                cmd.extend(["-vf", f"scale={params['scale']}"])
            if "video_bitrate" in params:
                cmd.extend(["-b:v", params["video_bitrate"]])
            if "audio_bitrate" in params:
                cmd.extend(["-b:a", params["audio_bitrate"]])
            if "audio_sample_rate" in params:
                cmd.extend(["-ar", str(params["audio_sample_rate"])])
            if "movflags" in params:
                cmd.extend(["-movflags", params["movflags"]])
                
            cmd.append(output_path)
            
            # Run command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode != 0:
                stderr = await process.stderr.read()
                raise RuntimeError(f"FFmpeg optimization failed: {stderr.decode()}")
                
            # Get output info
            output_info = await self._get_video_info(output_path)
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "output_path": output_path,
                "output_info": output_info,
                "processing_time_seconds": processing_time,
                "parameters_used": params
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "parameters_used": params
            }

    async def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Get basic video information using ffprobe"""
        try:
            probe = ffmpeg.probe(video_path)
            
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                return {}
                
            return {
                "duration": float(probe['format'].get('duration', 0)),
                "width": int(video_stream.get('width', 0)),
                "height": int(video_stream.get('height', 0)),
                "fps": eval(video_stream.get('r_frame_rate', '0/1')),
                "codec": video_stream.get('codec_name'),
                "bitrate": int(probe['format'].get('bit_rate', 0)),
                "size": int(probe['format'].get('size', 0))
            }
            
        except Exception as e:
            logger.error("Failed to get video info", video_path=video_path, error=str(e))
            return {}

    def _generate_variant_filename(
        self,
        input_path: str,
        variant: Dict[str, str],
        index: int
    ) -> str:
        """Generate filename for transcode variant"""
        base_name = Path(input_path).stem
        format_ext = variant.get("format", "mp4")
        resolution = variant.get("resolution", "720p")
        quality = variant.get("quality", "medium")
        
        return f"{base_name}_{resolution}_{quality}_{index}.{format_ext}"

    def _parse_time_to_seconds(self, time_str: str) -> float:
        """Parse FFmpeg time format (HH:MM:SS.MS) to seconds"""
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            return 0.0
        except:
            return 0.0


# Global transcoding service instance
transcoding_service = TranscodingService()