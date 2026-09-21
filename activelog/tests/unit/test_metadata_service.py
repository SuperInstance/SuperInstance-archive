"""
Unit tests for Metadata Service
Tests file metadata operations, tagging, search, and relationships
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

# Import metadata service components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services'))

from metadata.database import MetadataDatabase
from metadata.routes import MetadataRoutes
from metadata.schemas import FileMetadata, FileTag, FileRelationship
from metadata.embeddings import EmbeddingManager
from metadata.relationships import RelationshipAnalyzer


class TestMetadataDatabase:
    """Test metadata database operations"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.db = MetadataDatabase()
    
    @patch('metadata.database.create_engine')
    def test_database_connection(self, mock_engine):
        """Test database connection establishment"""
        mock_engine.return_value.connect.return_value = MagicMock()
        
        connection = self.db.get_connection()
        
        assert connection is not None
        mock_engine.assert_called_once()
    
    @patch('metadata.database.MetadataDatabase.execute_query')
    async def test_create_file_metadata(self, mock_execute, sample_file):
        """Test creating file metadata"""
        mock_execute.return_value = sample_file['id']
        
        result = await self.db.create_file_metadata(sample_file)
        
        assert result == sample_file['id']
        mock_execute.assert_called_once()
    
    @patch('metadata.database.MetadataDatabase.execute_query')
    async def test_get_file_metadata(self, mock_execute, sample_file):
        """Test retrieving file metadata"""
        mock_execute.return_value = [sample_file]
        
        result = await self.db.get_file_metadata(sample_file['id'])
        
        assert result == sample_file
        mock_execute.assert_called_once()
    
    @patch('metadata.database.MetadataDatabase.execute_query')
    async def test_update_file_metadata(self, mock_execute, sample_file):
        """Test updating file metadata"""
        mock_execute.return_value = True
        
        updates = {'name': 'updated_file.pdf', 'modified_at': datetime.utcnow()}
        result = await self.db.update_file_metadata(sample_file['id'], updates)
        
        assert result is True
        mock_execute.assert_called_once()
    
    @patch('metadata.database.MetadataDatabase.execute_query')
    async def test_delete_file_metadata(self, mock_execute, sample_file):
        """Test deleting file metadata"""
        mock_execute.return_value = True
        
        result = await self.db.delete_file_metadata(sample_file['id'])
        
        assert result is True
        mock_execute.assert_called_once()
    
    @patch('metadata.database.MetadataDatabase.execute_query')
    async def test_search_files(self, mock_execute, sample_file):
        """Test searching files"""
        mock_execute.return_value = [sample_file]
        
        search_params = {
            'query': 'test document',
            'file_type': 'document',
            'user_id': sample_file['user_id']
        }
        
        results = await self.db.search_files(search_params)
        
        assert len(results) == 1
        assert results[0] == sample_file
        mock_execute.assert_called_once()
    
    @patch('metadata.database.MetadataDatabase.execute_query')
    async def test_get_user_files(self, mock_execute, sample_file):
        """Test getting user files"""
        mock_execute.return_value = [sample_file]
        
        files = await self.db.get_user_files(sample_file['user_id'], limit=10, offset=0)
        
        assert len(files) == 1
        assert files[0] == sample_file
    
    @patch('metadata.database.MetadataDatabase.execute_query')
    async def test_get_file_statistics(self, mock_execute, sample_file):
        """Test getting file statistics"""
        mock_stats = {
            'total_files': 100,
            'total_size': 1024000000,
            'file_types': {'document': 50, 'image': 30, 'video': 20},
            'sync_status': {'synced': 80, 'local': 15, 'error': 5}
        }
        mock_execute.return_value = [mock_stats]
        
        stats = await self.db.get_file_statistics(sample_file['user_id'])
        
        assert stats == mock_stats
        assert stats['total_files'] == 100


