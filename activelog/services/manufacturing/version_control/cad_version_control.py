#!/usr/bin/env python3
"""
ActiveLog.ai 3D Model Version Control System

Git-like version control for CAD files with geometric diff visualization and collaborative editing.
"""

import os
import json
import hashlib
import sqlite3
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import uuid
import zipfile
import tempfile

# 3D processing libraries (would be installed separately)
try:
    import open3d as o3d
    import numpy as np
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False
    print("Open3D not available - 3D processing features will be limited")

class FileFormat(Enum):
    STEP = "step"
    STL = "stl"
    IGES = "iges"
    OBJ = "obj"
    PLY = "ply"
    SOLIDWORKS = "sldprt"
    FUSION360 = "f3d"
    INVENTOR = "ipt"
    PARASOLID = "x_t"

class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    RENAMED = "renamed"

class MergeConflictType(Enum):
    GEOMETRIC = "geometric"
    FEATURE = "feature"
    MATERIAL = "material"
    DIMENSION = "dimension"
    ASSEMBLY = "assembly"

@dataclass
class CADFile:
    """CAD file metadata"""
    file_id: str
    filename: str
    file_format: FileFormat
    file_size: int
    file_hash: str
    version: int
    created_at: str
    modified_at: str
    author: str
    description: str = ""
    tags: List[str] = None
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.properties is None:
            self.properties = {}

@dataclass
class Commit:
    """Version control commit"""
    commit_id: str
    parent_commits: List[str]
    author: str
    timestamp: str
    message: str
    files_changed: List[str]
    changeset: Dict[str, ChangeType]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class Branch:
    """Version control branch"""
    branch_name: str
    head_commit: str
    created_at: str
    created_by: str
    description: str = ""
    is_protected: bool = False

@dataclass
class GeometricDiff:
    """Geometric differences between 3D models"""
    added_vertices: np.ndarray = None
    removed_vertices: np.ndarray = None
    modified_faces: List[int] = None
    volume_change: float = 0.0
    surface_area_change: float = 0.0
    bounding_box_change: Dict[str, float] = None
    center_of_mass_shift: np.ndarray = None
    
    def __post_init__(self):
        if self.modified_faces is None:
            self.modified_faces = []
        if self.bounding_box_change is None:
            self.bounding_box_change = {}

@dataclass
class MergeConflict:
    """Merge conflict information"""
    conflict_id: str
    conflict_type: MergeConflictType
    file_path: str
    base_version: str
    current_version: str
    incoming_version: str
    description: str
    geometric_diff: Optional[GeometricDiff] = None
    resolution_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.resolution_suggestions is None:
            self.resolution_suggestions = []

