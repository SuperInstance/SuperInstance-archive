"""
Subtitle extraction and indexing processor for video content
"""

import asyncio
import os
import tempfile
import subprocess
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import aiofiles
import chardet
from pathlib import Path

from ..core.config import settings
from ..core.database import DatabaseManager
from ..models.video_models import VideoFile, ProcessingJob

logger = logging.getLogger(__name__)

class SubtitleProcessor:
    """Processor for extracting and indexing video subtitles"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)
        
        # Supported subtitle formats
        self.supported_formats = ['srt', 'vtt', 'ass', 'ssa', 'sub', 'idx', 'scc']
        
        # FFmpeg subtitle extraction settings
        self.ffmpeg_timeout = 300  # 5 minutes
        
        # Text processing settings
        self.min_subtitle_length = 2
        self.max_subtitle_length = 500
        
    async def process_video_subtitles(self, job_id: str, video_path: str,
                                    extract_embedded: bool = True,
                                    generate_auto_subtitles: bool = False,
                                    target_languages: List[str] = None) -> Dict[str, Any]:
        """
        Extract and index video subtitles from multiple sources
        
        Args:
            job_id: Processing job ID
            video_path: Path to video file
            extract_embedded: Whether to extract embedded subtitles
            generate_auto_subtitles: Whether to generate automatic subtitles
            target_languages: List of language codes to process
            
        Returns:
            Dictionary containing subtitle processing results
        """
        if target_languages is None:
            target_languages = ['en']
        
        try:
            logger.info(f"Starting subtitle processing for job {job_id}: {video_path}")
            
            # Update job status
            await self.db_manager.update_job_status(job_id, 'processing', 
                                                  {'stage': 'subtitle_extraction'})
            
            results = {
                'job_id': job_id,
                'video_path': video_path,
                'processing_time': datetime.utcnow().isoformat(),
                'subtitles': [],
                'statistics': {},
                'errors': []
            }
            
            progress = 0
            
            # 1. Extract embedded subtitles
            if extract_embedded:
                try:
                    embedded_subs = await self._extract_embedded_subtitles(
                        job_id, video_path, target_languages
                    )
                    results['subtitles'].extend(embedded_subs)
                    progress += 40
                    await self.db_manager.update_job_progress(job_id, progress)
                    logger.info(f"Extracted {len(embedded_subs)} embedded subtitle tracks")
                except Exception as e:
                    logger.warning(f"Embedded subtitle extraction failed: {str(e)}")
                    results['errors'].append(f"Embedded extraction: {str(e)}")
            
            # 2. Look for external subtitle files
            try:
                external_subs = await self._find_external_subtitles(
                    job_id, video_path, target_languages
                )
                results['subtitles'].extend(external_subs)
                progress += 30
                await self.db_manager.update_job_progress(job_id, progress)
                logger.info(f"Found {len(external_subs)} external subtitle files")
            except Exception as e:
                logger.warning(f"External subtitle search failed: {str(e)}")
                results['errors'].append(f"External search: {str(e)}")
            
            # 3. Generate automatic subtitles if requested and no subtitles found
            if generate_auto_subtitles and not results['subtitles']:
                try:
                    auto_subs = await self._generate_automatic_subtitles(
                        job_id, video_path, target_languages
                    )
                    results['subtitles'].extend(auto_subs)
                    progress += 20
                    await self.db_manager.update_job_progress(job_id, progress)
                    logger.info(f"Generated {len(auto_subs)} automatic subtitle tracks")
                except Exception as e:
                    logger.warning(f"Automatic subtitle generation failed: {str(e)}")
                    results['errors'].append(f"Auto generation: {str(e)}")
            
            # 4. Process and index all subtitle content
            if results['subtitles']:
                try:
                    await self._index_subtitle_content(job_id, results['subtitles'])
                    progress += 10
                    await self.db_manager.update_job_progress(job_id, progress)
                except Exception as e:
                    logger.warning(f"Subtitle indexing failed: {str(e)}")
                    results['errors'].append(f"Indexing: {str(e)}")
            
            # Generate statistics
            results['statistics'] = await self._generate_subtitle_statistics(results['subtitles'])
            
            # Update job status
            await self.db_manager.update_job_status(job_id, 'completed', results)
            
            logger.info(f"Subtitle processing completed for job {job_id}")
            return results
            
        except Exception as e:
            logger.error(f"Subtitle processing failed for job {job_id}: {str(e)}")
            await self.db_manager.update_job_status(job_id, 'failed', {'error': str(e)})
            raise
    
    async def _extract_embedded_subtitles(self, job_id: str, video_path: str,
                                        target_languages: List[str]) -> List[Dict]:
        """Extract embedded subtitles using FFmpeg"""
        
        extracted_subtitles = []
        
        try:
            # First, probe the video for subtitle streams
            probe_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_streams', '-select_streams', 's', video_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *probe_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=30
            )
            
            if process.returncode != 0:
                logger.warning(f"FFprobe failed: {stderr.decode()}")
                return []
            
            probe_data = json.loads(stdout.decode())
            subtitle_streams = probe_data.get('streams', [])
            
            if not subtitle_streams:
                logger.info("No embedded subtitle streams found")
                return []
            
            # Extract each subtitle stream
            for i, stream in enumerate(subtitle_streams):
                try:
                    codec_name = stream.get('codec_name', 'unknown')
                    language = stream.get('tags', {}).get('language', 'unknown')
                    
                    # Skip if language not in target languages (unless unknown)
                    if language != 'unknown' and language not in target_languages:
                        continue
                    
                    # Determine output format based on codec
                    if codec_name in ['subrip', 'srt']:
                        ext = 'srt'
                    elif codec_name in ['webvtt', 'vtt']:
                        ext = 'vtt'
                    elif codec_name in ['ass', 'ssa']:
                        ext = 'ass'
                    else:
                        ext = 'srt'  # Default to SRT
                    
                    # Create temporary output file
                    with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as temp_file:
                        temp_path = temp_file.name
                    
                    # Extract subtitle stream
                    extract_cmd = [
                        'ffmpeg', '-y', '-i', video_path,
                        '-map', f'0:s:{i}', '-c:s', ext, temp_path
                    ]
                    
                    process = await asyncio.create_subprocess_exec(
                        *extract_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=self.ffmpeg_timeout
                    )
                    
                    if process.returncode == 0 and os.path.exists(temp_path):
                        # Read and process subtitle content
                        subtitle_data = await self._process_subtitle_file(
                            temp_path, ext, language, 'embedded'
                        )
                        
                        if subtitle_data:
                            # Save to database
                            subtitle_id = await self.db_manager.save_subtitles(
                                job_id=job_id,
                                subtitle_type='extracted',
                                language=language,
                                format_type=ext,
                                content=subtitle_data['content'],
                                confidence=0.9  # High confidence for embedded subs
                            )
                            
                            extracted_subtitles.append({
                                'subtitle_id': subtitle_id,
                                'stream_index': i,
                                'language': language,
                                'format': ext,
                                'codec': codec_name,
                                'entry_count': len(subtitle_data['entries']),
                                'source': 'embedded',
                                'entries': subtitle_data['entries']
                            })
                            
                            logger.info(f"Extracted embedded subtitle: {language} ({ext})")
                    else:
                        logger.warning(f"Failed to extract subtitle stream {i}: {stderr.decode()}")
                    
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                
                except Exception as e:
                    logger.warning(f"Error extracting subtitle stream {i}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Embedded subtitle extraction error: {str(e)}")
        
        return extracted_subtitles
    
    async def _find_external_subtitles(self, job_id: str, video_path: str,
                                     target_languages: List[str]) -> List[Dict]:
        """Find external subtitle files in the same directory"""
        
        external_subtitles = []
        
        try:
            video_file = Path(video_path)
            video_dir = video_file.parent
            video_name = video_file.stem
            
            # Common subtitle file patterns
            patterns = [
                f"{video_name}.{{lang}}.{{ext}}",
                f"{video_name}.{{ext}}",
                f"{video_name}_{{lang}}.{{ext}}",
                f"{video_name}-{{lang}}.{{ext}}"
            ]
            
            # Search for subtitle files
            for pattern in patterns:
                for ext in self.supported_formats:
                    for lang in target_languages + ['']:
                        if lang:
                            subtitle_path = video_dir / pattern.format(lang=lang, ext=ext)
                        else:
                            subtitle_path = video_dir / pattern.format(ext=ext).replace('.{lang}.', '.')
                        
                        if subtitle_path.exists() and subtitle_path.is_file():
                            try:
                                # Process subtitle file
                                subtitle_data = await self._process_subtitle_file(
                                    str(subtitle_path), ext, lang or 'unknown', 'external'
                                )
                                
                                if subtitle_data:
                                    # Save to database
                                    subtitle_id = await self.db_manager.save_subtitles(
                                        job_id=job_id,
                                        subtitle_type='extracted',
                                        language=lang or 'unknown',
                                        format_type=ext,
                                        file_path=str(subtitle_path),
                                        content=subtitle_data['content'],
                                        confidence=0.95  # Very high confidence for external files
                                    )
                                    
                                    external_subtitles.append({
                                        'subtitle_id': subtitle_id,
                                        'file_path': str(subtitle_path),
                                        'language': lang or 'unknown',
                                        'format': ext,
                                        'entry_count': len(subtitle_data['entries']),
                                        'source': 'external',
                                        'entries': subtitle_data['entries']
                                    })
                                    
                                    logger.info(f"Found external subtitle: {subtitle_path}")
                                
                            except Exception as e:
                                logger.warning(f"Error processing {subtitle_path}: {str(e)}")
                                continue
            
        except Exception as e:
            logger.error(f"External subtitle search error: {str(e)}")
        
        return external_subtitles
    
    async def _generate_automatic_subtitles(self, job_id: str, video_path: str,
                                          target_languages: List[str]) -> List[Dict]:
        """Generate automatic subtitles using speech recognition"""
        
        # Note: This would require additional dependencies like whisper-ai
        # For now, return empty list as placeholder
        logger.info("Automatic subtitle generation not implemented yet")
        return []
        
        # Future implementation would use something like:
        # import whisper
        # model = whisper.load_model("base")
        # result = model.transcribe(video_path)
        # return processed_whisper_results
    
    async def _process_subtitle_file(self, file_path: str, format_type: str,
                                   language: str, source: str) -> Optional[Dict]:
        """Process subtitle file and extract entries"""
        
        try:
            # Detect file encoding
            async with aiofiles.open(file_path, 'rb') as f:
                raw_data = await f.read()
                encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
            
            # Read file content
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                content = await f.read()
            
            # Parse based on format
            if format_type == 'srt':
                entries = self._parse_srt(content)
            elif format_type == 'vtt':
                entries = self._parse_vtt(content)
            elif format_type in ['ass', 'ssa']:
                entries = self._parse_ass(content)
            else:
                # Try to parse as SRT by default
                entries = self._parse_srt(content)
            
            if not entries:
                return None
            
            return {
                'content': content,
                'entries': entries,
                'format': format_type,
                'language': language,
                'source': source
            }
            
        except Exception as e:
            logger.error(f"Error processing subtitle file {file_path}: {str(e)}")
            return None
    
    def _parse_srt(self, content: str) -> List[Dict]:
        """Parse SRT subtitle format"""
        
        entries = []
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            try:
                # Parse index
                index = int(lines[0])
                
                # Parse timestamp
                time_match = re.match(
                    r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                    lines[1]
                )
                
                if not time_match:
                    continue
                
                start_time = self._time_to_seconds(
                    int(time_match.group(1)), int(time_match.group(2)),
                    int(time_match.group(3)), int(time_match.group(4))
                )
                
                end_time = self._time_to_seconds(
                    int(time_match.group(5)), int(time_match.group(6)),
                    int(time_match.group(7)), int(time_match.group(8))
                )
                
                # Parse text
                text = '\n'.join(lines[2:]).strip()
                
                # Clean up text (remove HTML tags, etc.)
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'\{[^}]+\}', '', text)
                
                if len(text) >= self.min_subtitle_length:
                    entries.append({
                        'index': index,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'text': text,
                        'word_count': len(text.split())
                    })
                
            except Exception as e:
                logger.warning(f"Error parsing SRT block: {str(e)}")
                continue
        
        return entries
    
    def _parse_vtt(self, content: str) -> List[Dict]:
        """Parse WebVTT subtitle format"""
        
        entries = []
        
        # Remove WEBVTT header
        content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.MULTILINE | re.DOTALL)
        
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for i, block in enumerate(blocks):
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            if len(lines) < 2:
                continue
            
            try:
                # Find timestamp line
                timestamp_line = None
                text_lines = []
                
                for line in lines:
                    if '-->' in line:
                        timestamp_line = line
                    elif timestamp_line is not None:
                        text_lines.append(line)
                
                if not timestamp_line or not text_lines:
                    continue
                
                # Parse timestamp
                time_match = re.search(
                    r'(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})\.(\d{3})',
                    timestamp_line
                )
                
                if not time_match:
                    continue
                
                start_time = self._time_to_seconds(
                    int(time_match.group(1)), int(time_match.group(2)),
                    int(time_match.group(3)), int(time_match.group(4))
                )
                
                end_time = self._time_to_seconds(
                    int(time_match.group(5)), int(time_match.group(6)),
                    int(time_match.group(7)), int(time_match.group(8))
                )
                
                # Parse text
                text = '\n'.join(text_lines).strip()
                
                # Clean up text
                text = re.sub(r'<[^>]+>', '', text)
                text = re.sub(r'\{[^}]+\}', '', text)
                
                if len(text) >= self.min_subtitle_length:
                    entries.append({
                        'index': i + 1,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': end_time - start_time,
                        'text': text,
                        'word_count': len(text.split())
                    })
                
            except Exception as e:
                logger.warning(f"Error parsing VTT block: {str(e)}")
                continue
        
        return entries
    
    def _parse_ass(self, content: str) -> List[Dict]:
        """Parse ASS/SSA subtitle format"""
        
        entries = []
        
        # Find dialogue events
        in_events = False
        format_line = None
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('[Events]'):
                in_events = True
                continue
            elif line.startswith('[') and in_events:
                break
            
            if not in_events:
                continue
            
            if line.startswith('Format:'):
                format_line = line[7:].strip()
                continue
            
            if line.startswith('Dialogue:') and format_line:
                try:
                    # Parse format
                    format_fields = [f.strip() for f in format_line.split(',')]
                    dialogue_values = [v.strip() for v in line[9:].split(',')]
                    
                    if len(dialogue_values) < len(format_fields):
                        continue
                    
                    # Create mapping
                    dialogue_dict = dict(zip(format_fields, dialogue_values))
                    
                    # Parse times
                    start_time = self._parse_ass_time(dialogue_dict.get('Start', '0:00:00.00'))
                    end_time = self._parse_ass_time(dialogue_dict.get('End', '0:00:00.00'))
                    
                    # Get text (last field, may contain commas)
                    text = ','.join(dialogue_values[len(format_fields)-1:])
                    
                    # Clean up text
                    text = re.sub(r'\{[^}]+\}', '', text)
                    text = re.sub(r'\\[nN]', ' ', text)
                    text = text.strip()
                    
                    if len(text) >= self.min_subtitle_length and start_time < end_time:
                        entries.append({
                            'index': len(entries) + 1,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': end_time - start_time,
                            'text': text,
                            'word_count': len(text.split())
                        })
                
                except Exception as e:
                    logger.warning(f"Error parsing ASS dialogue: {str(e)}")
                    continue
        
        return entries
    
    def _time_to_seconds(self, hours: int, minutes: int, seconds: int, 
                        milliseconds: int) -> float:
        """Convert time components to seconds"""
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
    
    def _parse_ass_time(self, time_str: str) -> float:
        """Parse ASS time format (H:MM:SS.ss)"""
        try:
            parts = time_str.split(':')
            if len(parts) != 3:
                return 0.0
            
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            centiseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
            
            return hours * 3600 + minutes * 60 + seconds + centiseconds / 100.0
            
        except Exception:
            return 0.0
    
    async def _index_subtitle_content(self, job_id: str, subtitles: List[Dict]):
        """Index subtitle content in database for searching"""
        
        for subtitle in subtitles:
            subtitle_id = subtitle['subtitle_id']
            
            for entry in subtitle['entries']:
                try:
                    await self.db_manager.save_subtitle_entry(
                        subtitle_id=subtitle_id,
                        start_time=entry['start_time'],
                        end_time=entry['end_time'],
                        text_content=entry['text'],
                        confidence=0.9,  # High confidence for parsed subtitles
                        entry_index=entry['index']
                    )
                    
                except Exception as e:
                    logger.warning(f"Error indexing subtitle entry: {str(e)}")
                    continue
        
        logger.info(f"Indexed subtitle content for job {job_id}")
    
    async def _generate_subtitle_statistics(self, subtitles: List[Dict]) -> Dict[str, Any]:
        """Generate statistics about processed subtitles"""
        
        if not subtitles:
            return {
                'total_tracks': 0,
                'total_entries': 0,
                'total_words': 0,
                'languages': [],
                'formats': [],
                'sources': []
            }
        
        total_entries = sum(sub['entry_count'] for sub in subtitles)
        total_words = 0
        languages = set()
        formats = set()
        sources = set()
        
        for subtitle in subtitles:
            languages.add(subtitle['language'])
            formats.add(subtitle['format'])
            sources.add(subtitle['source'])
            
            for entry in subtitle.get('entries', []):
                total_words += entry.get('word_count', 0)
        
        return {
            'total_tracks': len(subtitles),
            'total_entries': total_entries,
            'total_words': total_words,
            'average_words_per_entry': total_words / total_entries if total_entries > 0 else 0,
            'languages': list(languages),
            'formats': list(formats),
            'sources': list(sources)
        }
    
    async def search_subtitles(self, query: str, language: str = None,
                              limit: int = 50) -> List[Dict]:
        """Search subtitle content across all videos"""
        
        try:
            base_query = """
                SELECT 
                    se.subtitle_id,
                    vs.job_id,
                    vpj.original_filename,
                    vs.language,
                    se.start_time_seconds,
                    se.end_time_seconds,
                    se.text_content,
                    se.confidence_score
                FROM subtitle_entries se
                JOIN video_subtitles vs ON se.subtitle_id = vs.subtitle_id
                JOIN video_processing_jobs vpj ON vs.job_id = vpj.job_id
                WHERE se.text_content ILIKE $1
            """
            
            params = [f"%{query}%"]
            
            if language:
                base_query += " AND vs.language = $2"
                params.append(language)
            
            base_query += " ORDER BY se.confidence_score DESC, se.start_time_seconds ASC"
            base_query += f" LIMIT ${len(params) + 1}"
            params.append(limit)
            
            results = await self.db_manager.fetch_all(base_query, *params)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Subtitle search failed: {str(e)}")
            return []
    
    async def get_video_subtitles(self, job_id: str) -> List[Dict]:
        """Get all subtitles for a video"""
        
        try:
            results = await self.db_manager.fetch_all("""
                SELECT 
                    vs.subtitle_id,
                    vs.subtitle_type,
                    vs.language,
                    vs.format,
                    vs.file_path,
                    vs.entry_count,
                    vs.confidence_score,
                    vs.created_at
                FROM video_subtitles vs
                WHERE vs.job_id = $1
                ORDER BY vs.language, vs.subtitle_type
            """, job_id)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get subtitles for job {job_id}: {str(e)}")
            return []
    
    async def get_subtitle_entries(self, subtitle_id: str) -> List[Dict]:
        """Get all entries for a subtitle track"""
        
        try:
            results = await self.db_manager.fetch_all("""
                SELECT 
                    entry_index,
                    start_time_seconds,
                    end_time_seconds,
                    text_content,
                    confidence_score,
                    speaker_id
                FROM subtitle_entries
                WHERE subtitle_id = $1
                ORDER BY start_time_seconds
            """, subtitle_id)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get subtitle entries: {str(e)}")
            return []