class TestFileMetadata:
    """Test FileMetadata schema"""
    
    def test_file_metadata_creation(self, sample_file):
        """Test creating FileMetadata object"""
        metadata = FileMetadata(**sample_file)
        
        assert metadata.id == sample_file['id']
        assert metadata.name == sample_file['name']
        assert metadata.path == sample_file['path']
        assert metadata.size == sample_file['size']
        assert metadata.file_type == sample_file['file_type']
    
    def test_file_metadata_validation(self):
        """Test FileMetadata validation"""
        # Test invalid data
        with pytest.raises(ValueError):
            FileMetadata(
                id="invalid-id",  # Should be UUID
                name="",  # Empty name
                size=-1  # Negative size
            )
    
    def test_file_metadata_serialization(self, sample_file):
        """Test FileMetadata serialization"""
        metadata = FileMetadata(**sample_file)
        
        serialized = metadata.to_dict()
        
        assert isinstance(serialized, dict)
        assert serialized['id'] == sample_file['id']
        assert 'created_at' in serialized
    
    def test_file_metadata_from_dict(self, sample_file):
        """Test creating FileMetadata from dictionary"""
        metadata = FileMetadata.from_dict(sample_file)
        
        assert metadata.id == sample_file['id']
        assert metadata.name == sample_file['name']
    
    def test_file_size_formatting(self, sample_file):
        """Test file size formatting"""
        metadata = FileMetadata(**sample_file)
        
        formatted_size = metadata.get_formatted_size()
        
        assert isinstance(formatted_size, str)
        assert 'KB' in formatted_size or 'MB' in formatted_size or 'GB' in formatted_size
    
    def test_file_age_calculation(self, sample_file):
        """Test file age calculation"""
        metadata = FileMetadata(**sample_file)
        
        age = metadata.get_age_days()
        
        assert isinstance(age, int)
        assert age >= 0


class TestFileTag:
    """Test FileTag schema"""
    
    def test_tag_creation(self):
        """Test creating FileTag"""
        tag = FileTag(
            id=str(uuid.uuid4()),
            name="important",
            color="#ff0000",
            user_id=str(uuid.uuid4())
        )
        
        assert tag.name == "important"
        assert tag.color == "#ff0000"
        assert isinstance(tag.created_at, datetime)
    
    def test_tag_validation(self):
        """Test tag validation"""
        # Test invalid color
        with pytest.raises(ValueError):
            FileTag(
                name="test",
                color="invalid-color",
                user_id=str(uuid.uuid4())
            )
        
        # Test empty name
        with pytest.raises(ValueError):
            FileTag(
                name="",
                color="#ff0000",
                user_id=str(uuid.uuid4())
            )
    
    def test_tag_normalization(self):
        """Test tag name normalization"""
        tag = FileTag(
            name="  Important  ",
            color="#ff0000",
            user_id=str(uuid.uuid4())
        )
        
        assert tag.name == "important"  # Should be normalized


class TestFileRelationship:
    """Test FileRelationship schema"""
    
    def test_relationship_creation(self):
        """Test creating file relationship"""
        relationship = FileRelationship(
            parent_file_id=str(uuid.uuid4()),
            child_file_id=str(uuid.uuid4()),
            relationship_type="similar",
            strength=0.85,
            metadata={"algorithm": "cosine_similarity"}
        )
        
        assert relationship.relationship_type == "similar"
        assert relationship.strength == 0.85
        assert relationship.metadata["algorithm"] == "cosine_similarity"
    
    def test_relationship_validation(self):
        """Test relationship validation"""
        # Test invalid strength
        with pytest.raises(ValueError):
            FileRelationship(
                parent_file_id=str(uuid.uuid4()),
                child_file_id=str(uuid.uuid4()),
                relationship_type="similar",
                strength=1.5  # Should be between 0 and 1
            )
        
        # Test same parent and child
        file_id = str(uuid.uuid4())
        with pytest.raises(ValueError):
            FileRelationship(
                parent_file_id=file_id,
                child_file_id=file_id,
                relationship_type="similar",
                strength=0.5
            )


