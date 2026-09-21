#!/usr/bin/env python3
"""
ActiveLog.ai Selective Sync Strategies

Device capability-aware sync with granular content filtering and adaptive strategies.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import re

from ..core.sync_engine import DeviceInfo, DeviceCapabilities, SyncItem, ContentType, DeviceType

class SyncRule(Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    TRANSFORM = "transform"
    DEFER = "defer"

@dataclass
class SelectiveRule:
    """Rule for selective synchronization"""
    rule_id: str
    rule_type: SyncRule
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    priority: int = 5
    enabled: bool = True
    description: str = ""

@dataclass
class SyncFilter:
    """Filter configuration for device"""
    device_id: str
    rules: List[SelectiveRule]
    max_file_size: Optional[int] = None
    allowed_content_types: Optional[Set[ContentType]] = None
    bandwidth_limit: Optional[int] = None
    storage_quota: Optional[int] = None
    battery_threshold: Optional[int] = None

class ContentAnalyzer:
    """Analyze content for selective sync decisions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_content(self, item: SyncItem) -> Dict[str, Any]:
        """Analyze content characteristics"""
        analysis = {
            'content_type': item.content_type.value,
            'size': item.file_size or len(json.dumps(item.data)),
            'priority': item.priority,
            'tags': item.tags,
            'created_age_hours': self._get_age_hours(item.created_at),
            'modified_age_hours': self._get_age_hours(item.modified_at),
            'has_file': item.file_path is not None,
            'complexity_score': self._calculate_complexity_score(item)
        }
        
        # Content-specific analysis
        if item.content_type == ContentType.TEXT:
            analysis.update(self._analyze_text_content(item))
        elif item.content_type == ContentType.IMAGE:
            analysis.update(self._analyze_image_content(item))
        elif item.content_type == ContentType.VIDEO:
            analysis.update(self._analyze_video_content(item))
        elif item.content_type == ContentType.DOCUMENT:
            analysis.update(self._analyze_document_content(item))
        
        return analysis
    
    def _get_age_hours(self, timestamp: str) -> float:
        """Get age in hours from timestamp"""
        try:
            dt = datetime.fromisoformat(timestamp)
            return (datetime.now() - dt).total_seconds() / 3600
        except:
            return 0
    
    def _calculate_complexity_score(self, item: SyncItem) -> float:
        """Calculate content complexity score (0-10)"""
        score = 1.0
        
        # File size factor
        if item.file_size:
            if item.file_size > 100 * 1024 * 1024:  # >100MB
                score += 4
            elif item.file_size > 10 * 1024 * 1024:  # >10MB
                score += 2
            elif item.file_size > 1024 * 1024:  # >1MB
                score += 1
        
        # Data complexity
        data_str = json.dumps(item.data)
        if len(data_str) > 10000:
            score += 2
        elif len(data_str) > 1000:
            score += 1
        
        # Metadata complexity
        if len(item.metadata) > 10:
            score += 1
        
        return min(score, 10.0)
    
    def _analyze_text_content(self, item: SyncItem) -> Dict[str, Any]:
        """Analyze text content"""
        text_data = item.data.get('content', '') or item.data.get('text', '')
        
        return {
            'word_count': len(text_data.split()) if text_data else 0,
            'character_count': len(text_data) if text_data else 0,
            'has_formatting': self._has_rich_formatting(text_data),
            'language_detected': self._detect_language(text_data),
            'contains_urls': bool(re.search(r'http[s]?://\S+', text_data)),
            'contains_mentions': bool(re.search(r'@\w+', text_data)),
            'contains_hashtags': bool(re.search(r'#\w+', text_data))
        }
    
    def _analyze_image_content(self, item: SyncItem) -> Dict[str, Any]:
        """Analyze image content"""
        metadata = item.metadata
        
        return {
            'format': metadata.get('format', 'unknown'),
            'dimensions': metadata.get('dimensions', {}),
            'has_exif': 'exif' in metadata,
            'is_photo': metadata.get('type') == 'photo',
            'is_screenshot': metadata.get('type') == 'screenshot',
            'compression_ratio': metadata.get('compression_ratio', 1.0)
        }
    
    def _analyze_video_content(self, item: SyncItem) -> Dict[str, Any]:
        """Analyze video content"""
        metadata = item.metadata
        
        return {
            'duration_seconds': metadata.get('duration', 0),
            'resolution': metadata.get('resolution', 'unknown'),
            'fps': metadata.get('fps', 0),
            'codec': metadata.get('codec', 'unknown'),
            'bitrate': metadata.get('bitrate', 0),
            'has_audio': metadata.get('has_audio', False)
        }
    
    def _analyze_document_content(self, item: SyncItem) -> Dict[str, Any]:
        """Analyze document content"""
        metadata = item.metadata
        
        return {
            'page_count': metadata.get('pages', 0),
            'document_type': metadata.get('type', 'unknown'),
            'has_images': metadata.get('has_images', False),
            'has_tables': metadata.get('has_tables', False),
            'editable': metadata.get('editable', True)
        }
    
    def _has_rich_formatting(self, text: str) -> bool:
        """Check if text has rich formatting"""
        formatting_patterns = [
            r'<[^>]+>',  # HTML tags
            r'\*\*.*?\*\*',  # Bold markdown
            r'\*.*?\*',  # Italic markdown
            r'`.*?`',  # Code markdown
            r'!\[.*?\]\(.*?\)',  # Images
            r'\[.*?\]\(.*?\)'  # Links
        ]
        
        for pattern in formatting_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_language(self, text: str) -> str:
        """Basic language detection"""
        # Simplified language detection
        if not text:
            return 'unknown'
        
        # Count common English words
        english_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = text.lower().split()
        english_count = sum(1 for word in words if word in english_words)
        
        if words and english_count / len(words) > 0.1:
            return 'en'
        
        return 'unknown'