class CADDatabase:
    """SQLite database for CAD version control"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Repositories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS repositories (
                repo_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                default_branch TEXT DEFAULT 'main'
            )
        ''')
        
        # Branches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS branches (
                repo_id TEXT NOT NULL,
                branch_name TEXT NOT NULL,
                head_commit TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                description TEXT,
                is_protected BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (repo_id, branch_name),
                FOREIGN KEY (repo_id) REFERENCES repositories (repo_id)
            )
        ''')
        
        # Commits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commits (
                commit_id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                parent_commits TEXT,
                author TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                message TEXT NOT NULL,
                files_changed TEXT,
                changeset TEXT,
                metadata TEXT,
                FOREIGN KEY (repo_id) REFERENCES repositories (repo_id)
            )
        ''')
        
        # Files table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                commit_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_format TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                author TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                properties TEXT,
                FOREIGN KEY (repo_id) REFERENCES repositories (repo_id),
                FOREIGN KEY (commit_id) REFERENCES commits (commit_id)
            )
        ''')
        
        # Merge conflicts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS merge_conflicts (
                conflict_id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL,
                branch_name TEXT NOT NULL,
                conflict_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                base_version TEXT NOT NULL,
                current_version TEXT NOT NULL,
                incoming_version TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                resolved_by TEXT,
                resolution TEXT,
                FOREIGN KEY (repo_id) REFERENCES repositories (repo_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_commits_repo ON commits(repo_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_repo_commit ON files(repo_id, commit_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conflicts_repo ON merge_conflicts(repo_id)')
        
        conn.commit()
        conn.close()

class GeometryProcessor:
    """3D geometry processing and comparison"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_formats = [FileFormat.STL, FileFormat.OBJ, FileFormat.PLY]
    
    def load_mesh(self, file_path: str) -> Optional[o3d.geometry.TriangleMesh]:
        """Load 3D mesh from file"""
        if not OPEN3D_AVAILABLE:
            self.logger.warning("Open3D not available - cannot load mesh")
            return None
        
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.stl':
                mesh = o3d.io.read_triangle_mesh(file_path)
            elif file_ext == '.obj':
                mesh = o3d.io.read_triangle_mesh(file_path)
            elif file_ext == '.ply':
                mesh = o3d.io.read_triangle_mesh(file_path)
            else:
                self.logger.warning(f"Unsupported file format: {file_ext}")
                return None
            
            if len(mesh.vertices) == 0:
                self.logger.error(f"Failed to load mesh from {file_path}")
                return None
            
            return mesh
        
        except Exception as e:
            self.logger.error(f"Error loading mesh: {e}")
            return None
    
    def compute_geometric_diff(self, mesh1: o3d.geometry.TriangleMesh, 
                              mesh2: o3d.geometry.TriangleMesh) -> GeometricDiff:
        """Compute geometric differences between two meshes"""
        if not OPEN3D_AVAILABLE:
            return GeometricDiff()
        
        try:
            # Convert meshes to numpy arrays
            vertices1 = np.asarray(mesh1.vertices)
            vertices2 = np.asarray(mesh2.vertices)
            
            # Compute basic metrics
            volume1 = mesh1.get_volume() if mesh1.is_watertight() else 0
            volume2 = mesh2.get_volume() if mesh2.is_watertight() else 0
            
            surface_area1 = mesh1.get_surface_area()
            surface_area2 = mesh2.get_surface_area()
            
            # Bounding box comparison
            bbox1 = mesh1.get_axis_aligned_bounding_box()
            bbox2 = mesh2.get_axis_aligned_bounding_box()
            
            bbox_change = {
                'min_x': bbox2.min_bound[0] - bbox1.min_bound[0],
                'min_y': bbox2.min_bound[1] - bbox1.min_bound[1], 
                'min_z': bbox2.min_bound[2] - bbox1.min_bound[2],
                'max_x': bbox2.max_bound[0] - bbox1.max_bound[0],
                'max_y': bbox2.max_bound[1] - bbox1.max_bound[1],
                'max_z': bbox2.max_bound[2] - bbox1.max_bound[2]
            }
            
            # Center of mass shift
            center1 = mesh1.get_center()
            center2 = mesh2.get_center()
            com_shift = np.array(center2) - np.array(center1)
            
            # Find added/removed vertices using nearest neighbor
            added_vertices, removed_vertices = self._find_vertex_changes(vertices1, vertices2)
            
            return GeometricDiff(
                added_vertices=added_vertices,
                removed_vertices=removed_vertices,
                volume_change=volume2 - volume1,
                surface_area_change=surface_area2 - surface_area1,
                bounding_box_change=bbox_change,
                center_of_mass_shift=com_shift
            )
        
        except Exception as e:
            self.logger.error(f"Error computing geometric diff: {e}")
            return GeometricDiff()
    
    def _find_vertex_changes(self, vertices1: np.ndarray, 
                           vertices2: np.ndarray, threshold: float = 0.001) -> Tuple[np.ndarray, np.ndarray]:
        """Find added and removed vertices between two meshes"""
        if not OPEN3D_AVAILABLE:
            return np.array([]), np.array([])
        
        try:
            # Create point clouds
            pcd1 = o3d.geometry.PointCloud()
            pcd1.points = o3d.utility.Vector3dVector(vertices1)
            
            pcd2 = o3d.geometry.PointCloud()
            pcd2.points = o3d.utility.Vector3dVector(vertices2)
            
            # Build KDTree for nearest neighbor search
            pcd1_tree = o3d.geometry.KDTreeFlann(pcd1)
            pcd2_tree = o3d.geometry.KDTreeFlann(pcd2)
            
            # Find vertices in mesh2 not in mesh1 (added)
            added_vertices = []
            for vertex in vertices2:
                [k, idx, _] = pcd1_tree.search_knn_vector_3d(vertex, 1)
                if len(idx) > 0:
                    nearest_distance = np.linalg.norm(vertex - vertices1[idx[0]])
                    if nearest_distance > threshold:
                        added_vertices.append(vertex)
            
            # Find vertices in mesh1 not in mesh2 (removed)
            removed_vertices = []
            for vertex in vertices1:
                [k, idx, _] = pcd2_tree.search_knn_vector_3d(vertex, 1)
                if len(idx) > 0:
                    nearest_distance = np.linalg.norm(vertex - vertices2[idx[0]])
                    if nearest_distance > threshold:
                        removed_vertices.append(vertex)
            
            return np.array(added_vertices), np.array(removed_vertices)
        
        except Exception as e:
            self.logger.error(f"Error finding vertex changes: {e}")
            return np.array([]), np.array([])
    
    def visualize_diff(self, mesh1: o3d.geometry.TriangleMesh, 
                      mesh2: o3d.geometry.TriangleMesh, diff: GeometricDiff) -> Dict[str, Any]:
        """Create visualization data for geometric differences"""
        if not OPEN3D_AVAILABLE:
            return {}
        
        try:
            visualization_data = {
                'mesh1_vertices': len(mesh1.vertices),
                'mesh2_vertices': len(mesh2.vertices),
                'volume_change': diff.volume_change,
                'surface_area_change': diff.surface_area_change,
                'added_vertices_count': len(diff.added_vertices) if diff.added_vertices is not None else 0,
                'removed_vertices_count': len(diff.removed_vertices) if diff.removed_vertices is not None else 0,
                'center_of_mass_shift_magnitude': np.linalg.norm(diff.center_of_mass_shift) if diff.center_of_mass_shift is not None else 0
            }
            
            # Create colored point cloud for visualization
            if diff.added_vertices is not None and len(diff.added_vertices) > 0:
                added_pcd = o3d.geometry.PointCloud()
                added_pcd.points = o3d.utility.Vector3dVector(diff.added_vertices)
                added_pcd.colors = o3d.utility.Vector3dVector(np.tile([0, 1, 0], (len(diff.added_vertices), 1)))  # Green
                visualization_data['added_points'] = diff.added_vertices.tolist()
            
            if diff.removed_vertices is not None and len(diff.removed_vertices) > 0:
                removed_pcd = o3d.geometry.PointCloud()
                removed_pcd.points = o3d.utility.Vector3dVector(diff.removed_vertices)
                removed_pcd.colors = o3d.utility.Vector3dVector(np.tile([1, 0, 0], (len(diff.removed_vertices), 1)))  # Red
                visualization_data['removed_points'] = diff.removed_vertices.tolist()
            
            return visualization_data
        
        except Exception as e:
            self.logger.error(f"Error creating diff visualization: {e}")
            return {}

