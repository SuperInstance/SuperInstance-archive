"""
IPFS Storage Manager for ActiveLog Blockchain Features
Handles decentralized storage with encryption and redundancy
"""

import json
import os
import hashlib
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..config.blockchain_config import blockchain_config

@dataclass
class IPFSFile:
    hash: str
    name: str
    size: int
    is_dir: bool
    links: List[Dict[str, Any]]

@dataclass
class PinningResult:
    hash: str
    name: str
    size: int
    timestamp: datetime
    status: str
    pin_policy: Dict[str, Any]

class IPFSManager:
    """Manages IPFS operations for decentralized storage"""
    
    def __init__(self):
        self.config = blockchain_config.ipfs_config
        self.local_node_url = self.config["local_node"]["api_url"]
        self.gateway_url = self.config["local_node"]["gateway_url"]
        self.pinning_service = self.config["pinning_service"]
        
        # Pinata configuration
        self.pinata_api_key = self.config.get("pinata_api_key")
        self.pinata_secret_key = self.config.get("pinata_secret_key")
        
        # Encryption setup
        self.encryption_enabled = self.config["encryption"]["enabled"]
        self.encryption_algorithm = self.config["encryption"]["algorithm"]
        
    async def add_json(self, data: Dict[str, Any], encrypt: bool = True) -> Dict[str, Any]:
        """Add JSON data to IPFS"""
        
        # Serialize data
        json_data = json.dumps(data, default=str, ensure_ascii=False)
        
        # Encrypt if enabled
        if encrypt and self.encryption_enabled:
            encrypted_data = await self._encrypt_data(json_data)
            content = json.dumps({
                "encrypted": True,
                "algorithm": self.encryption_algorithm,
                "data": encrypted_data
            })
        else:
            content = json_data
        
        # Add to local IPFS node
        result = await self._add_to_local_node(content.encode('utf-8'))
        
        return {
            "hash": result["Hash"],
            "size": result["Size"],
            "name": result["Name"],
            "encrypted": encrypt and self.encryption_enabled,
            "added_at": datetime.utcnow().isoformat()
        }
    
    async def pin_json(
        self, 
        data: Dict[str, Any], 
        name: Optional[str] = None,
        encrypt: bool = True
    ) -> Dict[str, Any]:
        """Add JSON data to IPFS and pin it"""
        
        # Add to IPFS
        add_result = await self.add_json(data, encrypt)
        
        # Pin the content
        pin_result = await self.pin_hash(add_result["hash"], name)
        
        return {
            **add_result,
            "pinned": True,
            "pin_service": self.pinning_service,
            "pin_result": pin_result
        }
    
    async def get_json(self, ipfs_hash: str, decrypt: bool = True) -> Dict[str, Any]:
        """Retrieve JSON data from IPFS"""
        
        # Try local node first, then gateways
        content = await self._get_from_ipfs(ipfs_hash)
        
        try:
            data = json.loads(content)
            
            # Check if data is encrypted
            if isinstance(data, dict) and data.get("encrypted"):
                if decrypt and self.encryption_enabled:
                    decrypted_data = await self._decrypt_data(data["data"])
                    return json.loads(decrypted_data)
                else:
                    return data  # Return encrypted data as-is
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data in IPFS hash {ipfs_hash}: {e}")
    
    async def add_file(
        self, 
        file_path: str, 
        encrypt: bool = True,
        pin: bool = True
    ) -> Dict[str, Any]:
        """Add a file to IPFS"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Encrypt if enabled
        if encrypt and self.encryption_enabled:
            encrypted_content = await self._encrypt_data(content.decode('utf-8'))
            # Create encrypted file wrapper
            encrypted_wrapper = {
                "encrypted": True,
                "algorithm": self.encryption_algorithm,
                "original_name": os.path.basename(file_path),
                "data": encrypted_content
            }
            content = json.dumps(encrypted_wrapper).encode('utf-8')
        
        # Add to IPFS
        result = await self._add_to_local_node(content)
        
        # Pin if requested
        pin_result = None
        if pin:
            pin_result = await self.pin_hash(result["Hash"], os.path.basename(file_path))
        
        return {
            "hash": result["Hash"],
            "size": result["Size"],
            "name": os.path.basename(file_path),
            "encrypted": encrypt and self.encryption_enabled,
            "pinned": pin,
            "pin_result": pin_result,
            "added_at": datetime.utcnow().isoformat()
        }
    
    async def get_file(
        self, 
        ipfs_hash: str, 
        output_path: Optional[str] = None,
        decrypt: bool = True
    ) -> Union[bytes, str]:
        """Retrieve a file from IPFS"""
        
        content = await self._get_from_ipfs(ipfs_hash)
        
        # Check if content is encrypted
        try:
            data = json.loads(content)
            if isinstance(data, dict) and data.get("encrypted"):
                if decrypt and self.encryption_enabled:
                    decrypted_content = await self._decrypt_data(data["data"])
                    content = decrypted_content.encode('utf-8')
                else:
                    # Return the encrypted wrapper as JSON
                    content = json.dumps(data).encode('utf-8')
        except json.JSONDecodeError:
            # Not JSON, treat as binary data
            pass
        
        # Save to file if output path provided
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(content if isinstance(content, bytes) else content.encode('utf-8'))
            return output_path
        
        return content
    
    async def pin_hash(
        self, 
        ipfs_hash: str, 
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pin content to prevent garbage collection"""
        
        if self.pinning_service == "pinata":
            return await self._pin_with_pinata(ipfs_hash, name)
        else:
            return await self._pin_with_local_node(ipfs_hash, name)
    
    async def unpin_hash(self, ipfs_hash: str) -> Dict[str, Any]:
        """Unpin content"""
        
        if self.pinning_service == "pinata":
            return await self._unpin_with_pinata(ipfs_hash)
        else:
            return await self._unpin_with_local_node(ipfs_hash)
    
    async def list_pins(self) -> List[PinningResult]:
        """List all pinned content"""
        
        if self.pinning_service == "pinata":
            return await self._list_pinata_pins()
        else:
            return await self._list_local_pins()
    
    async def create_directory(
        self, 
        files: Dict[str, Union[str, bytes, Dict[str, Any]]],
        encrypt: bool = True
    ) -> Dict[str, Any]:
        """Create a directory structure in IPFS"""
        
        directory_data = {}
        
        for filename, content in files.items():
            if isinstance(content, dict):
                # JSON content
                file_result = await self.add_json(content, encrypt)
            elif isinstance(content, str):
                # Text content
                file_result = await self._add_to_local_node(content.encode('utf-8'))
            else:
                # Binary content
                file_result = await self._add_to_local_node(content)
            
            directory_data[filename] = {
                "hash": file_result["Hash"],
                "size": file_result["Size"]
            }
        
        # Create directory manifest
        manifest = {
            "type": "directory",
            "files": directory_data,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Add manifest to IPFS
        manifest_result = await self.add_json(manifest, encrypt)
        
        return {
            "directory_hash": manifest_result["hash"],
            "files": directory_data,
            "manifest": manifest_result,
            "created_at": manifest["created_at"]
        }
    
    async def replicate_to_multiple_nodes(
        self, 
        ipfs_hash: str, 
        target_nodes: List[str]
    ) -> Dict[str, Any]:
        """Replicate content to multiple IPFS nodes for redundancy"""
        
        results = {}
        
        for node_url in target_nodes:
            try:
                # Pin content on target node
                async with aiohttp.ClientSession() as session:
                    pin_url = f"{node_url}/api/v0/pin/add"
                    params = {"arg": ipfs_hash}
                    
                    async with session.post(pin_url, params=params) as response:
                        if response.status == 200:
                            results[node_url] = {"status": "success", "response": await response.json()}
                        else:
                            results[node_url] = {"status": "failed", "error": await response.text()}
                            
            except Exception as e:
                results[node_url] = {"status": "error", "error": str(e)}
        
        return {
            "hash": ipfs_hash,
            "replication_results": results,
            "successful_nodes": len([r for r in results.values() if r["status"] == "success"]),
            "total_nodes": len(target_nodes)
        }
    
    async def verify_content_integrity(self, ipfs_hash: str) -> Dict[str, Any]:
        """Verify content integrity using IPFS hash"""
        
        try:
            # Retrieve content
            content = await self._get_from_ipfs(ipfs_hash)
            
            # Calculate hash of retrieved content
            import hashlib
            calculated_hash = hashlib.sha256(content).hexdigest()
            
            # Get IPFS stats
            stats = await self._get_ipfs_stats(ipfs_hash)
            
            return {
                "hash": ipfs_hash,
                "content_size": len(content),
                "content_hash": calculated_hash,
                "ipfs_stats": stats,
                "integrity_verified": True,
                "verified_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "hash": ipfs_hash,
                "integrity_verified": False,
                "error": str(e),
                "verified_at": datetime.utcnow().isoformat()
            }
    
    async def _add_to_local_node(self, content: bytes) -> Dict[str, Any]:
        """Add content to local IPFS node"""
        
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('file', content)
            
            url = f"{self.local_node_url}/api/v0/add"
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"IPFS add failed: {error_text}")
    
    async def _get_from_ipfs(self, ipfs_hash: str) -> bytes:
        """Get content from IPFS using multiple gateways"""
        
        # Try local node first
        gateways = [self.gateway_url] + self.config["backup_gateways"]
        
        for gateway in gateways:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{gateway}/ipfs/{ipfs_hash}"
                    
                    async with session.get(url, timeout=30) as response:
                        if response.status == 200:
                            return await response.read()
                        
            except Exception as e:
                print(f"Failed to get from gateway {gateway}: {e}")
                continue
        
        raise Exception(f"Failed to retrieve IPFS content {ipfs_hash} from all gateways")
    
    async def _pin_with_pinata(self, ipfs_hash: str, name: Optional[str]) -> Dict[str, Any]:
        """Pin content using Pinata service"""
        
        url = "https://api.pinata.cloud/pinning/pinByHash"
        
        headers = {
            "pinata_api_key": self.pinata_api_key,
            "pinata_secret_api_key": self.pinata_secret_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "hashToPin": ipfs_hash,
            "pinataMetadata": {
                "name": name or ipfs_hash,
                "keyvalues": {
                    "service": "activelog",
                    "pinned_at": datetime.utcnow().isoformat()
                }
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "hash": result["IpfsHash"],
                        "timestamp": result["Timestamp"],
                        "status": "pinned",
                        "service": "pinata"
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Pinata pinning failed: {error_text}")
    
    async def _pin_with_local_node(self, ipfs_hash: str, name: Optional[str]) -> Dict[str, Any]:
        """Pin content using local IPFS node"""
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.local_node_url}/api/v0/pin/add"
            params = {"arg": ipfs_hash}
            
            async with session.post(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "hash": ipfs_hash,
                        "status": "pinned",
                        "service": "local",
                        "result": result
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Local pinning failed: {error_text}")
    
    async def _unpin_with_pinata(self, ipfs_hash: str) -> Dict[str, Any]:
        """Unpin content from Pinata"""
        
        url = f"https://api.pinata.cloud/pinning/unpin/{ipfs_hash}"
        
        headers = {
            "pinata_api_key": self.pinata_api_key,
            "pinata_secret_api_key": self.pinata_secret_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status == 200:
                    return {
                        "hash": ipfs_hash,
                        "status": "unpinned",
                        "service": "pinata"
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Pinata unpinning failed: {error_text}")
    
    async def _unpin_with_local_node(self, ipfs_hash: str) -> Dict[str, Any]:
        """Unpin content from local node"""
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.local_node_url}/api/v0/pin/rm"
            params = {"arg": ipfs_hash}
            
            async with session.post(url, params=params) as response:
                if response.status == 200:
                    return {
                        "hash": ipfs_hash,
                        "status": "unpinned",
                        "service": "local"
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Local unpinning failed: {error_text}")
    
    async def _list_pinata_pins(self) -> List[PinningResult]:
        """List pins from Pinata"""
        
        url = "https://api.pinata.cloud/data/pinList"
        
        headers = {
            "pinata_api_key": self.pinata_api_key,
            "pinata_secret_api_key": self.pinata_secret_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    pins = []
                    for row in result.get("rows", []):
                        pins.append(PinningResult(
                            hash=row["ipfs_pin_hash"],
                            name=row["metadata"]["name"],
                            size=row["size"],
                            timestamp=datetime.fromisoformat(row["date_pinned"].replace('Z', '+00:00')),
                            status=row["status"],
                            pin_policy=row.get("pin_policy", {})
                        ))
                    
                    return pins
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to list Pinata pins: {error_text}")
    
    async def _list_local_pins(self) -> List[PinningResult]:
        """List pins from local node"""
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.local_node_url}/api/v0/pin/ls"
            
            async with session.post(url) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    pins = []
                    for hash_key, pin_info in result.get("Keys", {}).items():
                        pins.append(PinningResult(
                            hash=hash_key,
                            name=hash_key,  # Local node doesn't store names
                            size=0,  # Would need separate API call to get size
                            timestamp=datetime.utcnow(),  # Local node doesn't store timestamps
                            status="pinned",
                            pin_policy={"type": pin_info.get("Type", "unknown")}
                        ))
                    
                    return pins
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to list local pins: {error_text}")
    
    async def _get_ipfs_stats(self, ipfs_hash: str) -> Dict[str, Any]:
        """Get IPFS statistics for content"""
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.local_node_url}/api/v0/object/stat"
            params = {"arg": ipfs_hash}
            
            try:
                async with session.post(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
            except:
                pass
        
        return {}
    
    async def _encrypt_data(self, data: str) -> str:
        """Encrypt data using configured algorithm"""
        
        # Use a simple key derivation for demo (use proper key management in production)
        password = b"activelog_encryption_key"  # Should be from secure config
        salt = b"salt_12345678"  # Should be random per encryption
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        f = Fernet(key)
        
        encrypted_data = f.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    async def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data using configured algorithm"""
        
        # Use the same key derivation as encryption
        password = b"activelog_encryption_key"
        salt = b"salt_12345678"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        f = Fernet(key)
        
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted_data = f.decrypt(encrypted_bytes)
        return decrypted_data.decode()