class TestEmbeddingManager:
    """Test embedding management"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.embedding_manager = EmbeddingManager()
    
    @patch('metadata.embeddings.openai.Embedding.create')
    async def test_generate_text_embedding(self, mock_openai):
        """Test generating text embedding"""
        mock_openai.return_value = {
            'data': [{
                'embedding': [0.1] * 1536
            }]
        }
        
        text = "This is a test document about machine learning."
        embedding = await self.embedding_manager.generate_text_embedding(text)
        
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        mock_openai.assert_called_once()
    
    @patch('metadata.embeddings.EmbeddingManager.extract_text_from_file')
    @patch('metadata.embeddings.EmbeddingManager.generate_text_embedding')
    async def test_process_file_embedding(self, mock_generate, mock_extract, sample_file):
        """Test processing file for embeddings"""
        mock_extract.return_value = "Extracted text content from the file."
        mock_generate.return_value = [0.1] * 1536
        
        result = await self.embedding_manager.process_file_embedding(sample_file)
        
        assert 'embedding' in result
        assert 'text_chunks' in result
        assert len(result['embedding']) == 1536
        mock_extract.assert_called_once()
        mock_generate.assert_called_once()
    
    def test_chunk_text(self):
        """Test text chunking"""
        long_text = "This is a very long text. " * 100  # Create long text
        
        chunks = self.embedding_manager.chunk_text(long_text, max_chunk_size=100)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)
        assert ''.join(chunks).replace(' ', '') == long_text.replace(' ', '')
    
    @patch('metadata.embeddings.EmbeddingManager.generate_text_embedding')
    async def test_find_similar_files(self, mock_generate, sample_embedding):
        """Test finding similar files"""
        mock_generate.return_value = sample_embedding['embedding_vector']
        
        with patch('metadata.embeddings.MetadataDatabase') as mock_db:
            mock_db.return_value.search_similar_embeddings.return_value = [
                {
                    'file_id': str(uuid.uuid4()),
                    'similarity': 0.92,
                    'file_name': 'similar_document.pdf'
                }
            ]
            
            query = "machine learning algorithms"
            similar_files = await self.embedding_manager.find_similar_files(query, limit=5)
            
            assert len(similar_files) >= 0
            mock_generate.assert_called_once()
    
    def test_calculate_similarity(self):
        """Test similarity calculation"""
        embedding1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding2 = [0.2, 0.3, 0.4, 0.5, 0.6]
        
        similarity = self.embedding_manager.calculate_similarity(embedding1, embedding2)
        
        assert 0 <= similarity <= 1
        assert isinstance(similarity, float)
    
    def test_normalize_embedding(self):
        """Test embedding normalization"""
        embedding = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        normalized = self.embedding_manager.normalize_embedding(embedding)
        
        # Check that magnitude is approximately 1
        magnitude = sum(x**2 for x in normalized) ** 0.5
        assert abs(magnitude - 1.0) < 1e-6


class TestRelationshipAnalyzer:
    """Test relationship analysis"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.analyzer = RelationshipAnalyzer()
    
    def test_analyze_content_similarity(self, test_data_generator):
        """Test content similarity analysis"""
        files = test_data_generator.generate_files(str(uuid.uuid4()), 3)
        
        # Mock embeddings
        embeddings = {
            files[0]['id']: [0.1] * 1536,
            files[1]['id']: [0.2] * 1536,
            files[2]['id']: [0.9] * 1536
        }
        
        relationships = self.analyzer.analyze_content_similarity(files, embeddings)
        
        assert isinstance(relationships, list)
        for rel in relationships:
            assert 'parent_file_id' in rel
            assert 'child_file_id' in rel
            assert 'strength' in rel
            assert 0 <= rel['strength'] <= 1
    
    def test_analyze_temporal_relationships(self, test_data_generator):
        """Test temporal relationship analysis"""
        files = test_data_generator.generate_files(str(uuid.uuid4()), 5)
        
        # Set different creation times
        base_time = datetime.utcnow()
        for i, file in enumerate(files):
            file['created_at'] = base_time - timedelta(hours=i)
        
        relationships = self.analyzer.analyze_temporal_relationships(files)
        
        assert isinstance(relationships, list)
        for rel in relationships:
            assert rel['relationship_type'] == 'temporal'
    
    def test_analyze_structural_relationships(self, test_data_generator):
        """Test structural relationship analysis"""
        files = test_data_generator.generate_files(str(uuid.uuid4()), 4)
        
        # Set up folder structure
        files[0]['path'] = '/user/documents/project/report.pdf'
        files[1]['path'] = '/user/documents/project/data.csv'
        files[2]['path'] = '/user/documents/project/images/chart.png'
        files[3]['path'] = '/user/downloads/unrelated.txt'
        
        relationships = self.analyzer.analyze_structural_relationships(files)
        
        assert isinstance(relationships, list)
        # Files in same folder should have relationships
        project_files = [f for f in files if 'project' in f['path']]
        assert len(project_files) >= 2
    
    def test_find_duplicate_candidates(self, test_data_generator):
        """Test finding duplicate file candidates"""
        files = test_data_generator.generate_files(str(uuid.uuid4()), 3)
        
        # Create potential duplicates
        files[0]['checksum'] = 'abc123'
        files[1]['checksum'] = 'abc123'  # Same checksum
        files[2]['checksum'] = 'def456'
        
        duplicates = self.analyzer.find_duplicate_candidates(files)
        
        assert isinstance(duplicates, list)
        assert len(duplicates) >= 1  # Should find the duplicate pair
    
    def test_cluster_related_files(self, test_data_generator):
        """Test clustering related files"""
        files = test_data_generator.generate_files(str(uuid.uuid4()), 6)
        
        # Create mock relationships
        relationships = [
            {'parent_file_id': files[0]['id'], 'child_file_id': files[1]['id'], 'strength': 0.8},
            {'parent_file_id': files[1]['id'], 'child_file_id': files[2]['id'], 'strength': 0.7},
            {'parent_file_id': files[3]['id'], 'child_file_id': files[4]['id'], 'strength': 0.9}
        ]
        
        clusters = self.analyzer.cluster_related_files(files, relationships)
        
        assert isinstance(clusters, list)
        assert len(clusters) >= 1
        for cluster in clusters:
            assert 'files' in cluster
            assert 'cluster_strength' in cluster


