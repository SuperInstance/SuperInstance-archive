#!/usr/bin/env python3
"""
Test suite for ActiveLog Sync Service v2
"""

import asyncio
import pytest
import tempfile
import os
from datetime import datetime

# Import the modules we're testing
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.sync_engine import SyncEngine, SyncItem, DeviceInfo, DeviceType, DeviceCapabilities, ContentType
from strategies.selective_sync import SelectiveSyncEngine, SyncOptimizer
from strategies.bandwidth_aware import NetworkMonitor, AdaptiveSyncScheduler
from resolution.conflict_resolver import ConflictManager, ConflictItem, ConflictDetector
from protocols.sync_protocol import SyncProtocolFactory
from sync_service import SyncServiceV2

class TestSyncEngine:
    """Test cases for SyncEngine"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def sync_engine(self, temp_db):
        """Create SyncEngine instance for testing"""
        config = {'database_path': temp_db}
        return SyncEngine(config)
    
    @pytest.fixture
    def test_device(self):
        """Create test device"""
        return DeviceInfo(
            device_id="test-device-001",
            device_type=DeviceType.PHONE,
            capabilities=DeviceCapabilities.MOBILE,
            name="Test Phone",
            user_id="test-user",
            platform="test-platform",
            version="1.0.0",
            last_seen=datetime.now().isoformat()
        )
    
    @pytest.fixture
    def test_item(self):
        """Create test sync item"""
        return SyncItem(
            item_id="test-item-001",
            content_type=ContentType.TEXT,
            data={"title": "Test Note", "content": "This is a test note"},
            metadata={"app": "notes"},
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            version=1,
            device_id="test-device-001",
            user_id="test-user"
        )
    
    def test_device_registration(self, sync_engine, test_device):
        """Test device registration"""
        registered_device = sync_engine.register_device(
            test_device.device_id,
            test_device.device_type,
            test_device.capabilities,
            test_device.name,
            test_device.user_id,
            test_device.platform,
            test_device.version
        )
        
        assert registered_device.device_id == test_device.device_id
        assert registered_device.device_type == test_device.device_type
        assert registered_device.capabilities == test_device.capabilities
        
        # Verify device is stored in database
        retrieved_device = sync_engine.database.get_device(test_device.device_id)
        assert retrieved_device is not None
        assert retrieved_device.device_id == test_device.device_id
    
    @pytest.mark.asyncio
    async def test_item_sync(self, sync_engine, test_device, test_item):
        """Test item synchronization"""
        # Register device first
        sync_engine.register_device(
            test_device.device_id,
            test_device.device_type,
            test_device.capabilities,
            test_device.name,
            test_device.user_id,
            test_device.platform,
            test_device.version
        )
        
        # Sync item
        results = await sync_engine.sync_item(test_item)
        
        # Should have results for the device
        assert isinstance(results, dict)
        
        # Verify item is stored
        stored_item = sync_engine.database.get_sync_item(test_item.item_id)
        assert stored_item is not None
        assert stored_item.item_id == test_item.item_id
        assert stored_item.data == test_item.data

class TestSelectiveSync:
    """Test cases for selective sync"""
    
    @pytest.fixture
    def selective_engine(self):
        """Create SelectiveSyncEngine for testing"""
        return SelectiveSyncEngine()
    
    @pytest.fixture
    def mobile_device(self):
        """Create mobile device for testing"""
        return DeviceInfo(
            device_id="mobile-001",
            device_type=DeviceType.PHONE,
            capabilities=DeviceCapabilities.MOBILE,
            name="Test Mobile",
            user_id="test-user",
            platform="ios",
            version="1.0.0",
            last_seen=datetime.now().isoformat(),
            network_type="cellular",
            battery_level=25
        )
    
    @pytest.fixture
    def desktop_device(self):
        """Create desktop device for testing"""
        return DeviceInfo(
            device_id="desktop-001",
            device_type=DeviceType.DESKTOP,
            capabilities=DeviceCapabilities.FULL,
            name="Test Desktop",
            user_id="test-user",
            platform="macos",
            version="1.0.0",
            last_seen=datetime.now().isoformat()
        )
    
    @pytest.fixture
    def large_video_item(self):
        """Create large video item for testing"""
        return SyncItem(
            item_id="video-001",
            content_type=ContentType.VIDEO,
            data={"filename": "test_video.mp4"},
            metadata={"duration": 300, "resolution": "1080p"},
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            version=1,
            device_id="desktop-001",
            user_id="test-user",
            file_size=100 * 1024 * 1024,  # 100MB
            priority=4
        )
    
    @pytest.fixture
    def text_item(self):
        """Create text item for testing"""
        return SyncItem(
            item_id="text-001",
            content_type=ContentType.TEXT,
            data={"title": "Test Note", "content": "This is a test note"},
            metadata={},
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            version=1,
            device_id="desktop-001",
            user_id="test-user",
            priority=8
        )
    
    def test_mobile_video_exclusion(self, selective_engine, mobile_device, large_video_item):
        """Test that large videos are excluded on mobile with cellular"""
        decision = selective_engine.should_sync_item(large_video_item, mobile_device)
        
        # Large video should be deferred on cellular mobile device
        assert not decision['sync'] or decision['defer']
    
    def test_desktop_full_sync(self, selective_engine, desktop_device, large_video_item):
        """Test that desktop gets full sync"""
        decision = selective_engine.should_sync_item(large_video_item, desktop_device)
        
        # Desktop should sync everything
        assert decision['sync']
        assert not decision['defer']
    
    def test_high_priority_always_syncs(self, selective_engine, mobile_device, text_item):
        """Test that high priority items always sync"""
        decision = selective_engine.should_sync_item(text_item, mobile_device)
        
        # High priority text should always sync
        assert decision['sync']
        assert not decision['defer']
    
    def test_sync_optimizer_batch(self, mobile_device, large_video_item, text_item):
        """Test sync optimizer with mixed content"""
        optimizer = SyncOptimizer()
        items = [large_video_item, text_item]
        
        optimization = optimizer.optimize_sync_batch(items, mobile_device)
        
        # Should have some items to sync and some deferred/excluded
        assert optimization['optimization_summary']['original_count'] == 2
        assert optimization['optimization_summary']['sync_count'] >= 1  # At least the text item

class TestConflictResolution:
    """Test cases for conflict resolution"""
    
    @pytest.fixture
    def conflict_detector(self):
        """Create ConflictDetector for testing"""
        return ConflictDetector()
    
    @pytest.fixture
    def conflict_manager(self):
        """Create ConflictManager for testing"""
        return ConflictManager()
    
    @pytest.fixture
    def conflicting_items(self):
        """Create conflicting items for testing"""
        base_time = datetime.now()
        
        item1 = ConflictItem(
            version_id="v1",
            device_id="phone-001",
            device_name="iPhone",
            user_id="user123",
            timestamp=(base_time).isoformat(),
            data={"title": "Test Note", "content": "Original content\nAdded from phone"},
            metadata={"device_type": "mobile"},
            checksum="abc123"
        )
        
        item2 = ConflictItem(
            version_id="v2",
            device_id="desktop-001",
            device_name="Desktop",
            user_id="user123",
            timestamp=(base_time).isoformat(),  # Same time = concurrent
            data={"title": "Test Note", "content": "Original content\nAdded from desktop"},
            metadata={"device_type": "desktop"},
            checksum="def456"
        )
        
        return [item1, item2]
    
    def test_conflict_detection(self, conflict_detector, conflicting_items):
        """Test conflict detection between concurrent edits"""
        conflicts = conflict_detector.detect_conflicts("test-item", conflicting_items)
        
        # Should detect a concurrent edit conflict
        assert len(conflicts) >= 1
        assert any(c.conflict_type.value == "concurrent_edit" for c in conflicts)
    
    def test_conflict_resolution_auto_merge(self, conflict_manager, conflict_detector, conflicting_items):
        """Test automatic conflict resolution"""
        conflicts = conflict_detector.detect_conflicts("test-item", conflicting_items)
        
        if conflicts:
            conflict = conflicts[0]
            
            # Try to resolve with auto merge
            from resolution.conflict_resolver import ResolutionStrategy
            result = conflict_manager.resolver.resolve_conflict(
                conflict, 
                ResolutionStrategy.AUTO_MERGE
            )
            
            assert result.strategy_used == ResolutionStrategy.AUTO_MERGE
            assert result.merged_data is not None
            assert result.confidence_score > 0

class TestBandwidthAwareness:
    """Test cases for bandwidth-aware sync"""
    
    @pytest.mark.asyncio
    async def test_network_monitoring(self):
        """Test basic network monitoring functionality"""
        monitor = NetworkMonitor(monitor_interval=1)
        
        # Start monitoring briefly
        monitor_task = asyncio.create_task(monitor.start_monitoring())
        await asyncio.sleep(2)  # Let it run for 2 seconds
        
        monitor.stop_monitoring()
        monitor_task.cancel()
        
        # Should have some metrics
        assert monitor.current_metrics is not None
        assert monitor.current_metrics.bandwidth_down > 0
    
    def test_adaptive_scheduler_strategy_selection(self):
        """Test adaptive scheduler strategy selection"""
        # Create mock network monitor
        monitor = NetworkMonitor(monitor_interval=60)
        scheduler = AdaptiveSyncScheduler(monitor)
        
        # Get strategy (should not crash)
        strategy = scheduler.get_optimal_strategy()
        
        assert strategy is not None
        assert strategy.strategy_name in ["aggressive", "balanced", "conservative", "minimal"]

class TestSyncProtocols:
    """Test cases for sync protocols"""
    
    @pytest.fixture
    def mobile_device_info(self):
        """Create mobile device info for testing"""
        return DeviceInfo(
            device_id="mobile-test",
            device_type=DeviceType.PHONE,
            capabilities=DeviceCapabilities.MOBILE,
            name="Test Mobile",
            user_id="test-user",
            platform="ios",
            version="1.0.0",
            last_seen=datetime.now().isoformat()
        )
    
    @pytest.fixture
    def desktop_device_info(self):
        """Create desktop device info for testing"""
        return DeviceInfo(
            device_id="desktop-test",
            device_type=DeviceType.DESKTOP,
            capabilities=DeviceCapabilities.FULL,
            name="Test Desktop",
            user_id="test-user",
            platform="macos",
            version="1.0.0",
            last_seen=datetime.now().isoformat()
        )
    
    def test_protocol_factory_mobile(self, mobile_device_info):
        """Test protocol factory creates mobile protocol"""
        protocol = SyncProtocolFactory.create_protocol(mobile_device_info)
        
        # Should create MobileSyncProtocol
        from protocols.sync_protocol import MobileSyncProtocol
        assert isinstance(protocol, MobileSyncProtocol)
        
        # Should have mobile-specific capabilities
        capabilities = protocol._get_protocol_capabilities()
        assert "bandwidth_awareness" in capabilities
        assert "battery_optimization" in capabilities
    
    def test_protocol_factory_desktop(self, desktop_device_info):
        """Test protocol factory creates desktop protocol"""
        protocol = SyncProtocolFactory.create_protocol(desktop_device_info)
        
        # Should create DesktopSyncProtocol
        from protocols.sync_protocol import DesktopSyncProtocol
        assert isinstance(protocol, DesktopSyncProtocol)
        
        # Should have desktop-specific capabilities
        capabilities = protocol._get_protocol_capabilities()
        assert "real_time_collaboration" in capabilities
        assert "version_history" in capabilities

class TestSyncService:
    """Test cases for main sync service"""
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary config for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            config = {
                "sync_engine": {
                    "database_path": ":memory:",  # Use in-memory database
                    "sync_interval": 1
                },
                "log_level": "DEBUG"
            }
            json.dump(config, f)
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def sync_service(self, temp_config):
        """Create SyncServiceV2 for testing"""
        return SyncServiceV2(temp_config)
    
    @pytest.fixture
    def test_device_info(self):
        """Create test device info"""
        return DeviceInfo(
            device_id="service-test-device",
            device_type=DeviceType.PHONE,
            capabilities=DeviceCapabilities.MOBILE,
            name="Service Test Device",
            user_id="test-user",
            platform="test",
            version="1.0.0",
            last_seen=datetime.now().isoformat()
        )
    
    @pytest.mark.asyncio
    async def test_device_registration(self, sync_service, test_device_info):
        """Test device registration in sync service"""
        device_id = await sync_service.register_device(test_device_info)
        
        assert device_id == test_device_info.device_id
        assert device_id in sync_service.active_protocols
        
        # Check device status
        status = sync_service.get_device_status(device_id)
        assert status is not None
        assert status['device_id'] == device_id
    
    def test_sync_stats(self, sync_service):
        """Test sync statistics"""
        stats = sync_service.get_sync_stats()
        
        assert 'items_synced' in stats
        assert 'conflicts_resolved' in stats
        assert 'uptime_seconds' in stats
        assert 'registered_devices' in stats
    
    def test_device_list(self, sync_service):
        """Test device list functionality"""
        devices = sync_service.get_device_list()
        
        # Should be empty initially
        assert isinstance(devices, list)
        assert len(devices) == 0

# Integration test
@pytest.mark.asyncio
async def test_end_to_end_sync_flow():
    """Test complete sync flow from device registration to item sync"""
    # Create temporary service
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        config = {
            "sync_engine": {
                "database_path": temp_db.name,
                "sync_interval": 1
            }
        }
        
        service = SyncServiceV2()
        service.config = config
        service.sync_engine = SyncEngine(config["sync_engine"])
        
        try:
            # Register devices
            phone = DeviceInfo(
                device_id="integration-phone",
                device_type=DeviceType.PHONE,
                capabilities=DeviceCapabilities.MOBILE,
                name="Integration Phone",
                user_id="integration-user",
                platform="ios",
                version="1.0.0",
                last_seen=datetime.now().isoformat()
            )
            
            desktop = DeviceInfo(
                device_id="integration-desktop",
                device_type=DeviceType.DESKTOP,
                capabilities=DeviceCapabilities.FULL,
                name="Integration Desktop",
                user_id="integration-user",
                platform="macos",
                version="1.0.0",
                last_seen=datetime.now().isoformat()
            )
            
            await service.register_device(phone)
            await service.register_device(desktop)
            
            # Create and sync item
            test_item = SyncItem(
                item_id="integration-item",
                content_type=ContentType.TEXT,
                data={"title": "Integration Test", "content": "This is an integration test"},
                metadata={},
                created_at=datetime.now().isoformat(),
                modified_at=datetime.now().isoformat(),
                version=1,
                device_id="integration-phone",
                user_id="integration-user"
            )
            
            # Sync item
            sync_results = await service.sync_item(test_item)
            
            # Should have sync results
            assert isinstance(sync_results, dict)
            
            # Verify devices are registered
            devices = service.get_device_list()
            assert len(devices) == 2
            
        finally:
            # Cleanup
            os.unlink(temp_db.name)

if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])