#!/usr/bin/env python3
"""
Generate Python Protocol Buffer classes from .proto files
"""

import os
import subprocess
import sys
from pathlib import Path

def generate_protobuf_files():
    """Generate Python files from Protocol Buffer definitions"""
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    proto_dir = script_dir
    output_dir = script_dir / "generated"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Create __init__.py in the generated directory
    init_file = output_dir / "__init__.py"
    init_file.touch()
    
    # Find all .proto files
    proto_files = list(proto_dir.glob("*.proto"))
    
    if not proto_files:
        print("No .proto files found in", proto_dir)
        return False
    
    print(f"Found {len(proto_files)} proto file(s):")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")
    
    # Generate Python files
    try:
        for proto_file in proto_files:
            cmd = [
                sys.executable, "-m", "grpc_tools.protoc",
                f"--proto_path={proto_dir}",
                f"--python_out={output_dir}",
                f"--grpc_python_out={output_dir}",
                str(proto_file)
            ]
            
            print(f"\nGenerating Python files for {proto_file.name}...")
            print(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error generating files for {proto_file.name}:")
                print(result.stderr)
                return False
            else:
                print(f"Successfully generated files for {proto_file.name}")
        
        print(f"\nAll Protocol Buffer files generated successfully!")
        print(f"Generated files are in: {output_dir}")
        
        # List generated files
        generated_files = list(output_dir.glob("*.py"))
        if generated_files:
            print(f"\nGenerated files:")
            for gen_file in generated_files:
                print(f"  - {gen_file.name}")
        
        return True
        
    except Exception as e:
        print(f"Error generating Protocol Buffer files: {e}")
        return False

def create_convenience_imports():
    """Create a convenience module for easier imports"""
    
    output_dir = Path(__file__).parent / "generated"
    convenience_file = output_dir / "mobile_pb.py"
    
    convenience_content = '''"""
Convenience imports for ActiveLog Mobile Protocol Buffers

This module provides easy access to all generated Protocol Buffer classes.
"""

# Import all generated classes
try:
    from .mobile_api_pb2 import *
    from .mobile_api_pb2_grpc import *
except ImportError:
    # Fallback for different import paths
    from mobile_api_pb2 import *
    from mobile_api_pb2_grpc import *

# Convenience class mappings
__all__ = [
    # Device and connection
    'DeviceInfo',
    'ConnectionType',
    'BatteryInfo',
    'PerformanceTier',
    
    # Authentication
    'AuthRequest',
    'AuthResponse',
    'PasswordAuth',
    'TokenAuth',
    'BiometricAuth',
    'OAuthAuth',
    'UserProfile',
    'UserSettings',
    'StorageQuota',
    'ServerCapabilities',
    
    # Files and sync
    'FileMetadata',
    'FilePermissions',
    'SyncStatus',
    'ThumbnailInfo',
    'SyncRequest',
    'SyncResponse',
    'SyncItem',
    'SyncConflict',
    'SyncStats',
    'BatteryImpact',
    
    # Push notifications
    'PushNotification',
    'PushSubscription',
    'NotificationSettings',
    'QuietHours',
    'NotificationAction',
    
    # Media optimization
    'MediaRequest',
    'MediaResponse',
    'MediaFormat',
    'MediaMetadata',
    'OptimizationHints',
    'ProcessingStats',
    
    # Batch operations
    'BatchRequest',
    'BatchResponse',
    'BatchResult',
    'BatchStats',
    
    # Real-time updates
    'RealtimeMessage',
    'FileUpdate',
    'SyncProgress',
    'NotificationMessage',
    'SystemMessage',
    
    # Error handling
    'ErrorResponse',
    
    # Enums
    'SyncMode',
    'ConflictResolution',
    'CompressionType',
    'NotificationPriority',
    'Quality',
]


def create_device_info(device_id: str, platform: str, os_version: str, 
                      app_version: str, model: str = "") -> DeviceInfo:
    """Convenience function to create DeviceInfo message"""
    return DeviceInfo(
        device_id=device_id,
        platform=platform,
        os_version=os_version,
        app_version=app_version,
        model=model
    )


def create_auth_request(email: str, password: str, device_info: DeviceInfo,
                       totp_code: str = "", remember_device: bool = True) -> AuthRequest:
    """Convenience function to create password-based AuthRequest"""
    password_auth = PasswordAuth(
        email=email,
        password=password,
        totp_code=totp_code
    )
    
    return AuthRequest(
        password=password_auth,
        device=device_info,
        remember_device=remember_device
    )


def create_sync_request(sync_token: str, device_info: DeviceInfo,
                       mode: SyncMode = SyncMode.SYNC_MODE_INCREMENTAL) -> SyncRequest:
    """Convenience function to create SyncRequest"""
    return SyncRequest(
        sync_token=sync_token,
        device=device_info,
        mode=mode,
        options=SyncOptions(
            include_thumbnails=True,
            include_content=False,  # Content loaded separately for bandwidth optimization
            max_items=100
        )
    )


def create_media_request(file_id: str, quality: Quality = Quality.QUALITY_ADAPTIVE,
                        max_width: int = 1024, max_height: int = 1024) -> MediaRequest:
    """Convenience function to create MediaRequest"""
    format_info = MediaFormat(
        type=MediaFormat.Type.FORMAT_WEBP,
        max_width=max_width,
        max_height=max_height,
        quality=85
    )
    
    return MediaRequest(
        file_id=file_id,
        format=format_info,
        quality=quality
    )


def create_push_subscription(device_id: str, platform: str, 
                           token: str, topics: list = None) -> PushSubscription:
    """Convenience function to create PushSubscription"""
    return PushSubscription(
        device_id=device_id,
        platform=platform,
        token=token,
        topics=topics or [],
        settings=NotificationSettings(
            enabled=True,
            show_preview=True,
            play_sound=True,
            vibrate=True
        )
    )
'''
    
    try:
        with open(convenience_file, 'w') as f:
            f.write(convenience_content)
        print(f"Created convenience import file: {convenience_file}")
        return True
    except Exception as e:
        print(f"Error creating convenience file: {e}")
        return False

if __name__ == "__main__":
    print("Generating ActiveLog Mobile API Protocol Buffer files...")
    
    success = generate_protobuf_files()
    if success:
        create_convenience_imports()
        print("\n✅ Protocol Buffer generation completed successfully!")
    else:
        print("\n❌ Protocol Buffer generation failed!")
        sys.exit(1)