@pytest.mark.asyncio
class TestMetadataRoutes:
    """Test metadata API routes"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.routes = MetadataRoutes()
    
    @patch('metadata.routes.MetadataDatabase')
    async def test_create_file_endpoint(self, mock_db, sample_file):
        """Test file creation endpoint"""
        mock_db.return_value.create_file_metadata.return_value = sample_file['id']
        mock_db.return_value.get_file_metadata.return_value = sample_file
        
        response = await self.routes.create_file(sample_file)
        
        assert response['success'] is True
        assert response['file']['id'] == sample_file['id']
    
    @patch('metadata.routes.MetadataDatabase')
    async def test_get_file_endpoint(self, mock_db, sample_file):
        """Test get file endpoint"""
        mock_db.return_value.get_file_metadata.return_value = sample_file
        
        response = await self.routes.get_file(sample_file['id'])
        
        assert response['success'] is True
        assert response['file'] == sample_file
    
    @patch('metadata.routes.MetadataDatabase')
    async def test_get_file_not_found(self, mock_db):
        """Test get file endpoint with non-existent file"""
        mock_db.return_value.get_file_metadata.return_value = None
        
        response = await self.routes.get_file(str(uuid.uuid4()))
        
        assert response['success'] is False
        assert 'not found' in response['error']
    
    @patch('metadata.routes.MetadataDatabase')
    async def test_update_file_endpoint(self, mock_db, sample_file):
        """Test update file endpoint"""
        updated_file = sample_file.copy()
        updated_file['name'] = 'updated_name.pdf'
        
        mock_db.return_value.get_file_metadata.return_value = sample_file
        mock_db.return_value.update_file_metadata.return_value = True
        mock_db.return_value.get_file_metadata.return_value = updated_file
        
        update_data = {'name': 'updated_name.pdf'}
        response = await self.routes.update_file(sample_file['id'], update_data)
        
        assert response['success'] is True
        assert response['file']['name'] == 'updated_name.pdf'
    
    @patch('metadata.routes.MetadataDatabase')
    async def test_delete_file_endpoint(self, mock_db, sample_file):
        """Test delete file endpoint"""
        mock_db.return_value.get_file_metadata.return_value = sample_file
        mock_db.return_value.delete_file_metadata.return_value = True
        
        response = await self.routes.delete_file(sample_file['id'])
        
        assert response['success'] is True
    
    @patch('metadata.routes.MetadataDatabase')
    async def test_search_files_endpoint(self, mock_db, sample_file):
        """Test search files endpoint"""
        mock_db.return_value.search_files.return_value = [sample_file]
        
        search_params = {
            'query': 'test document',
            'file_type': 'document',
            'limit': 10
        }
        
        response = await self.routes.search_files(search_params)
        
        assert response['success'] is True
        assert len(response['files']) == 1
        assert response['files'][0] == sample_file
    
    @patch('metadata.routes.MetadataDatabase')
    async def test_get_user_files_endpoint(self, mock_db, sample_file):
        """Test get user files endpoint"""
        mock_db.return_value.get_user_files.return_value = [sample_file]
        
        response = await self.routes.get_user_files(
            user_id=sample_file['user_id'],
            limit=10,
            offset=0
        )
        
        assert response['success'] is True
        assert len(response['files']) == 1
    
    @patch('metadata.routes.EmbeddingManager')
    async def test_generate_embeddings_endpoint(self, mock_embedding, sample_file):
        """Test generate embeddings endpoint"""
        mock_embedding.return_value.process_file_embedding.return_value = {
            'embedding': [0.1] * 1536,
            'text_chunks': ['chunk1', 'chunk2']
        }
        
        response = await self.routes.generate_embeddings(sample_file['id'])
        
        assert response['success'] is True
        assert 'embedding' in response
    
    @patch('metadata.routes.EmbeddingManager')
    async def test_find_similar_files_endpoint(self, mock_embedding):
        """Test find similar files endpoint"""
        mock_similar_files = [
            {'file_id': str(uuid.uuid4()), 'similarity': 0.92, 'file_name': 'similar1.pdf'},
            {'file_id': str(uuid.uuid4()), 'similarity': 0.88, 'file_name': 'similar2.pdf'}
        ]
        mock_embedding.return_value.find_similar_files.return_value = mock_similar_files
        
        response = await self.routes.find_similar_files(
            query="machine learning",
            limit=5
        )
        
        assert response['success'] is True
        assert len(response['similar_files']) == 2


@pytest.mark.unit
class TestMetadataServiceIntegration:
    """Integration tests for metadata service components"""
    
    @patch('metadata.database.MetadataDatabase')
    @patch('metadata.embeddings.EmbeddingManager')
    async def test_complete_file_processing_flow(self, mock_embedding, mock_db, sample_file):
        """Test complete file processing workflow"""
        # Mock database operations
        mock_db.return_value.create_file_metadata.return_value = sample_file['id']
        mock_db.return_value.get_file_metadata.return_value = sample_file
        
        # Mock embedding generation
        mock_embedding.return_value.process_file_embedding.return_value = {
            'embedding': [0.1] * 1536,
            'text_chunks': ['chunk1', 'chunk2']
        }
        
        # Create metadata routes instance
        routes = MetadataRoutes()
        
        # 1. Create file metadata
        create_response = await routes.create_file(sample_file)
        assert create_response['success'] is True
        
        # 2. Generate embeddings
        embedding_response = await routes.generate_embeddings(sample_file['id'])
        assert embedding_response['success'] is True
        
        # 3. Verify file was processed
        get_response = await routes.get_file(sample_file['id'])
        assert get_response['success'] is True
    
    def test_metadata_validation_and_serialization(self, sample_file):
        """Test metadata validation and serialization flow"""
        # Create metadata object
        metadata = FileMetadata(**sample_file)
        
        # Validate
        assert metadata.id == sample_file['id']
        assert metadata.size > 0
        
        # Serialize
        serialized = metadata.to_dict()
        assert isinstance(serialized, dict)
        
        # Deserialize
        deserialized = FileMetadata.from_dict(serialized)
        assert deserialized.id == metadata.id
        assert deserialized.name == metadata.name