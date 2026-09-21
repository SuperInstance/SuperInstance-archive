#!/usr/bin/env python3

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecretsRotationCLI:
    def __init__(self, config_file: str = "configs/rotation-config.yaml"):
        self.config = self._load_config(config_file)
        self.api_base_url = f"http://localhost:{self.config['service']['port']}/api/v1"
        self.session = None

    def _load_config(self, config_file: str) -> Dict:
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        session = await self._get_session()
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            async with session.request(method, url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Request failed: {response.status} - {error_text}")
                    return {"error": error_text, "status": response.status}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"error": str(e)}

    async def list_secrets(self) -> None:
        """List all configured secrets and their status."""
        print("Fetching secrets status...")
        
        response = await self._make_request("GET", "/secrets/status")
        if "error" in response:
            print(f"Error: {response['error']}")
            return

        stats = response.get("stats", {})
        recent_rotations = response.get("recent_rotations", [])

        print(f"\n📊 Secrets Overview:")
        print(f"   Total Secrets: {stats.get('total_secrets', 0)}")
        print(f"   Expiring Soon (7 days): {stats.get('expiring_soon', 0)}")
        print(f"   Expired: {stats.get('expired', 0)}")
        print(f"   Scheduler Running: {response.get('scheduler_running', False)}")

        if recent_rotations:
            print(f"\n🔄 Recent Rotations (Last 24 hours):")
            for rotation in recent_rotations:
                status_emoji = "✅" if rotation['status'] == 'success' else "❌"
                rotated_at = datetime.fromisoformat(rotation['rotated_at'].replace('Z', '+00:00'))
                print(f"   {status_emoji} {rotation['secret_name']} - {rotated_at.strftime('%Y-%m-%d %H:%M:%S')}")

    async def get_secret_info(self, secret_name: str) -> None:
        """Get information about a specific secret."""
        print(f"Fetching information for secret: {secret_name}")
        
        response = await self._make_request("GET", f"/secrets/{secret_name}/current")
        if "error" in response:
            print(f"Error: {response['error']}")
            return

        print(f"\n🔐 Secret: {response['name']}")
        print(f"   Version: {response['version']}")
        print(f"   Created: {response['created_at']}")
        if response.get('expires_at'):
            expires_at = datetime.fromisoformat(response['expires_at'].replace('Z', '+00:00'))
            now = datetime.now()
            if expires_at > now:
                days_until_expiry = (expires_at - now).days
                print(f"   Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} ({days_until_expiry} days)")
            else:
                print(f"   ⚠️  EXPIRED: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Active: {response['is_active']}")

    async def rotate_secret(self, secret_name: str) -> None:
        """Manually rotate a specific secret."""
        print(f"Initiating rotation for secret: {secret_name}")
        
        response = await self._make_request("POST", f"/secrets/{secret_name}/rotate")
        if "error" in response:
            print(f"Error: {response['error']}")
            return

        print(f"✅ Secret rotated successfully!")
        print(f"   Secret: {response['secret_name']}")
        print(f"   Old Version: {response['old_version']}")
        print(f"   New Version: {response['new_version']}")
        print(f"   Status: {response['status']}")
        print(f"   Message: {response['message']}")
        print(f"   Rotated At: {response['rotated_at']}")

    async def create_secret_config(self, name: str, secret_type: str, 
                                 interval_days: int = 30, auto_rotate: bool = True,
                                 environments: List[str] = None) -> None:
        """Create or update a secret configuration."""
        if environments is None:
            environments = ["production"]

        config_data = {
            "name": name,
            "type": secret_type,
            "rotation_interval_days": interval_days,
            "auto_rotate": auto_rotate,
            "backup_versions": 3,
            "notification_before_expiry_hours": 24,
            "environments": environments
        }

        print(f"Creating/updating secret configuration for: {name}")
        
        response = await self._make_request("POST", "/secrets/config", config_data)
        if "error" in response:
            print(f"Error: {response['error']}")
            return

        print(f"✅ Secret configuration created/updated successfully!")
        print(f"   Name: {name}")
        print(f"   Type: {secret_type}")
        print(f"   Rotation Interval: {interval_days} days")
        print(f"   Auto Rotate: {auto_rotate}")
        print(f"   Environments: {', '.join(environments)}")

    async def emergency_rotation(self) -> None:
        """Perform emergency rotation of all auto-rotate secrets."""
        print("⚠️  Initiating EMERGENCY ROTATION of all auto-rotate secrets...")
        print("This will rotate ALL secrets configured for automatic rotation.")
        
        confirm = input("Are you sure you want to proceed? (type 'YES' to confirm): ")
        if confirm != "YES":
            print("Emergency rotation cancelled.")
            return

        response = await self._make_request("POST", "/secrets/emergency-rotation")
        if "error" in response:
            print(f"Error: {response['error']}")
            return

        rotated_secrets = response.get("rotated_secrets", [])
        successful = [s for s in rotated_secrets if s.get("status") == "success"]
        failed = [s for s in rotated_secrets if s.get("status") == "failed"]

        print(f"\n🚨 Emergency Rotation Complete!")
        print(f"   Successful: {len(successful)}")
        print(f"   Failed: {len(failed)}")

        if successful:
            print(f"\n✅ Successfully Rotated:")
            for secret in successful:
                print(f"   - {secret['secret_name']} (v{secret.get('old_version', 'N/A')} → v{secret['new_version']})")

        if failed:
            print(f"\n❌ Failed Rotations:")
            for secret in failed:
                print(f"   - {secret['secret_name']}: {secret.get('message', 'Unknown error')}")

    async def test_connection(self) -> None:
        """Test connection to the secrets rotation service."""
        print("Testing connection to secrets rotation service...")
        
        response = await self._make_request("GET", "/secrets/status")
        if "error" in response:
            print(f"❌ Connection failed: {response['error']}")
            return

        print("✅ Connection successful!")
        print(f"   Service running on: {self.api_base_url}")
        print(f"   Scheduler status: {'Running' if response.get('scheduler_running') else 'Stopped'}")

    async def close(self):
        if self.session:
            await self.session.close()

