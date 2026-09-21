"""
File-related test fixtures and data generators
"""

import uuid
import random
import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from faker import Faker
from pathlib import Path

fake = Faker()


class FileFixtures:
    """Generate file test data and fixtures"""
    
    # File type configurations
    FILE_TYPES = {
        'document': {
            'extensions': ['.pdf', '.docx', '.doc', '.txt', '.md', '.rtf', '.odt'],
            'mime_types': [
                'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword', 'text/plain', 'text/markdown', 'application/rtf'
            ],
            'size_range': (1024, 10 * 1024 * 1024)  # 1KB to 10MB
        },
        'image': {
            'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
            'mime_types': [
                'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/svg+xml', 'image/webp'
            ],
            'size_range': (10 * 1024, 50 * 1024 * 1024)  # 10KB to 50MB
        },
        'video': {
            'extensions': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'],
            'mime_types': [
                'video/mp4', 'video/avi', 'video/quicktime', 'video/x-ms-wmv', 'video/webm'
            ],
            'size_range': (1024 * 1024, 2 * 1024 * 1024 * 1024)  # 1MB to 2GB
        },
        'audio': {
            'extensions': ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma'],
            'mime_types': [
                'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/ogg', 'audio/mp4'
            ],
            'size_range': (100 * 1024, 100 * 1024 * 1024)  # 100KB to 100MB
        },
        'archive': {
            'extensions': ['.zip', '.rar', '.tar', '.gz', '.7z', '.bz2'],
            'mime_types': [
                'application/zip', 'application/x-rar-compressed', 'application/x-tar',
                'application/gzip', 'application/x-7z-compressed'
            ],
            'size_range': (1024, 500 * 1024 * 1024)  # 1KB to 500MB
        },
        'spreadsheet': {
            'extensions': ['.xlsx', '.xls', '.csv', '.ods'],
            'mime_types': [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel', 'text/csv'
            ],
            'size_range': (1024, 50 * 1024 * 1024)  # 1KB to 50MB
        },
        'presentation': {
            'extensions': ['.pptx', '.ppt', '.odp'],
            'mime_types': [
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.ms-powerpoint'
            ],
            'size_range': (100 * 1024, 100 * 1024 * 1024)  # 100KB to 100MB
        }
    }
    
    @staticmethod
    def create_file(
        file_id: Optional[str] = None,
        user_id: Optional[str] = None,
        file_type: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a single file fixture"""
        
        file_id = file_id or str(uuid.uuid4())
        user_id = user_id or str(uuid.uuid4())
        file_type = file_type or random.choice(list(FileFixtures.FILE_TYPES.keys()))
        
        # Generate file properties based on type
        type_config = FileFixtures.FILE_TYPES[file_type]
        extension = random.choice(type_config['extensions'])
        mime_type = random.choice(type_config['mime_types'])
        size = random.randint(*type_config['size_range'])
        
        # Generate name if not provided
        if not name:
            base_name = fake.catch_phrase().replace(' ', '_').lower()
            name = f"{base_name}{extension}"
        
        # Generate path
        folder_depth = random.randint(0, 4)
        path_parts = [fake.word() for _ in range(folder_depth)]
        path = '/' + '/'.join(path_parts + [name]) if path_parts else f"/{name}"
        
        # Generate checksum
        checksum_input = f"{name}{size}{datetime.utcnow().isoformat()}"
        checksum = hashlib.sha256(checksum_input.encode()).hexdigest()
        
        created_time = fake.date_time_between(start_date='-1y', end_date='-1d')
        modified_time = fake.date_time_between(start_date=created_time, end_date='now')
        
        return {
            'id': file_id,
            'name': name,
            'path': path,
            'size': size,
            'file_type': file_type,
            'mime_type': mime_type,
            'extension': extension,
            'checksum': checksum,
            'user_id': user_id,
            'created_at': created_time,
            'modified_at': modified_time,
            'accessed_at': fake.date_time_between(start_date=modified_time, end_date='now'),
            'sync_status': random.choice(['local', 'synced', 'cloud', 'conflict', 'syncing']),
            'version': random.randint(1, 10),
            'is_deleted': fake.boolean(chance_of_getting_true=5),
            'is_public': fake.boolean(chance_of_getting_true=20),
            'is_favorite': fake.boolean(chance_of_getting_true=15),
            'download_count': random.randint(0, 100),
            'view_count': random.randint(0, 500),
            'metadata': FileFixtures._generate_file_metadata(file_type, name),
            'tags': random.sample([
                'work', 'personal', 'project', 'important', 'archive', 'draft',
                'review', 'shared', 'backup', 'temporary', 'confidential'
            ], random.randint(0, 3)),
            'permissions': {
                'owner': ['read', 'write', 'delete', 'share'],
                'group': random.choice([[], ['read'], ['read', 'write']]),
                'public': random.choice([[], ['read']])
            },
            **kwargs
        }
    
    @staticmethod
    def _generate_file_metadata(file_type: str, name: str) -> Dict[str, Any]:
        """Generate type-specific metadata"""
        
        base_metadata = {
            'title': Path(name).stem.replace('_', ' ').title(),
            'description': fake.text(max_nb_chars=200),
            'created_by': fake.name(),
            'language': random.choice(['en', 'es', 'fr', 'de', 'ja', 'zh']),
            'encoding': 'utf-8'
        }
        
        if file_type == 'document':
            base_metadata.update({
                'word_count': random.randint(100, 10000),
                'page_count': random.randint(1, 100),
                'author': fake.name(),
                'subject': fake.catch_phrase(),
                'keywords': fake.words(nb=5),
                'has_images': fake.boolean(),
                'has_tables': fake.boolean(),
                'is_searchable': fake.boolean(chance_of_getting_true=80)
            })
        
        elif file_type == 'image':
            base_metadata.update({
                'width': random.randint(100, 4000),
                'height': random.randint(100, 4000),
                'color_depth': random.choice([8, 16, 24, 32]),
                'has_exif': fake.boolean(),
                'camera_make': fake.company() if fake.boolean() else None,
                'camera_model': fake.bothify('#### ??') if fake.boolean() else None,
                'taken_at': fake.date_time_between(start_date='-2y', end_date='now') if fake.boolean() else None,
                'location': {
                    'latitude': fake.latitude(),
                    'longitude': fake.longitude()
                } if fake.boolean() else None,
                'faces_detected': random.randint(0, 10),
                'objects_detected': random.sample(['person', 'car', 'building', 'tree', 'animal'], random.randint(0, 3))
            })
        
        elif file_type == 'video':
            base_metadata.update({
                'duration_seconds': random.randint(10, 7200),
                'width': random.choice([720, 1080, 1440, 2160]),
                'height': random.choice([480, 720, 1080, 1440]),
                'fps': random.choice([24, 25, 30, 60]),
                'bitrate': random.randint(500, 50000),
                'codec': random.choice(['H.264', 'H.265', 'VP9', 'AV1']),
                'has_audio': fake.boolean(chance_of_getting_true=90),
                'audio_codec': random.choice(['AAC', 'MP3', 'Opus']) if fake.boolean() else None,
                'thumbnail_generated': fake.boolean(),
                'chapters': random.randint(0, 20)
            })
        
        elif file_type == 'audio':
            base_metadata.update({
                'duration_seconds': random.randint(30, 3600),
                'bitrate': random.randint(64, 320),
                'sample_rate': random.choice([22050, 44100, 48000, 96000]),
                'channels': random.choice([1, 2]),
                'codec': random.choice(['MP3', 'AAC', 'FLAC', 'OGG']),
                'album': fake.catch_phrase(),
                'artist': fake.name(),
                'genre': random.choice(['Pop', 'Rock', 'Jazz', 'Classical', 'Electronic']),
                'year': random.randint(1950, 2024),
                'track_number': random.randint(1, 20),
                'has_lyrics': fake.boolean(),
                'bpm': random.randint(60, 200)
            })
        
        elif file_type == 'archive':
            base_metadata.update({
                'compression_ratio': round(random.uniform(0.1, 0.9), 2),
                'file_count': random.randint(1, 1000),
                'folder_count': random.randint(0, 100),
                'is_encrypted': fake.boolean(chance_of_getting_true=20),
                'compression_method': random.choice(['deflate', 'bzip2', 'lzma', 'store']),
                'created_with': random.choice(['WinZip', '7-Zip', 'Archive Utility', 'tar'])
            })
        
        elif file_type == 'spreadsheet':
            base_metadata.update({
                'sheet_count': random.randint(1, 10),
                'row_count': random.randint(10, 100000),
                'column_count': random.randint(5, 100),
                'has_formulas': fake.boolean(),
                'has_charts': fake.boolean(),
                'has_macros': fake.boolean(chance_of_getting_true=20),
                'is_protected': fake.boolean(chance_of_getting_true=30),
                'last_calculated': fake.date_time_between(start_date='-30d', end_date='now')
            })
        
        elif file_type == 'presentation':
            base_metadata.update({
                'slide_count': random.randint(5, 100),
                'has_animations': fake.boolean(),
                'has_transitions': fake.boolean(),
                'has_embedded_media': fake.boolean(),
                'template_used': fake.catch_phrase(),
                'presentation_duration': random.randint(300, 3600),
                'notes_count': random.randint(0, 50)
            })
        
        return base_metadata
    
    @staticmethod
    def create_file_version(file_id: str, version: int = 1, **kwargs) -> Dict[str, Any]:
        """Create file version fixture"""
        return {
            'id': str(uuid.uuid4()),
            'file_id': file_id,
            'version': version,
            'size': random.randint(1024, 10 * 1024 * 1024),
            'checksum': fake.sha256(),
            'created_at': fake.date_time_between(start_date='-30d', end_date='now'),
            'created_by': str(uuid.uuid4()),
            'storage_path': f"/versions/{file_id}/{version}/{fake.file_name()}",
            'change_summary': fake.text(max_nb_chars=100),
            'is_current': version == 1,
            'download_count': random.randint(0, 50),
            **kwargs
        }
    
    @staticmethod
    def create_file_share(file_id: str, shared_by: str, **kwargs) -> Dict[str, Any]:
        """Create file share fixture"""
        return {
            'id': str(uuid.uuid4()),
            'file_id': file_id,
            'shared_by': shared_by,
            'shared_with': kwargs.get('shared_with', fake.email()),
            'share_type': random.choice(['email', 'link', 'public', 'team']),
            'permissions': random.choice([['read'], ['read', 'download'], ['read', 'write']]),
            'expires_at': fake.date_time_between(start_date='+1d', end_date='+30d') if fake.boolean() else None,
            'created_at': fake.date_time_between(start_date='-7d', end_date='now'),
            'accessed_count': random.randint(0, 100),
            'last_accessed_at': fake.date_time_between(start_date='-7d', end_date='now') if fake.boolean() else None,
            'is_active': fake.boolean(chance_of_getting_true=90),
            'password_protected': fake.boolean(chance_of_getting_true=30),
            'download_limit': random.randint(1, 100) if fake.boolean() else None,
            'token': fake.sha256(),
            **kwargs
        }
    
    @staticmethod
    def create_folder(
        folder_id: Optional[str] = None,
        user_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create folder fixture"""
        
        folder_id = folder_id or str(uuid.uuid4())
        user_id = user_id or str(uuid.uuid4())
        
        name = fake.catch_phrase().replace(' ', '_').lower()
        
        # Generate path based on parent
        if parent_id:
            path = f"/parent_folder/{name}"
        else:
            path = f"/{name}"
        
        return {
            'id': folder_id,
            'name': name,
            'path': path,
            'parent_id': parent_id,
            'user_id': user_id,
            'created_at': fake.date_time_between(start_date='-1y', end_date='-1d'),
            'modified_at': fake.date_time_between(start_date='-30d', end_date='now'),
            'is_deleted': fake.boolean(chance_of_getting_true=5),
            'is_public': fake.boolean(chance_of_getting_true=10),
            'file_count': random.randint(0, 100),
            'folder_count': random.randint(0, 20),
            'total_size': random.randint(0, 1024 * 1024 * 1024),
            'color': random.choice([None, 'blue', 'red', 'green', 'yellow', 'purple']),
            'description': fake.text(max_nb_chars=200) if fake.boolean() else None,
            'tags': random.sample([
                'project', 'archive', 'work', 'personal', 'shared', 'backup'
            ], random.randint(0, 2)),
            'permissions': {
                'owner': ['read', 'write', 'delete', 'share'],
                'group': random.choice([[], ['read'], ['read', 'write']]),
                'public': random.choice([[], ['read']])
            },
            **kwargs
        }
    
    @staticmethod
    def create_sync_conflict(file_id: str, **kwargs) -> Dict[str, Any]:
        """Create sync conflict fixture"""
        return {
            'id': str(uuid.uuid4()),
            'file_id': file_id,
            'conflict_type': random.choice(['modification', 'deletion', 'rename', 'move']),
            'local_version': {
                'size': random.randint(1024, 10 * 1024 * 1024),
                'modified_at': fake.date_time_between(start_date='-7d', end_date='now'),
                'checksum': fake.sha256()
            },
            'remote_version': {
                'size': random.randint(1024, 10 * 1024 * 1024),
                'modified_at': fake.date_time_between(start_date='-7d', end_date='now'),
                'checksum': fake.sha256()
            },
            'detected_at': fake.date_time_between(start_date='-1d', end_date='now'),
            'resolved_at': None,
            'resolution_strategy': None,
            'resolved_by': None,
            'status': 'pending',
            **kwargs
        }
    
    @staticmethod
    def create_files_for_user(user_id: str, count: int = 50) -> List[Dict[str, Any]]:
        """Create multiple files for a specific user"""
        files = []
        
        # Ensure variety in file types
        type_distribution = {
            'document': 0.4,
            'image': 0.3,
            'video': 0.1,
            'audio': 0.05,
            'archive': 0.05,
            'spreadsheet': 0.05,
            'presentation': 0.05
        }
        
        for _ in range(count):
            # Choose file type based on distribution
            rand = random.random()
            cumulative = 0
            selected_type = 'document'
            
            for file_type, probability in type_distribution.items():
                cumulative += probability
                if rand <= cumulative:
                    selected_type = file_type
                    break
            
            file_data = FileFixtures.create_file(user_id=user_id, file_type=selected_type)
            files.append(file_data)
        
        return files
    
    @staticmethod
    def create_folder_structure(user_id: str, depth: int = 3, width: int = 3) -> Dict[str, Any]:
        """Create nested folder structure"""
        
        def create_level(parent_id: Optional[str], current_depth: int) -> List[Dict[str, Any]]:
            if current_depth >= depth:
                return []
            
            folders = []
            for i in range(width):
                folder = FileFixtures.create_folder(
                    user_id=user_id,
                    parent_id=parent_id
                )
                
                # Add some files to each folder
                folder['files'] = [
                    FileFixtures.create_file(user_id=user_id)
                    for _ in range(random.randint(1, 5))
                ]
                
                # Recursively create subfolders
                folder['subfolders'] = create_level(folder['id'], current_depth + 1)
                
                folders.append(folder)
            
            return folders
        
        root_folders = create_level(None, 0)
        
        return {
            'user_id': user_id,
            'structure': root_folders,
            'total_folders': FileFixtures._count_folders(root_folders),
            'total_files': FileFixtures._count_files(root_folders)
        }
    
    @staticmethod
    def _count_folders(folders: List[Dict[str, Any]]) -> int:
        """Count total folders in structure"""
        count = len(folders)
        for folder in folders:
            count += FileFixtures._count_folders(folder.get('subfolders', []))
        return count
    
    @staticmethod
    def _count_files(folders: List[Dict[str, Any]]) -> int:
        """Count total files in structure"""
        count = 0
        for folder in folders:
            count += len(folder.get('files', []))
            count += FileFixtures._count_files(folder.get('subfolders', []))
        return count


class FileFactory:
    """Factory for creating complex file scenarios"""
    
    def __init__(self):
        self.files = []
        self.folders = []
        self.shares = []
        self.versions = []
    
    def create_shared_project(self, owner_id: str, collaborator_ids: List[str]) -> Dict[str, Any]:
        """Create a shared project with multiple files and collaborators"""
        
        # Create project folder
        project_folder = FileFixtures.create_folder(user_id=owner_id)
        self.folders.append(project_folder)
        
        # Create project files
        project_files = []
        for file_type in ['document', 'spreadsheet', 'presentation']:
            file_data = FileFixtures.create_file(user_id=owner_id, file_type=file_type)
            project_files.append(file_data)
            self.files.append(file_data)
            
            # Create versions for each file
            for version in range(1, random.randint(2, 5)):
                version_data = FileFixtures.create_file_version(file_data['id'], version)
                self.versions.append(version_data)
            
            # Share with collaborators
            for collaborator_id in collaborator_ids:
                share = FileFixtures.create_file_share(
                    file_data['id'],
                    owner_id,
                    shared_with=collaborator_id,
                    share_type='team'
                )
                self.shares.append(share)
        
        return {
            'folder': project_folder,
            'files': project_files,
            'collaborators': collaborator_ids,
            'owner': owner_id
        }
    
    def create_media_library(self, user_id: str, image_count: int = 20, video_count: int = 5) -> Dict[str, Any]:
        """Create media library with organized content"""
        
        # Create media folders
        photos_folder = FileFixtures.create_folder(user_id=user_id, name="Photos")
        videos_folder = FileFixtures.create_folder(user_id=user_id, name="Videos")
        
        self.folders.extend([photos_folder, videos_folder])
        
        # Create images
        images = []
        for _ in range(image_count):
            image = FileFixtures.create_file(user_id=user_id, file_type='image')
            images.append(image)
            self.files.append(image)
        
        # Create videos
        videos = []
        for _ in range(video_count):
            video = FileFixtures.create_file(user_id=user_id, file_type='video')
            videos.append(video)
            self.files.append(video)
        
        return {
            'photos_folder': photos_folder,
            'videos_folder': videos_folder,
            'images': images,
            'videos': videos,
            'total_size': sum(f['size'] for f in images + videos)
        }