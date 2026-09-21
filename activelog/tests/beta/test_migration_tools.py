"""
Integration tests for migration tools
Tests data migration between platforms and legacy system imports
"""

import pytest
import asyncio
import uuid
import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
import httpx
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import shutil
import sqlite3
import zipfile

# Test configuration
MIGRATION_TOOLKIT_URL = "http://localhost:8006"
API_GATEWAY_URL = "http://localhost:8000"
DATA_EXPORT_URL = "http://localhost:8007"
IMPORT_SERVICE_URL = "http://localhost:8008"


class TestMigrationTools:
    """Test comprehensive data migration and import/export functionality"""
    
    @pytest.fixture
    def sample_legacy_d20_data(self):
        """Sample data from legacy d20 campaign management tools"""
        return {
            'campaigns': [
                {
                    'id': 'legacy_campaign_001',
                    'name': 'The Shattered Crown',
                    'system': 'D&D 3.5',
                    'dm_name': 'John Smith',
                    'created_date': '2019-03-15',
                    'last_session': '2021-12-20',
                    'level_range': '1-12',
                    'setting': 'Forgotten Realms'
                }
            ],
            'characters': [
                {
                    'id': 'char_001',
                    'campaign_id': 'legacy_campaign_001',
                    'name': 'Thorin Ironbeard',
                    'class': 'Fighter',
                    'level': 8,
                    'race': 'Dwarf',
                    'player_name': 'Alice Johnson',
                    'stats': {
                        'strength': 18,
                        'dexterity': 12,
                        'constitution': 16,
                        'intelligence': 10,
                        'wisdom': 14,
                        'charisma': 8
                    },
                    'equipment': ['Warhammer +1', 'Chain Mail', 'Shield +1']
                }
            ],
            'sessions': [
                {
                    'id': 'session_001',
                    'campaign_id': 'legacy_campaign_001',
                    'date': '2021-12-20',
                    'duration': 240,
                    'notes': 'Party defeated the goblin king and rescued the villagers',
                    'experience_awarded': 1200
                }
            ]
        }
    
    @pytest.fixture
    def sample_maker_portfolio_data(self):
        """Sample maker portfolio data for import testing"""
        return {
            'maker_profile': {
                'business_name': 'Legacy Crafts Studio',
                'owner_name': 'Sarah Martinez',
                'specialties': ['woodworking', 'laser_engraving'],
                'years_active': 5,
                'location': 'Portland, OR'
            },
            'projects': [
                {
                    'title': 'Custom Gaming Table',
                    'description': 'Oak gaming table with felt surface and cup holders',
                    'materials': ['oak_wood', 'felt', 'metal_hardware'],
                    'completion_time': '3 weeks',
                    'price': 850.00,
                    'images': ['table_main.jpg', 'table_detail1.jpg'],
                    'client_feedback': 'Excellent quality, perfect for our game nights!'
                },
                {
                    'title': 'Engraved Dice Boxes',
                    'description': 'Set of personalized dice storage boxes',
                    'materials': ['walnut_wood', 'foam_padding'],
                    'completion_time': '1 week',
                    'price': 45.00,
                    'quantity': 6
                }
            ]
        }
    
    @pytest.fixture
    def authenticated_admin_session(self):
        """Admin user session for migration operations"""
        return {
            'user_id': str(uuid.uuid4()),
            'role': 'admin',
            'token': 'admin.migration.token',
            'headers': {'Authorization': 'Bearer admin.migration.token'}
        }

    @pytest.fixture
    async def temp_data_files(self, sample_legacy_d20_data, sample_maker_portfolio_data):
        """Create temporary data files for testing"""
        temp_dir = tempfile.mkdtemp(prefix="migration_test_")
        
        # Create CSV file for D&D data
        csv_file = os.path.join(temp_dir, 'legacy_campaigns.csv')
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'name', 'system', 'dm_name', 'created_date'])
            writer.writeheader()
            for campaign in sample_legacy_d20_data['campaigns']:
                writer.writerow({
                    'id': campaign['id'],
                    'name': campaign['name'],
                    'system': campaign['system'],
                    'dm_name': campaign['dm_name'],
                    'created_date': campaign['created_date']
                })
        
        # Create JSON file for maker data
        json_file = os.path.join(temp_dir, 'maker_portfolio.json')
        with open(json_file, 'w') as f:
            json.dump(sample_maker_portfolio_data, f, indent=2)
        
        # Create XML file for character data
        xml_file = os.path.join(temp_dir, 'characters.xml')
        root = ET.Element('characters')
        for char in sample_legacy_d20_data['characters']:
            char_elem = ET.SubElement(root, 'character')
            for key, value in char.items():
                if key != 'stats' and key != 'equipment':
                    ET.SubElement(char_elem, key).text = str(value)
                elif key == 'stats':
                    stats_elem = ET.SubElement(char_elem, 'stats')
                    for stat, val in value.items():
                        ET.SubElement(stats_elem, stat).text = str(val)
        
        tree = ET.ElementTree(root)
        tree.write(xml_file)
        
        # Create SQLite database file
        db_file = os.path.join(temp_dir, 'legacy_data.db')
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                campaign_id TEXT,
                date TEXT,
                duration INTEGER,
                notes TEXT,
                experience_awarded INTEGER
            )
        ''')
        
        for session in sample_legacy_d20_data['sessions']:
            cursor.execute('''
                INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['id'], session['campaign_id'], session['date'], 
                  session['duration'], session['notes'], session['experience_awarded']))
        
        conn.commit()
        conn.close()
        
        yield {
            'temp_dir': temp_dir,
            'csv_file': csv_file,
            'json_file': json_file,
            'xml_file': xml_file,
            'db_file': db_file
        }
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_d20_campaign_migration(self, temp_data_files, authenticated_admin_session):
        """Test migrating legacy D&D campaign data to DMLog"""
        
        async with httpx.AsyncClient() as client:
            # Step 1: Upload legacy campaign data
            with open(temp_data_files['csv_file'], 'rb') as f:
                files = {'file': ('legacy_campaigns.csv', f, 'text/csv')}
                data = {
                    'source_system': 'd20_pro',
                    'target_platform': 'dmlog',
                    'data_type': 'campaigns'
                }
                
                upload_response = await client.post(
                    f"{MIGRATION_TOOLKIT_URL}/api/import/upload",
                    files=files,
                    data=data,
                    headers=authenticated_admin_session['headers']
                )
                assert upload_response.status_code == 201
                
                import_job_id = upload_response.json()['job_id']
                assert 'preview' in upload_response.json()
                assert len(upload_response.json()['preview']['campaigns']) == 1
            
            # Step 2: Validate and process the import
            validation_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/import/{import_job_id}/validate",
                headers=authenticated_admin_session['headers']
            )
            assert validation_response.status_code == 200
            
            validation_data = validation_response.json()
            assert validation_data['valid'] == True
            assert validation_data['warnings'] == []
            assert validation_data['estimated_records'] == 1
            
            # Step 3: Execute the migration
            migration_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/import/{import_job_id}/execute",
                json={'confirm_import': True},
                headers=authenticated_admin_session['headers']
            )
            assert migration_response.status_code == 202
            
            # Step 4: Monitor migration progress
            for _ in range(10):  # Poll for completion
                status_response = await client.get(
                    f"{MIGRATION_TOOLKIT_URL}/api/import/{import_job_id}/status",
                    headers=authenticated_admin_session['headers']
                )
                status_data = status_response.json()
                
                if status_data['status'] == 'completed':
                    break
                elif status_data['status'] == 'failed':
                    pytest.fail(f"Migration failed: {status_data.get('error')}")
                
                await asyncio.sleep(1)
            
            assert status_data['status'] == 'completed'
            assert status_data['records_processed'] == 1
            assert status_data['records_success'] == 1
            
            # Step 5: Verify campaign was created in DMLog
            dmlog_response = await client.get(
                f"http://localhost:8300/api/campaigns/search",
                params={'name': 'The Shattered Crown'},
                headers=authenticated_admin_session['headers']
            )
            assert dmlog_response.status_code == 200
            
            campaigns = dmlog_response.json()['campaigns']
            assert len(campaigns) == 1
            
            migrated_campaign = campaigns[0]
            assert migrated_campaign['name'] == 'The Shattered Crown'
            assert migrated_campaign['system'] == 'D&D 3.5'
            assert migrated_campaign['migration_source'] == 'd20_pro'

    @pytest.mark.asyncio
    async def test_character_data_xml_migration(self, temp_data_files, authenticated_admin_session):
        """Test migrating character data from XML format"""
        
        async with httpx.AsyncClient() as client:
            # Upload XML character data
            with open(temp_data_files['xml_file'], 'rb') as f:
                files = {'file': ('characters.xml', f, 'application/xml')}
                data = {
                    'source_system': 'herolab',
                    'target_platform': 'dmlog',
                    'data_type': 'characters'
                }
                
                upload_response = await client.post(
                    f"{MIGRATION_TOOLKIT_URL}/api/import/upload",
                    files=files,
                    data=data,
                    headers=authenticated_admin_session['headers']
                )
                assert upload_response.status_code == 201
                
                import_job_id = upload_response.json()['job_id']
                preview = upload_response.json()['preview']
                
                assert 'characters' in preview
                assert len(preview['characters']) == 1
                assert preview['characters'][0]['name'] == 'Thorin Ironbeard'
            
            # Execute migration with character mapping
            execute_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/import/{import_job_id}/execute",
                json={
                    'confirm_import': True,
                    'character_mapping': {
                        'stat_system': 'd20_3.5',
                        'auto_calculate_modifiers': True,
                        'preserve_custom_fields': True
                    }
                },
                headers=authenticated_admin_session['headers']
            )
            assert execute_response.status_code == 202
            
            # Wait for completion and verify
            await asyncio.sleep(2)
            
            status_response = await client.get(
                f"{MIGRATION_TOOLKIT_URL}/api/import/{import_job_id}/status",
                headers=authenticated_admin_session['headers']
            )
            assert status_response.json()['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_maker_portfolio_json_migration(self, temp_data_files, authenticated_admin_session):
        """Test migrating maker portfolio from JSON format"""
        
        async with httpx.AsyncClient() as client:
            with open(temp_data_files['json_file'], 'rb') as f:
                files = {'file': ('maker_portfolio.json', f, 'application/json')}
                data = {
                    'source_system': 'etsy_export',
                    'target_platform': 'makerlog',
                    'data_type': 'portfolio'
                }
                
                upload_response = await client.post(
                    f"{MIGRATION_TOOLKIT_URL}/api/import/upload",
                    files=files,
                    data=data,
                    headers=authenticated_admin_session['headers']
                )
                assert upload_response.status_code == 201
                
                preview = upload_response.json()['preview']
                assert 'projects' in preview
                assert len(preview['projects']) == 2
            
            import_job_id = upload_response.json()['job_id']
            
            # Execute with portfolio-specific settings
            execute_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/import/{import_job_id}/execute",
                json={
                    'confirm_import': True,
                    'portfolio_settings': {
                        'import_images': False,  # Skip image migration for test
                        'create_maker_profile': True,
                        'set_availability': True
                    }
                },
                headers=authenticated_admin_session['headers']
            )
            assert execute_response.status_code == 202
            
            await asyncio.sleep(2)
            
            # Verify maker profile was created
            makerlog_response = await client.get(
                f"http://localhost:8301/api/makers/search",
                params={'business_name': 'Legacy Crafts Studio'},
                headers=authenticated_admin_session['headers']
            )
            assert makerlog_response.status_code == 200
            
            makers = makerlog_response.json()['makers']
            assert len(makers) == 1
            assert makers[0]['specialties'] == ['woodworking', 'laser_engraving']

    @pytest.mark.asyncio
    async def test_database_migration_sqlite(self, temp_data_files, authenticated_admin_session):
        """Test migrating data from SQLite database"""
        
        async with httpx.AsyncClient() as client:
            with open(temp_data_files['db_file'], 'rb') as f:
                files = {'file': ('legacy_data.db', f, 'application/octet-stream')}
                data = {
                    'source_system': 'sqlite_db',
                    'target_platform': 'dmlog',
                    'data_type': 'sessions',
                    'table_mappings': json.dumps({
                        'sessions': {
                            'primary_table': 'sessions',
                            'id_field': 'id',
                            'foreign_keys': {'campaign_id': 'campaigns.id'}
                        }
                    })
                }
                
                upload_response = await client.post(
                    f"{MIGRATION_TOOLKIT_URL}/api/import/upload",
                    files=files,
                    data=data,
                    headers=authenticated_admin_session['headers']
                )
                assert upload_response.status_code == 201
                
                preview = upload_response.json()['preview']
                assert 'sessions' in preview
                assert len(preview['sessions']) == 1
            
            import_job_id = upload_response.json()['job_id']
            
            # Execute database migration
            execute_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/import/{import_job_id}/execute",
                json={'confirm_import': True},
                headers=authenticated_admin_session['headers']
            )
            assert execute_response.status_code == 202

    @pytest.mark.asyncio
    async def test_bulk_data_export(self, authenticated_admin_session):
        """Test bulk data export functionality"""
        
        async with httpx.AsyncClient() as client:
            # Create some test data to export
            test_campaigns = []
            for i in range(3):
                campaign_response = await client.post(
                    f"http://localhost:8300/api/campaigns",
                    json={
                        'name': f'Export Test Campaign {i+1}',
                        'description': 'Campaign for export testing',
                        'system': 'D&D 5e'
                    },
                    headers=authenticated_admin_session['headers']
                )
                test_campaigns.append(campaign_response.json()['campaign_id'])
            
            # Request bulk export
            export_request = {
                'platform': 'dmlog',
                'data_types': ['campaigns', 'characters', 'sessions'],
                'format': 'json',
                'date_range': {
                    'start': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    'end': datetime.utcnow().isoformat()
                },
                'include_metadata': True
            }
            
            export_response = await client.post(
                f"{DATA_EXPORT_URL}/api/export/request",
                json=export_request,
                headers=authenticated_admin_session['headers']
            )
            assert export_response.status_code == 202
            
            export_job_id = export_response.json()['job_id']
            
            # Wait for export completion
            for _ in range(15):
                status_response = await client.get(
                    f"{DATA_EXPORT_URL}/api/export/{export_job_id}/status",
                    headers=authenticated_admin_session['headers']
                )
                status_data = status_response.json()
                
                if status_data['status'] == 'completed':
                    break
                elif status_data['status'] == 'failed':
                    pytest.fail(f"Export failed: {status_data.get('error')}")
                
                await asyncio.sleep(1)
            
            assert status_data['status'] == 'completed'
            assert 'download_url' in status_data
            
            # Download and verify export data
            download_response = await client.get(
                status_data['download_url'],
                headers=authenticated_admin_session['headers']
            )
            assert download_response.status_code == 200
            
            export_data = download_response.json()
            assert 'campaigns' in export_data
            assert len(export_data['campaigns']) >= 3  # Our test campaigns
            assert 'export_metadata' in export_data
            
            # Verify export metadata
            metadata = export_data['export_metadata']
            assert metadata['export_date'] is not None
            assert metadata['total_records'] > 0
            assert metadata['platforms_included'] == ['dmlog']

    @pytest.mark.asyncio
    async def test_incremental_migration_sync(self, authenticated_admin_session):
        """Test incremental data synchronization for ongoing migrations"""
        
        async with httpx.AsyncClient() as client:
            # Set up initial migration baseline
            baseline_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/sync/baseline",
                json={
                    'source_system': 'legacy_d20',
                    'target_platform': 'dmlog',
                    'sync_frequency': 'daily',
                    'data_types': ['campaigns', 'sessions']
                },
                headers=authenticated_admin_session['headers']
            )
            assert baseline_response.status_code == 201
            sync_config_id = baseline_response.json()['sync_config_id']
            
            # Simulate new data in source system
            new_data = {
                'campaigns': [
                    {
                        'id': 'new_campaign_001',
                        'name': 'Incremental Test Campaign',
                        'created_date': datetime.utcnow().isoformat(),
                        'last_modified': datetime.utcnow().isoformat()
                    }
                ]
            }
            
            # Trigger incremental sync
            sync_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/sync/{sync_config_id}/execute",
                json={'new_data': new_data},
                headers=authenticated_admin_session['headers']
            )
            assert sync_response.status_code == 202
            
            sync_job_id = sync_response.json()['job_id']
            
            # Monitor sync progress
            for _ in range(10):
                sync_status = await client.get(
                    f"{MIGRATION_TOOLKIT_URL}/api/sync/{sync_job_id}/status",
                    headers=authenticated_admin_session['headers']
                )
                if sync_status.json()['status'] == 'completed':
                    break
                await asyncio.sleep(1)
            
            sync_result = sync_status.json()
            assert sync_result['status'] == 'completed'
            assert sync_result['new_records'] == 1
            assert sync_result['updated_records'] == 0

    @pytest.mark.asyncio
    async def test_migration_rollback(self, authenticated_admin_session):
        """Test rolling back a completed migration"""
        
        async with httpx.AsyncClient() as client:
            # First, create a test migration to rollback
            test_data = {
                'campaigns': [
                    {
                        'name': 'Rollback Test Campaign',
                        'system': 'Test System',
                        'migration_batch': 'rollback_test_001'
                    }
                ]
            }
            
            # Create migration record
            migration_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/import/direct",
                json={
                    'source_system': 'test',
                    'target_platform': 'dmlog',
                    'data': test_data,
                    'create_rollback_point': True
                },
                headers=authenticated_admin_session['headers']
            )
            assert migration_response.status_code == 201
            
            migration_id = migration_response.json()['migration_id']
            
            # Verify data was created
            search_response = await client.get(
                f"http://localhost:8300/api/campaigns/search",
                params={'migration_batch': 'rollback_test_001'},
                headers=authenticated_admin_session['headers']
            )
            assert len(search_response.json()['campaigns']) == 1
            
            # Execute rollback
            rollback_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/migrations/{migration_id}/rollback",
                json={'confirm_rollback': True, 'reason': 'Test rollback'},
                headers=authenticated_admin_session['headers']
            )
            assert rollback_response.status_code == 202
            
            rollback_job_id = rollback_response.json()['rollback_job_id']
            
            # Wait for rollback completion
            for _ in range(10):
                rollback_status = await client.get(
                    f"{MIGRATION_TOOLKIT_URL}/api/rollbacks/{rollback_job_id}/status",
                    headers=authenticated_admin_session['headers']
                )
                if rollback_status.json()['status'] == 'completed':
                    break
                await asyncio.sleep(1)
            
            # Verify data was removed
            verify_response = await client.get(
                f"http://localhost:8300/api/campaigns/search",
                params={'migration_batch': 'rollback_test_001'},
                headers=authenticated_admin_session['headers']
            )
            assert len(verify_response.json()['campaigns']) == 0

    @pytest.mark.asyncio
    async def test_cross_platform_data_validation(self, authenticated_admin_session):
        """Test data validation across different platform schemas"""
        
        async with httpx.AsyncClient() as client:
            # Test data with schema mismatches
            invalid_data = {
                'campaigns': [
                    {
                        'name': '',  # Empty name should fail validation
                        'system': 'Unknown System',
                        'level_range': 'invalid-range',  # Should be numeric
                        'max_players': 'unlimited'  # Should be numeric
                    }
                ]
            }
            
            validation_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/validation/schema",
                json={
                    'target_platform': 'dmlog',
                    'data_type': 'campaigns',
                    'data': invalid_data
                },
                headers=authenticated_admin_session['headers']
            )
            assert validation_response.status_code == 200
            
            validation_result = validation_response.json()
            assert validation_result['valid'] == False
            assert len(validation_result['errors']) > 0
            assert any('name' in error['field'] for error in validation_result['errors'])
            
            # Test with corrections
            corrected_data = {
                'campaigns': [
                    {
                        'name': 'Valid Campaign Name',
                        'system': 'D&D 5e',
                        'level_range': '1-10',
                        'max_players': 6
                    }
                ]
            }
            
            corrected_validation = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/validation/schema",
                json={
                    'target_platform': 'dmlog',
                    'data_type': 'campaigns',
                    'data': corrected_data
                },
                headers=authenticated_admin_session['headers']
            )
            assert corrected_validation.json()['valid'] == True

    @pytest.mark.load
    async def test_large_dataset_migration(self, authenticated_admin_session):
        """Test migration performance with large datasets"""
        
        # Generate large dataset for testing
        large_dataset = {
            'campaigns': [],
            'characters': [],
            'sessions': []
        }
        
        # Create 100 campaigns, 500 characters, 1000 sessions
        for i in range(100):
            campaign_id = f"large_test_campaign_{i:03d}"
            large_dataset['campaigns'].append({
                'id': campaign_id,
                'name': f'Large Test Campaign {i+1}',
                'system': 'D&D 5e',
                'created_date': datetime.utcnow().isoformat()
            })
            
            # 5 characters per campaign
            for j in range(5):
                large_dataset['characters'].append({
                    'id': f"char_{i:03d}_{j:02d}",
                    'campaign_id': campaign_id,
                    'name': f'Character {j+1} Campaign {i+1}',
                    'class': 'Fighter',
                    'level': j + 1
                })
            
            # 10 sessions per campaign
            for k in range(10):
                large_dataset['sessions'].append({
                    'id': f"session_{i:03d}_{k:02d}",
                    'campaign_id': campaign_id,
                    'date': (datetime.utcnow() - timedelta(days=k*7)).isoformat(),
                    'duration': 180 + (k * 15)
                })
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            start_time = datetime.utcnow()
            
            migration_response = await client.post(
                f"{MIGRATION_TOOLKIT_URL}/api/import/direct",
                json={
                    'source_system': 'performance_test',
                    'target_platform': 'dmlog',
                    'data': large_dataset,
                    'batch_size': 50  # Process in batches
                },
                headers=authenticated_admin_session['headers']
            )
            assert migration_response.status_code == 201
            
            migration_id = migration_response.json()['migration_id']
            
            # Monitor migration progress
            completed = False
            for _ in range(60):  # Wait up to 60 seconds
                status_response = await client.get(
                    f"{MIGRATION_TOOLKIT_URL}/api/migrations/{migration_id}/status",
                    headers=authenticated_admin_session['headers']
                )
                status = status_response.json()
                
                if status['status'] == 'completed':
                    completed = True
                    break
                elif status['status'] == 'failed':
                    pytest.fail(f"Large dataset migration failed: {status.get('error')}")
                
                await asyncio.sleep(1)
            
            assert completed, "Large dataset migration did not complete in time"
            
            # Verify performance metrics
            completion_time = datetime.utcnow()
            duration = (completion_time - start_time).total_seconds()
            
            # Should complete large dataset in under 60 seconds
            assert duration < 60
            
            # Verify all records were processed
            final_status = status_response.json()
            assert final_status['total_records'] == 1600  # 100 + 500 + 1000
            assert final_status['successful_records'] == 1600