async def main():
    parser = argparse.ArgumentParser(description="ActiveLog Secrets Rotation CLI")
    parser.add_argument("--config", default="configs/rotation-config.yaml", 
                       help="Configuration file path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all secrets and their status")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get information about a specific secret")
    get_parser.add_argument("secret_name", help="Name of the secret")
    
    # Rotate command
    rotate_parser = subparsers.add_parser("rotate", help="Manually rotate a specific secret")
    rotate_parser.add_argument("secret_name", help="Name of the secret to rotate")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create or update secret configuration")
    create_parser.add_argument("name", help="Secret name")
    create_parser.add_argument("type", help="Secret type (password, api_key, jwt_secret, etc.)")
    create_parser.add_argument("--interval", type=int, default=30, 
                              help="Rotation interval in days (default: 30)")
    create_parser.add_argument("--no-auto-rotate", action="store_true",
                              help="Disable automatic rotation")
    create_parser.add_argument("--environments", nargs="+", default=["production"],
                              help="Target environments (default: production)")
    
    # Emergency command
    emergency_parser = subparsers.add_parser("emergency", help="Emergency rotation of all secrets")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test connection to rotation service")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    cli = SecretsRotationCLI(args.config)
    
    try:
        if args.command == "list":
            await cli.list_secrets()
        elif args.command == "get":
            await cli.get_secret_info(args.secret_name)
        elif args.command == "rotate":
            await cli.rotate_secret(args.secret_name)
        elif args.command == "create":
            await cli.create_secret_config(
                args.name, 
                args.type,
                args.interval,
                not args.no_auto_rotate,
                args.environments
            )
        elif args.command == "emergency":
            await cli.emergency_rotation()
        elif args.command == "test":
            await cli.test_connection()
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"Command failed: {e}")
    finally:
        await cli.close()

if __name__ == "__main__":
    asyncio.run(main())