class DeviceProfiler:
    """Profile device capabilities and limitations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_device_profile(self, device: DeviceInfo) -> Dict[str, Any]:
        """Get comprehensive device profile"""
        profile = {
            'device_type': device.device_type.value,
            'capabilities': device.capabilities.value,
            'platform': device.platform,
            'constraints': self._get_device_constraints(device),
            'preferences': self._get_device_preferences(device),
            'network_profile': self._get_network_profile(device),
            'storage_profile': self._get_storage_profile(device),
            'power_profile': self._get_power_profile(device)
        }
        
        return profile
    
    def _get_device_constraints(self, device: DeviceInfo) -> Dict[str, Any]:
        """Get device constraints"""
        constraints = {}
        
        if device.capabilities == DeviceCapabilities.MINIMAL:
            constraints.update({
                'max_file_size': 1024 * 1024,  # 1MB
                'max_concurrent_syncs': 1,
                'text_only': True,
                'no_media': True
            })
        elif device.capabilities == DeviceCapabilities.MOBILE:
            constraints.update({
                'max_file_size': 50 * 1024 * 1024,  # 50MB
                'max_concurrent_syncs': 3,
                'compress_images': True,
                'defer_videos': True
            })
        elif device.capabilities == DeviceCapabilities.STANDARD:
            constraints.update({
                'max_file_size': 500 * 1024 * 1024,  # 500MB
                'max_concurrent_syncs': 5,
                'compress_videos': True
            })
        else:  # FULL
            constraints.update({
                'max_file_size': None,  # No limit
                'max_concurrent_syncs': 10,
                'full_quality': True
            })
        
        # Platform-specific constraints
        if device.platform in ['ios', 'android']:
            constraints['background_limits'] = True
            constraints['cellular_awareness'] = True
        elif device.platform == 'web':
            constraints['storage_api_limits'] = True
            constraints['cors_restrictions'] = True
        
        return constraints
    
    def _get_device_preferences(self, device: DeviceInfo) -> Dict[str, Any]:
        """Get device-specific preferences"""
        preferences = {}
        
        # Mobile preferences
        if device.device_type in [DeviceType.PHONE, DeviceType.TABLET]:
            preferences.update({
                'wifi_only_large_files': True,
                'battery_aware_sync': True,
                'thumbnail_preview': True,
                'incremental_sync': True
            })
        
        # Desktop preferences
        elif device.device_type == DeviceType.DESKTOP:
            preferences.update({
                'full_sync': True,
                'immediate_sync': True,
                'version_history': True,
                'background_processing': True
            })
        
        # Web preferences
        elif device.device_type == DeviceType.WEB:
            preferences.update({
                'reference_only_large_files': True,
                'session_based_sync': True,
                'progressive_loading': True
            })
        
        return preferences
    
    def _get_network_profile(self, device: DeviceInfo) -> Dict[str, Any]:
        """Get network profile"""
        profile = {
            'current_type': device.network_type,
            'bandwidth_limit': device.bandwidth_limit,
            'is_metered': device.network_type == 'cellular',
            'latency_sensitive': device.device_type in [DeviceType.PHONE, DeviceType.TABLET]
        }
        
        return profile
    
    def _get_storage_profile(self, device: DeviceInfo) -> Dict[str, Any]:
        """Get storage profile"""
        profile = {
            'storage_limit': device.storage_limit,
            'has_local_storage': device.device_type != DeviceType.WEB,
            'cache_aggressive': device.capabilities in [DeviceCapabilities.STANDARD, DeviceCapabilities.FULL],
            'cleanup_old_files': device.capabilities == DeviceCapabilities.MOBILE
        }
        
        return profile
    
    def _get_power_profile(self, device: DeviceInfo) -> Dict[str, Any]:
        """Get power profile"""
        profile = {
            'battery_level': device.battery_level,
            'is_battery_powered': device.device_type in [DeviceType.PHONE, DeviceType.TABLET],
            'power_save_mode': device.battery_level and device.battery_level < 20,
            'background_sync_allowed': device.battery_level is None or device.battery_level > 30
        }
        
        return profile

class SelectiveSyncEngine:
    """Engine for selective synchronization decisions"""
    
    def __init__(self):
        self.content_analyzer = ContentAnalyzer()
        self.device_profiler = DeviceProfiler()
        self.logger = logging.getLogger(__name__)
        
        # Built-in rules
        self.built_in_rules = self._create_built_in_rules()
    
    def should_sync_item(self, item: SyncItem, device: DeviceInfo, 
                        custom_rules: List[SelectiveRule] = None) -> Dict[str, Any]:
        """Determine if item should be synced to device"""
        # Analyze content
        content_analysis = self.content_analyzer.analyze_content(item)
        
        # Get device profile
        device_profile = self.device_profiler.get_device_profile(device)
        
        # Evaluate rules
        all_rules = self.built_in_rules + (custom_rules or [])
        rule_results = []
        
        for rule in all_rules:
            if not rule.enabled:
                continue
            
            result = self._evaluate_rule(rule, item, device, content_analysis, device_profile)
            if result['matches']:
                rule_results.append(result)
        
        # Make final decision
        decision = self._make_sync_decision(rule_results, item, device, content_analysis, device_profile)
        
        return decision
    
    def _evaluate_rule(self, rule: SelectiveRule, item: SyncItem, device: DeviceInfo,
                      content_analysis: Dict[str, Any], device_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate individual rule against item and device"""
        matches = True
        context = {
            'item': asdict(item),
            'device': asdict(device),
            'content': content_analysis,
            'profile': device_profile
        }
        
        # Check conditions
        for condition_key, condition_value in rule.conditions.items():
            if not self._check_condition(condition_key, condition_value, context):
                matches = False
                break
        
        return {
            'rule_id': rule.rule_id,
            'rule_type': rule.rule_type.value,
            'matches': matches,
            'actions': rule.actions,
            'priority': rule.priority,
            'description': rule.description
        }
    
    def _check_condition(self, condition_key: str, condition_value: Any, context: Dict[str, Any]) -> bool:
        """Check if condition is met"""
        try:
            # Parse condition key (e.g., "content.size", "device.capabilities")
            if '.' in condition_key:
                obj_key, attr_key = condition_key.split('.', 1)
                value = context.get(obj_key, {}).get(attr_key)
            else:
                value = context.get(condition_key)
            
            # Handle different condition types
            if isinstance(condition_value, dict):
                # Complex condition with operators
                if 'gt' in condition_value:
                    return value > condition_value['gt']
                elif 'lt' in condition_value:
                    return value < condition_value['lt']
                elif 'eq' in condition_value:
                    return value == condition_value['eq']
                elif 'in' in condition_value:
                    return value in condition_value['in']
                elif 'contains' in condition_value:
                    return condition_value['contains'] in str(value)
                elif 'regex' in condition_value:
                    return bool(re.search(condition_value['regex'], str(value)))
            else:
                # Simple equality check
                return value == condition_value
            
        except Exception as e:
            self.logger.error(f"Error checking condition {condition_key}: {e}")
            return False
        
        return False
    
    def _make_sync_decision(self, rule_results: List[Dict[str, Any]], item: SyncItem, 
                          device: DeviceInfo, content_analysis: Dict[str, Any],
                          device_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Make final sync decision based on rule results"""
        # Sort rules by priority
        rule_results.sort(key=lambda x: x['priority'], reverse=True)
        
        decision = {
            'sync': True,
            'transform': False,
            'defer': False,
            'reason': 'default',
            'transformations': [],
            'applied_rules': [],
            'estimated_size': content_analysis.get('size', 0),
            'estimated_time': 0
        }
        
        # Apply rules in priority order
        for result in rule_results:
            rule_type = result['rule_type']
            actions = result['actions']
            
            decision['applied_rules'].append({
                'rule_id': result['rule_id'],
                'type': rule_type,
                'description': result['description']
            })
            
            if rule_type == 'exclude':
                decision['sync'] = False
                decision['reason'] = f"excluded by rule {result['rule_id']}"
                break
            
            elif rule_type == 'defer':
                decision['defer'] = True
                decision['reason'] = f"deferred by rule {result['rule_id']}"
                if 'defer_until' in actions:
                    decision['defer_until'] = actions['defer_until']
            
            elif rule_type == 'transform':
                decision['transform'] = True
                if 'compression' in actions:
                    decision['transformations'].append({
                        'type': 'compression',
                        'params': actions['compression']
                    })
                if 'resize' in actions:
                    decision['transformations'].append({
                        'type': 'resize',
                        'params': actions['resize']
                    })
                if 'format_conversion' in actions:
                    decision['transformations'].append({
                        'type': 'format_conversion',
                        'params': actions['format_conversion']
                    })
        
        # Calculate estimates
        if decision['sync'] and not decision['defer']:
            decision['estimated_size'] = self._estimate_sync_size(
                content_analysis, decision['transformations']
            )
            decision['estimated_time'] = self._estimate_sync_time(
                decision['estimated_size'], device_profile
            )
        
        return decision
    
    def _estimate_sync_size(self, content_analysis: Dict[str, Any], 
                           transformations: List[Dict[str, Any]]) -> int:
        """Estimate size after transformations"""
        size = content_analysis.get('size', 0)
        
        for transform in transformations:
            if transform['type'] == 'compression':
                compression_ratio = transform['params'].get('ratio', 0.7)
                size = int(size * compression_ratio)
            elif transform['type'] == 'resize':
                resize_factor = transform['params'].get('factor', 0.5)
                size = int(size * resize_factor * resize_factor)  # Quadratic for images
        
        return size
    
    def _estimate_sync_time(self, size: int, device_profile: Dict[str, Any]) -> float:
        """Estimate sync time in seconds"""
        network_profile = device_profile.get('network_profile', {})
        bandwidth = network_profile.get('bandwidth_limit', 1024 * 1024)  # 1 Mbps default
        
        # Add overhead for protocol, processing, etc.
        overhead_factor = 1.5
        estimated_time = (size * 8 / bandwidth) * overhead_factor
        
        return estimated_time
    
    def _create_built_in_rules(self) -> List[SelectiveRule]:
        """Create built-in selective sync rules"""
        rules = []
        
        # Rule 1: Exclude large files on minimal devices
        rules.append(SelectiveRule(
            rule_id="exclude_large_files_minimal",
            rule_type=SyncRule.EXCLUDE,
            conditions={
                "device.capabilities": "minimal",
                "content.size": {"gt": 1024 * 1024}  # >1MB
            },
            actions={},
            priority=9,
            description="Exclude files >1MB on minimal devices"
        ))
        
        # Rule 2: Defer videos on cellular
        rules.append(SelectiveRule(
            rule_id="defer_videos_cellular",
            rule_type=SyncRule.DEFER,
            conditions={
                "profile.network_profile.current_type": "cellular",
                "item.content_type": "video"
            },
            actions={
                "defer_until": "wifi_available"
            },
            priority=8,
            description="Defer video sync on cellular connections"
        ))
        
        # Rule 3: Compress images on mobile
        rules.append(SelectiveRule(
            rule_id="compress_images_mobile",
            rule_type=SyncRule.TRANSFORM,
            conditions={
                "device.capabilities": "mobile",
                "item.content_type": "image",
                "content.size": {"gt": 500 * 1024}  # >500KB
            },
            actions={
                "compression": {
                    "quality": 0.8,
                    "max_dimension": 1920
                }
            },
            priority=7,
            description="Compress large images on mobile devices"
        ))
        
        # Rule 4: Text-only on low battery
        rules.append(SelectiveRule(
            rule_id="text_only_low_battery",
            rule_type=SyncRule.EXCLUDE,
            conditions={
                "profile.power_profile.battery_level": {"lt": 15},
                "item.content_type": {"in": ["video", "audio", "image"]}
            },
            actions={},
            priority=8,
            description="Exclude media when battery is very low"
        ))
        
        # Rule 5: High priority items always sync
        rules.append(SelectiveRule(
            rule_id="high_priority_always",
            rule_type=SyncRule.INCLUDE,
            conditions={
                "item.priority": {"gt": 8}
            },
            actions={},
            priority=10,
            description="Always sync high priority items"
        ))
        
        # Rule 6: Exclude old low-priority items on mobile
        rules.append(SelectiveRule(
            rule_id="exclude_old_low_priority_mobile",
            rule_type=SyncRule.EXCLUDE,
            conditions={
                "device.capabilities": "mobile",
                "item.priority": {"lt": 3},
                "content.modified_age_hours": {"gt": 168}  # >1 week
            },
            actions={},
            priority=6,
            description="Exclude old low-priority items on mobile"
        ))
        
        # Rule 7: Reference-only for very large files on web
        rules.append(SelectiveRule(
            rule_id="reference_large_files_web",
            rule_type=SyncRule.TRANSFORM,
            conditions={
                "device.device_type": "web",
                "content.size": {"gt": 100 * 1024 * 1024}  # >100MB
            },
            actions={
                "reference_only": True,
                "thumbnail": True
            },
            priority=7,
            description="Reference-only for large files on web"
        ))
        
        return rules

class SyncOptimizer:
    """Optimize sync operations based on device capabilities and network conditions"""
    
    def __init__(self):
        self.selective_engine = SelectiveSyncEngine()
        self.logger = logging.getLogger(__name__)
    
    def optimize_sync_batch(self, items: List[SyncItem], device: DeviceInfo,
                           custom_rules: List[SelectiveRule] = None) -> Dict[str, Any]:
        """Optimize batch of items for sync to device"""
        sync_items = []
        deferred_items = []
        excluded_items = []
        transformations_needed = []
        
        total_size = 0
        total_time = 0
        
        for item in items:
            decision = self.selective_engine.should_sync_item(item, device, custom_rules)
            
            if decision['sync'] and not decision['defer']:
                sync_items.append({
                    'item': item,
                    'decision': decision
                })
                total_size += decision['estimated_size']
                total_time += decision['estimated_time']
                
                if decision['transform']:
                    transformations_needed.append({
                        'item_id': item.item_id,
                        'transformations': decision['transformations']
                    })
            
            elif decision['defer']:
                deferred_items.append({
                    'item': item,
                    'reason': decision['reason'],
                    'defer_until': decision.get('defer_until')
                })
            
            else:
                excluded_items.append({
                    'item': item,
                    'reason': decision['reason']
                })
        
        # Sort sync items by priority and size
        sync_items.sort(key=lambda x: (x['item'].priority, -x['decision']['estimated_size']), reverse=True)
        
        return {
            'sync_items': sync_items,
            'deferred_items': deferred_items,
            'excluded_items': excluded_items,
            'transformations_needed': transformations_needed,
            'total_size': total_size,
            'estimated_total_time': total_time,
            'batch_count': len(sync_items),
            'optimization_summary': {
                'original_count': len(items),
                'sync_count': len(sync_items),
                'deferred_count': len(deferred_items),
                'excluded_count': len(excluded_items),
                'transformation_count': len(transformations_needed)
            }
        }
    
    def create_device_filter(self, device: DeviceInfo, user_preferences: Dict[str, Any] = None) -> SyncFilter:
        """Create sync filter for device based on capabilities and user preferences"""
        device_profile = self.selective_engine.device_profiler.get_device_profile(device)
        constraints = device_profile['constraints']
        preferences = device_profile['preferences']
        
        # Merge with user preferences
        if user_preferences:
            preferences.update(user_preferences)
        
        # Create rules based on device profile
        rules = []
        
        # File size limits
        if constraints.get('max_file_size'):
            rules.append(SelectiveRule(
                rule_id=f"max_size_{device.device_id}",
                rule_type=SyncRule.EXCLUDE,
                conditions={
                    "content.size": {"gt": constraints['max_file_size']}
                },
                actions={},
                priority=9,
                description=f"Exclude files larger than {constraints['max_file_size']} bytes"
            ))
        
        # Content type restrictions
        if constraints.get('text_only'):
            rules.append(SelectiveRule(
                rule_id=f"text_only_{device.device_id}",
                rule_type=SyncRule.EXCLUDE,
                conditions={
                    "item.content_type": {"in": ["video", "audio", "image"]}
                },
                actions={},
                priority=8,
                description="Text content only"
            ))
        
        # Compression rules
        if preferences.get('compress_images'):
            rules.append(SelectiveRule(
                rule_id=f"compress_images_{device.device_id}",
                rule_type=SyncRule.TRANSFORM,
                conditions={
                    "item.content_type": "image",
                    "content.size": {"gt": 100 * 1024}  # >100KB
                },
                actions={
                    "compression": {
                        "quality": 0.8,
                        "max_dimension": 1920
                    }
                },
                priority=7,
                description="Compress images for mobile"
            ))
        
        return SyncFilter(
            device_id=device.device_id,
            rules=rules,
            max_file_size=constraints.get('max_file_size'),
            bandwidth_limit=device.bandwidth_limit,
            storage_quota=device.storage_limit,
            battery_threshold=20 if device.device_type in [DeviceType.PHONE, DeviceType.TABLET] else None
        )

async def main():
    """Example usage of selective sync"""
    from ..core.sync_engine import DeviceInfo, DeviceType, DeviceCapabilities, SyncItem, ContentType
    
    # Create test device
    mobile_device = DeviceInfo(
        device_id="phone-001",
        device_type=DeviceType.PHONE,
        capabilities=DeviceCapabilities.MOBILE,
        name="iPhone 15",
        user_id="user123",
        platform="ios",
        version="1.0.0",
        last_seen=datetime.now().isoformat(),
        is_online=True,
        network_type="cellular",
        battery_level=25
    )
    
    # Create test items
    items = [
        SyncItem(
            item_id="text-001",
            content_type=ContentType.TEXT,
            data={"title": "Note", "content": "This is a text note"},
            metadata={},
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            version=1,
            device_id="desktop-001",
            user_id="user123",
            priority=5
        ),
        SyncItem(
            item_id="image-001",
            content_type=ContentType.IMAGE,
            data={"filename": "photo.jpg"},
            metadata={"format": "jpeg", "dimensions": {"width": 4032, "height": 3024}},
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            version=1,
            device_id="desktop-001",
            user_id="user123",
            file_size=5 * 1024 * 1024,  # 5MB
            priority=6
        ),
        SyncItem(
            item_id="video-001",
            content_type=ContentType.VIDEO,
            data={"filename": "video.mp4"},
            metadata={"duration": 300, "resolution": "1080p"},
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat(),
            version=1,
            device_id="desktop-001",
            user_id="user123",
            file_size=100 * 1024 * 1024,  # 100MB
            priority=4
        )
    ]
    
    # Initialize optimizer
    optimizer = SyncOptimizer()
    
    # Optimize batch for mobile device
    optimization = optimizer.optimize_sync_batch(items, mobile_device)
    
    print("Sync Optimization Results:")
    print(f"Original items: {optimization['optimization_summary']['original_count']}")
    print(f"Items to sync: {optimization['optimization_summary']['sync_count']}")
    print(f"Items deferred: {optimization['optimization_summary']['deferred_count']}")
    print(f"Items excluded: {optimization['optimization_summary']['excluded_count']}")
    print(f"Transformations needed: {optimization['optimization_summary']['transformation_count']}")
    print(f"Total estimated size: {optimization['total_size']} bytes")
    print(f"Estimated sync time: {optimization['estimated_total_time']:.2f} seconds")
    
    # Create device filter
    device_filter = optimizer.create_device_filter(mobile_device)
    print(f"\nDevice filter created with {len(device_filter.rules)} rules")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())