class CADRepository:
    """CAD file repository with version control"""
    
    def __init__(self, repo_path: str, database: CADDatabase):
        self.repo_path = Path(repo_path)
        self.database = database
        self.geometry_processor = GeometryProcessor()
        self.logger = logging.getLogger(__name__)
        
        # Create repository directories
        self.objects_dir = self.repo_path / "objects"
        self.refs_dir = self.repo_path / "refs"
        self.working_dir = self.repo_path / "working"
        
        for dir_path in [self.objects_dir, self.refs_dir, self.working_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def create_repository(self, repo_id: str, name: str, description: str, created_by: str) -> str:
        """Create new CAD repository"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO repositories (repo_id, name, description, created_at, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (repo_id, name, description, datetime.now().isoformat(), created_by))
        
        # Create main branch
        cursor.execute('''
            INSERT INTO branches (repo_id, branch_name, created_at, created_by, description)
            VALUES (?, 'main', ?, ?, 'Main development branch')
        ''', (repo_id, datetime.now().isoformat(), created_by))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Created repository: {name} ({repo_id})")
        return repo_id
    
    def add_file(self, repo_id: str, file_path: str, description: str = "", tags: List[str] = None) -> CADFile:
        """Add CAD file to repository"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_content = f.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Determine file format
        file_ext = Path(file_path).suffix.lower()
        file_format = self._detect_file_format(file_ext)
        
        # Create CAD file object
        cad_file = CADFile(
            file_id=str(uuid.uuid4()),
            filename=os.path.basename(file_path),
            file_format=file_format,
            file_size=len(file_content),
            file_hash=file_hash,
            version=1,
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            author="system",  # Would be set from authentication
            description=description,
            tags=tags or []
        )
        
        # Store file in objects directory
        object_path = self.objects_dir / file_hash
        with open(object_path, 'wb') as f:
            f.write(file_content)
        
        self.logger.info(f"Added file: {cad_file.filename} ({cad_file.file_id})")
        return cad_file
    
    def commit_changes(self, repo_id: str, branch_name: str, message: str, 
                      author: str, files: List[CADFile]) -> Commit:
        """Commit changes to repository"""
        commit_id = str(uuid.uuid4())
        
        # Get parent commit
        parent_commits = []
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT head_commit FROM branches WHERE repo_id = ? AND branch_name = ?', 
                      (repo_id, branch_name))
        result = cursor.fetchone()
        if result and result[0]:
            parent_commits = [result[0]]
        
        # Create commit
        commit = Commit(
            commit_id=commit_id,
            parent_commits=parent_commits,
            author=author,
            timestamp=datetime.now().isoformat(),
            message=message,
            files_changed=[f.file_id for f in files],
            changeset={f.file_id: ChangeType.MODIFIED for f in files}
        )
        
        # Store commit in database
        cursor.execute('''
            INSERT INTO commits 
            (commit_id, repo_id, parent_commits, author, timestamp, message, files_changed, changeset, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            commit.commit_id, repo_id, json.dumps(commit.parent_commits), commit.author,
            commit.timestamp, commit.message, json.dumps(commit.files_changed),
            json.dumps({k: v.value for k, v in commit.changeset.items()}),
            json.dumps(commit.metadata)
        ))
        
        # Store files
        for cad_file in files:
            cursor.execute('''
                INSERT INTO files 
                (file_id, repo_id, commit_id, filename, file_format, file_size, file_hash,
                 version, created_at, modified_at, author, description, tags, properties)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cad_file.file_id, repo_id, commit.commit_id, cad_file.filename,
                cad_file.file_format.value, cad_file.file_size, cad_file.file_hash,
                cad_file.version, cad_file.created_at, cad_file.modified_at,
                cad_file.author, cad_file.description, json.dumps(cad_file.tags),
                json.dumps(cad_file.properties)
            ))
        
        # Update branch head
        cursor.execute('UPDATE branches SET head_commit = ? WHERE repo_id = ? AND branch_name = ?',
                      (commit_id, repo_id, branch_name))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Created commit: {commit_id} in {repo_id}/{branch_name}")
        return commit
    
    def create_branch(self, repo_id: str, branch_name: str, from_commit: str, 
                     created_by: str, description: str = "") -> Branch:
        """Create new branch from commit"""
        branch = Branch(
            branch_name=branch_name,
            head_commit=from_commit,
            created_at=datetime.now().isoformat(),
            created_by=created_by,
            description=description
        )
        
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO branches (repo_id, branch_name, head_commit, created_at, created_by, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (repo_id, branch.branch_name, branch.head_commit, branch.created_at,
              branch.created_by, branch.description))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Created branch: {branch_name} in {repo_id}")
        return branch
    
    def merge_branches(self, repo_id: str, source_branch: str, target_branch: str, 
                      author: str) -> Union[Commit, List[MergeConflict]]:
        """Merge source branch into target branch"""
        # Get commits from both branches
        source_commit = self._get_branch_head(repo_id, source_branch)
        target_commit = self._get_branch_head(repo_id, target_branch)
        
        if not source_commit or not target_commit:
            raise ValueError("Source or target branch not found")
        
        # Find common ancestor
        common_ancestor = self._find_common_ancestor(repo_id, source_commit, target_commit)
        
        # Get files from all three commits
        base_files = self._get_commit_files(repo_id, common_ancestor) if common_ancestor else {}
        source_files = self._get_commit_files(repo_id, source_commit)
        target_files = self._get_commit_files(repo_id, target_commit)
        
        # Detect conflicts
        conflicts = self._detect_merge_conflicts(repo_id, target_branch, base_files, source_files, target_files)
        
        if conflicts:
            # Store conflicts in database
            self._store_merge_conflicts(repo_id, target_branch, conflicts)
            return conflicts
        
        # No conflicts - perform merge
        merged_files = self._merge_files(base_files, source_files, target_files)
        
        # Create merge commit
        merge_commit = Commit(
            commit_id=str(uuid.uuid4()),
            parent_commits=[source_commit, target_commit],
            author=author,
            timestamp=datetime.now().isoformat(),
            message=f"Merge branch '{source_branch}' into '{target_branch}'",
            files_changed=list(merged_files.keys()),
            changeset={f_id: ChangeType.MODIFIED for f_id in merged_files.keys()},
            metadata={"merge": True, "source_branch": source_branch}
        )
        
        return self._store_merge_commit(repo_id, target_branch, merge_commit, list(merged_files.values()))
    
    def get_geometric_diff(self, repo_id: str, commit1: str, commit2: str, filename: str) -> GeometricDiff:
        """Get geometric differences between file versions"""
        file1_path = self._get_file_from_commit(repo_id, commit1, filename)
        file2_path = self._get_file_from_commit(repo_id, commit2, filename)
        
        if not file1_path or not file2_path:
            return GeometricDiff()
        
        mesh1 = self.geometry_processor.load_mesh(file1_path)
        mesh2 = self.geometry_processor.load_mesh(file2_path)
        
        if mesh1 is None or mesh2 is None:
            return GeometricDiff()
        
        return self.geometry_processor.compute_geometric_diff(mesh1, mesh2)
    
    def _detect_file_format(self, file_ext: str) -> FileFormat:
        """Detect CAD file format from extension"""
        format_map = {
            '.step': FileFormat.STEP,
            '.stp': FileFormat.STEP,
            '.stl': FileFormat.STL,
            '.iges': FileFormat.IGES,
            '.igs': FileFormat.IGES,
            '.obj': FileFormat.OBJ,
            '.ply': FileFormat.PLY,
            '.sldprt': FileFormat.SOLIDWORKS,
            '.f3d': FileFormat.FUSION360,
            '.ipt': FileFormat.INVENTOR,
            '.x_t': FileFormat.PARASOLID
        }
        
        return format_map.get(file_ext.lower(), FileFormat.STL)
    
    def _get_branch_head(self, repo_id: str, branch_name: str) -> Optional[str]:
        """Get head commit of branch"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT head_commit FROM branches WHERE repo_id = ? AND branch_name = ?',
                      (repo_id, branch_name))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None
    
    def _find_common_ancestor(self, repo_id: str, commit1: str, commit2: str) -> Optional[str]:
        """Find common ancestor of two commits"""
        # Simplified implementation - would use proper graph traversal
        return None
    
    def _get_commit_files(self, repo_id: str, commit_id: str) -> Dict[str, CADFile]:
        """Get all files in a commit"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_id, filename, file_format, file_size, file_hash, version,
                   created_at, modified_at, author, description, tags, properties
            FROM files WHERE repo_id = ? AND commit_id = ?
        ''', (repo_id, commit_id))
        
        files = {}
        for row in cursor.fetchall():
            cad_file = CADFile(
                file_id=row[0], filename=row[1], file_format=FileFormat(row[2]),
                file_size=row[3], file_hash=row[4], version=row[5],
                created_at=row[6], modified_at=row[7], author=row[8],
                description=row[9], tags=json.loads(row[10]) if row[10] else [],
                properties=json.loads(row[11]) if row[11] else {}
            )
            files[row[1]] = cad_file  # Key by filename
        
        conn.close()
        return files
    
    def _detect_merge_conflicts(self, repo_id: str, branch_name: str, base_files: Dict[str, CADFile],
                               source_files: Dict[str, CADFile], target_files: Dict[str, CADFile]) -> List[MergeConflict]:
        """Detect merge conflicts between file versions"""
        conflicts = []
        
        # Find files that were modified in both branches
        all_filenames = set(base_files.keys()) | set(source_files.keys()) | set(target_files.keys())
        
        for filename in all_filenames:
            base_file = base_files.get(filename)
            source_file = source_files.get(filename)
            target_file = target_files.get(filename)
            
            # Check for conflicts
            if base_file and source_file and target_file:
                # All three versions exist - check for concurrent modifications
                if (source_file.file_hash != base_file.file_hash and 
                    target_file.file_hash != base_file.file_hash and
                    source_file.file_hash != target_file.file_hash):
                    
                    # Geometric conflict analysis
                    geometric_diff = None
                    if (source_file.file_format in [FileFormat.STL, FileFormat.OBJ, FileFormat.PLY] and
                        target_file.file_format == source_file.file_format):
                        try:
                            source_mesh = self.geometry_processor.load_mesh(
                                str(self.objects_dir / source_file.file_hash)
                            )
                            target_mesh = self.geometry_processor.load_mesh(
                                str(self.objects_dir / target_file.file_hash)
                            )
                            if source_mesh and target_mesh:
                                geometric_diff = self.geometry_processor.compute_geometric_diff(
                                    source_mesh, target_mesh
                                )
                        except Exception as e:
                            self.logger.error(f"Error analyzing geometric conflict: {e}")
                    
                    conflict = MergeConflict(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type=MergeConflictType.GEOMETRIC,
                        file_path=filename,
                        base_version=base_file.file_hash,
                        current_version=target_file.file_hash,
                        incoming_version=source_file.file_hash,
                        description=f"Concurrent modifications to {filename}",
                        geometric_diff=geometric_diff,
                        resolution_suggestions=[
                            "Manual review required",
                            "Compare geometric differences",
                            "Consider feature-based merge"
                        ]
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _store_merge_conflicts(self, repo_id: str, branch_name: str, conflicts: List[MergeConflict]):
        """Store merge conflicts in database"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        for conflict in conflicts:
            cursor.execute('''
                INSERT INTO merge_conflicts 
                (conflict_id, repo_id, branch_name, conflict_type, file_path,
                 base_version, current_version, incoming_version, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                conflict.conflict_id, repo_id, branch_name, conflict.conflict_type.value,
                conflict.file_path, conflict.base_version, conflict.current_version,
                conflict.incoming_version, conflict.description, datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def _merge_files(self, base_files: Dict[str, CADFile], source_files: Dict[str, CADFile],
                    target_files: Dict[str, CADFile]) -> Dict[str, CADFile]:
        """Merge files from different branches (no conflicts)"""
        merged = {}
        
        # Start with target files
        merged.update(target_files)
        
        # Add/update with source files that don't conflict
        for filename, source_file in source_files.items():
            if filename not in target_files:
                # File only in source - add it
                merged[filename] = source_file
            elif filename in base_files:
                # File exists in both - use source if target unchanged
                base_file = base_files[filename]
                target_file = target_files[filename]
                
                if target_file.file_hash == base_file.file_hash:
                    # Target unchanged, use source
                    merged[filename] = source_file
                # Otherwise keep target (already in merged)
        
        return merged
    
    def _store_merge_commit(self, repo_id: str, branch_name: str, commit: Commit, files: List[CADFile]) -> Commit:
        """Store merge commit and update branch"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        # Store commit
        cursor.execute('''
            INSERT INTO commits 
            (commit_id, repo_id, parent_commits, author, timestamp, message, files_changed, changeset, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            commit.commit_id, repo_id, json.dumps(commit.parent_commits), commit.author,
            commit.timestamp, commit.message, json.dumps(commit.files_changed),
            json.dumps({k: v.value for k, v in commit.changeset.items()}),
            json.dumps(commit.metadata)
        ))
        
        # Store files
        for cad_file in files:
            cursor.execute('''
                INSERT INTO files 
                (file_id, repo_id, commit_id, filename, file_format, file_size, file_hash,
                 version, created_at, modified_at, author, description, tags, properties)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cad_file.file_id, repo_id, commit.commit_id, cad_file.filename,
                cad_file.file_format.value, cad_file.file_size, cad_file.file_hash,
                cad_file.version, cad_file.created_at, cad_file.modified_at,
                cad_file.author, cad_file.description, json.dumps(cad_file.tags),
                json.dumps(cad_file.properties)
            ))
        
        # Update branch head
        cursor.execute('UPDATE branches SET head_commit = ? WHERE repo_id = ? AND branch_name = ?',
                      (commit.commit_id, repo_id, branch_name))
        
        conn.commit()
        conn.close()
        
        return commit
    
    def _get_file_from_commit(self, repo_id: str, commit_id: str, filename: str) -> Optional[str]:
        """Get file path from commit"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_hash FROM files WHERE repo_id = ? AND commit_id = ? AND filename = ?',
                      (repo_id, commit_id, filename))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            object_path = self.objects_dir / result[0]
            if object_path.exists():
                return str(object_path)
        
        return None

async def main():
    """Example usage of CAD version control system"""
    # Initialize database
    db = CADDatabase("cad_version_control.db")
    
    # Create repository
    repo = CADRepository("./test_repo", db)
    repo_id = repo.create_repository(
        str(uuid.uuid4()), 
        "Test CAD Project", 
        "Testing CAD version control",
        "engineer@company.com"
    )
    
    print(f"Created repository: {repo_id}")
    
    # Example workflow would continue here...
    # - Add CAD files
    # - Create commits
    # - Create branches
    # - Merge changes
    # - Analyze geometric diffs

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())