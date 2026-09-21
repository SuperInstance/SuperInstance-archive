"""
CDN configuration and static asset optimization for ActiveLog.
Provides configuration for CloudFront, Cloudflare, and other CDN providers.
"""
import os
import hashlib
import mimetypes
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CDNConfig:
    """CDN configuration settings."""
    provider: str = "cloudfront"  # cloudfront, cloudflare, fastly
    domain: str = ""
    distribution_id: str = ""
    cache_behaviors: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    origins: List[Dict[str, Any]] = field(default_factory=list)
    custom_headers: Dict[str, str] = field(default_factory=dict)
    ssl_certificate: Optional[str] = None
    price_class: str = "PriceClass_100"
    
    def __post_init__(self):
        if not self.cache_behaviors:
            self.cache_behaviors = self._default_cache_behaviors()
        
        if not self.origins:
            self.origins = self._default_origins()
    
    def _default_cache_behaviors(self) -> Dict[str, Dict[str, Any]]:
        """Default cache behaviors for different content types."""
        return {
            # Static assets - long cache
            "/static/*": {
                "ttl": 31536000,  # 1 year
                "compress": True,
                "cache_policy": "static_assets",
                "allowed_methods": ["GET", "HEAD"],
                "cached_methods": ["GET", "HEAD"]
            },
            
            # Images - long cache
            "/images/*": {
                "ttl": 2592000,  # 30 days
                "compress": False,  # Already compressed
                "cache_policy": "images",
                "allowed_methods": ["GET", "HEAD"],
                "cached_methods": ["GET", "HEAD"]
            },
            
            # API responses - short cache
            "/api/v1/files": {
                "ttl": 300,  # 5 minutes
                "compress": True,
                "cache_policy": "api_responses",
                "allowed_methods": ["GET", "HEAD", "OPTIONS"],
                "cached_methods": ["GET", "HEAD"],
                "cache_key_parameters": ["user_id", "page", "limit"]
            },
            
            # User avatars - medium cache
            "/avatars/*": {
                "ttl": 604800,  # 7 days
                "compress": False,
                "cache_policy": "user_content",
                "allowed_methods": ["GET", "HEAD"],
                "cached_methods": ["GET", "HEAD"]
            },
            
            # File previews - medium cache
            "/previews/*": {
                "ttl": 86400,  # 24 hours
                "compress": True,
                "cache_policy": "previews",
                "allowed_methods": ["GET", "HEAD"],
                "cached_methods": ["GET", "HEAD"]
            },
            
            # Default behavior
            "/*": {
                "ttl": 0,  # No cache
                "compress": True,
                "cache_policy": "dynamic",
                "allowed_methods": ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
                "cached_methods": ["GET", "HEAD"]
            }
        }
    
    def _default_origins(self) -> List[Dict[str, Any]]:
        """Default origin configurations."""
        return [
            {
                "id": "api-origin",
                "domain": "api.activelog.com",
                "protocol": "https",
                "path": "/",
                "custom_headers": {
                    "X-Forwarded-Host": "{domain_name}"
                }
            },
            {
                "id": "static-origin",
                "domain": "static.activelog.com",
                "protocol": "https",
                "path": "/static",
                "custom_headers": {}
            }
        ]


class StaticAssetOptimizer:
    """Optimizes static assets for CDN delivery."""
    
    def __init__(self, asset_dir: str, output_dir: str):
        self.asset_dir = Path(asset_dir)
        self.output_dir = Path(output_dir)
        self.asset_manifest = {}
        self.compression_types = ['br', 'gzip']
    
    def generate_asset_manifest(self) -> Dict[str, Any]:
        """Generate manifest of all static assets with hashes."""
        manifest = {
            "assets": {},
            "generated_at": datetime.utcnow().isoformat(),
            "version": self._get_version_hash()
        }
        
        for asset_file in self.asset_dir.rglob('*'):
            if asset_file.is_file():
                relative_path = asset_file.relative_to(self.asset_dir)
                
                # Calculate file hash
                file_hash = self._calculate_file_hash(asset_file)
                
                # Generate versioned filename
                versioned_name = self._create_versioned_name(relative_path, file_hash)
                
                # Get content type
                content_type = mimetypes.guess_type(str(asset_file))[0]
                
                manifest["assets"][str(relative_path)] = {
                    "hash": file_hash,
                    "versioned_path": str(versioned_name),
                    "size": asset_file.stat().st_size,
                    "content_type": content_type,
                    "last_modified": datetime.fromtimestamp(
                        asset_file.stat().st_mtime
                    ).isoformat(),
                    "compressed_versions": []
                }
        
        return manifest
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:12]  # Use first 12 chars
    
    def _create_versioned_name(self, original_path: Path, file_hash: str) -> Path:
        """Create versioned filename with hash."""
        stem = original_path.stem
        suffix = original_path.suffix
        parent = original_path.parent
        
        versioned_name = f"{stem}.{file_hash}{suffix}"
        return parent / versioned_name
    
    def _get_version_hash(self) -> str:
        """Get version hash for entire asset collection."""
        all_files_data = []
        for asset_file in sorted(self.asset_dir.rglob('*')):
            if asset_file.is_file():
                all_files_data.append(f"{asset_file.name}:{asset_file.stat().st_mtime}")
        
        combined = "".join(all_files_data)
        return hashlib.sha256(combined.encode()).hexdigest()[:12]
    
    def optimize_and_compress_assets(self) -> Dict[str, Any]:
        """Optimize and compress all assets."""
        import subprocess
        from PIL import Image
        
        manifest = self.generate_asset_manifest()
        
        for original_path, asset_info in manifest["assets"].items():
            source_file = self.asset_dir / original_path
            versioned_path = Path(asset_info["versioned_path"])
            output_file = self.output_dir / versioned_path
            
            # Create output directory
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Optimize based on file type
            try:
                if source_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    self._optimize_image(source_file, output_file)
                elif source_file.suffix.lower() in ['.js', '.css', '.html']:
                    self._optimize_text_asset(source_file, output_file)
                else:
                    # Copy as-is
                    output_file.write_bytes(source_file.read_bytes())
                
                # Create compressed versions
                compressed_versions = self._create_compressed_versions(output_file)
                asset_info["compressed_versions"] = compressed_versions
                
                logger.info(f"Optimized asset: {original_path}")
                
            except Exception as e:
                logger.error(f"Failed to optimize {original_path}: {e}")
                # Copy original on failure
                output_file.write_bytes(source_file.read_bytes())
        
        # Save manifest
        manifest_file = self.output_dir / "asset-manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
    
    def _optimize_image(self, source: Path, output: Path):
        """Optimize image files."""
        try:
            from PIL import Image
            
            with Image.open(source) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    if source.suffix.lower() in ['.jpg', '.jpeg']:
                        # Convert to RGB for JPEG
                        img = img.convert('RGB')
                
                # Optimize settings based on format
                save_kwargs = {'optimize': True}
                
                if source.suffix.lower() in ['.jpg', '.jpeg']:
                    save_kwargs['quality'] = 85
                    save_kwargs['progressive'] = True
                elif source.suffix.lower() == '.png':
                    save_kwargs['compress_level'] = 9
                
                img.save(output, **save_kwargs)
        
        except ImportError:
            # Pillow not available, copy as-is
            output.write_bytes(source.read_bytes())
        except Exception as e:
            logger.error(f"Image optimization failed for {source}: {e}")
            output.write_bytes(source.read_bytes())
    
    def _optimize_text_asset(self, source: Path, output: Path):
        """Optimize text-based assets (JS, CSS, HTML)."""
        content = source.read_text(encoding='utf-8')
        
        if source.suffix.lower() == '.js':
            # Basic JS minification (remove comments and extra whitespace)
            optimized = self._minify_js(content)
        elif source.suffix.lower() == '.css':
            # Basic CSS minification
            optimized = self._minify_css(content)
        else:
            optimized = content
        
        output.write_text(optimized, encoding='utf-8')
    
    def _minify_js(self, content: str) -> str:
        """Basic JavaScript minification."""
        # This is a simple implementation - in production, use a proper minifier
        import re
        
        # Remove single-line comments (not in strings)
        content = re.sub(r'^\s*//.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r';\s*}', '}', content)
        content = re.sub(r'{\s*', '{', content)
        content = re.sub(r'}\s*', '}', content)
        
        return content.strip()
    
    def _minify_css(self, content: str) -> str:
        """Basic CSS minification."""
        import re
        
        # Remove comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r';\s*}', '}', content)
        content = re.sub(r'{\s*', '{', content)
        content = re.sub(r'}\s*', '}', content)
        content = re.sub(r':\s*', ':', content)
        content = re.sub(r';\s*', ';', content)
        
        return content.strip()
    
    def _create_compressed_versions(self, file_path: Path) -> List[str]:
        """Create compressed versions of the file."""
        import gzip
        import brotli
        
        compressed_versions = []
        original_content = file_path.read_bytes()
        
        # Create gzip version
        gzip_path = file_path.with_suffix(file_path.suffix + '.gz')
        with gzip.open(gzip_path, 'wb', compresslevel=9) as f:
            f.write(original_content)
        compressed_versions.append('gzip')
        
        # Create brotli version
        try:
            br_path = file_path.with_suffix(file_path.suffix + '.br')
            compressed = brotli.compress(original_content, quality=11)
            br_path.write_bytes(compressed)
            compressed_versions.append('brotli')
        except ImportError:
            logger.warning("Brotli not available, skipping brotli compression")
        
        return compressed_versions


class CloudFrontConfig:
    """CloudFront-specific configuration generator."""
    
    @staticmethod
    def generate_distribution_config(cdn_config: CDNConfig) -> Dict[str, Any]:
        """Generate CloudFront distribution configuration."""
        return {
            "DistributionConfig": {
                "CallerReference": f"activelog-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "DefaultRootObject": "index.html",
                "Comment": "ActiveLog CDN Distribution",
                "Enabled": True,
                "PriceClass": cdn_config.price_class,
                
                "Origins": {
                    "Quantity": len(cdn_config.origins),
                    "Items": [
                        {
                            "Id": origin["id"],
                            "DomainName": origin["domain"],
                            "CustomOriginConfig": {
                                "HTTPPort": 80,
                                "HTTPSPort": 443,
                                "OriginProtocolPolicy": "https-only",
                                "OriginSslProtocols": {
                                    "Quantity": 3,
                                    "Items": ["TLSv1", "TLSv1.1", "TLSv1.2"]
                                }
                            },
                            "OriginPath": origin.get("path", "")
                        }
                        for origin in cdn_config.origins
                    ]
                },
                
                "DefaultCacheBehavior": CloudFrontConfig._create_cache_behavior(
                    cdn_config.cache_behaviors.get("/*", {})
                ),
                
                "CacheBehaviors": {
                    "Quantity": len(cdn_config.cache_behaviors) - 1,
                    "Items": [
                        {
                            "PathPattern": path,
                            **CloudFrontConfig._create_cache_behavior(behavior)
                        }
                        for path, behavior in cdn_config.cache_behaviors.items()
                        if path != "/*"
                    ]
                },
                
                "Aliases": {
                    "Quantity": 1 if cdn_config.domain else 0,
                    "Items": [cdn_config.domain] if cdn_config.domain else []
                },
                
                "ViewerCertificate": {
                    "CloudFrontDefaultCertificate": not cdn_config.ssl_certificate,
                    "ACMCertificateArn": cdn_config.ssl_certificate,
                    "SSLSupportMethod": "sni-only" if cdn_config.ssl_certificate else None,
                    "MinimumProtocolVersion": "TLSv1.2_2021"
                },
                
                "WebACLId": "",
                "HttpVersion": "http2",
                "IsIPV6Enabled": True
            }
        }
    
    @staticmethod
    def _create_cache_behavior(behavior: Dict[str, Any]) -> Dict[str, Any]:
        """Create CloudFront cache behavior configuration."""
        return {
            "TargetOriginId": "api-origin",
            "ViewerProtocolPolicy": "redirect-to-https",
            "MinTTL": 0,
            "ForwardedValues": {
                "QueryString": True,
                "Cookies": {"Forward": "none"},
                "Headers": {
                    "Quantity": 3,
                    "Items": ["Accept", "Accept-Encoding", "Authorization"]
                }
            },
            "DefaultTTL": behavior.get("ttl", 0),
            "MaxTTL": behavior.get("ttl", 0),
            "Compress": behavior.get("compress", True),
            "AllowedMethods": {
                "Quantity": len(behavior.get("allowed_methods", ["GET", "HEAD"])),
                "Items": behavior.get("allowed_methods", ["GET", "HEAD"]),
                "CachedMethods": {
                    "Quantity": len(behavior.get("cached_methods", ["GET", "HEAD"])),
                    "Items": behavior.get("cached_methods", ["GET", "HEAD"])
                }
            }
        }


class CDNUrlGenerator:
    """Generates CDN URLs for assets."""
    
    def __init__(self, cdn_domain: str, asset_manifest: Dict[str, Any]):
        self.cdn_domain = cdn_domain.rstrip('/')
        self.asset_manifest = asset_manifest
    
    def get_asset_url(self, asset_path: str, use_versioned: bool = True) -> str:
        """Get CDN URL for an asset."""
        if use_versioned and asset_path in self.asset_manifest.get("assets", {}):
            versioned_path = self.asset_manifest["assets"][asset_path]["versioned_path"]
            return f"{self.cdn_domain}/{versioned_path}"
        else:
            return f"{self.cdn_domain}/{asset_path.lstrip('/')}"
    
    def get_preload_links(self, critical_assets: List[str]) -> List[str]:
        """Generate preload link headers for critical assets."""
        preload_links = []
        
        for asset_path in critical_assets:
            url = self.get_asset_url(asset_path)
            
            # Determine resource type based on file extension
            if asset_path.endswith('.css'):
                rel_type = "style"
            elif asset_path.endswith('.js'):
                rel_type = "script"
            elif asset_path.endswith(('.woff', '.woff2', '.ttf', '.otf')):
                rel_type = "font"
            elif asset_path.endswith(('.jpg', '.jpeg', '.png', '.webp', '.svg')):
                rel_type = "image"
            else:
                continue
            
            preload_links.append(f'<{url}>; rel=preload; as={rel_type}')
        
        return preload_links


def create_asset_optimizer_cli():
    """Create CLI interface for asset optimization."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimize static assets for CDN")
    parser.add_argument("--input", required=True, help="Input directory with assets")
    parser.add_argument("--output", required=True, help="Output directory for optimized assets")
    parser.add_argument("--config", help="CDN configuration file")
    
    args = parser.parse_args()
    
    optimizer = StaticAssetOptimizer(args.input, args.output)
    manifest = optimizer.optimize_and_compress_assets()
    
    print(f"Optimized {len(manifest['assets'])} assets")
    print(f"Manifest saved to {args.output}/asset-manifest.json")
    
    return manifest


# Example usage configurations
EXAMPLE_CONFIGS = {
    "development": {
        "provider": "none",
        "domain": "localhost:8000",
        "cache_behaviors": {
            "/*": {"ttl": 0, "compress": False}
        }
    },
    
    "production_cloudfront": {
        "provider": "cloudfront",
        "domain": "cdn.activelog.com",
        "distribution_id": "E1234567890ABC",
        "price_class": "PriceClass_100",
        "ssl_certificate": "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012"
    },
    
    "production_cloudflare": {
        "provider": "cloudflare",
        "domain": "cdn.activelog.com",
        "zone_id": "abcdef1234567890",
        "custom_headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY"
        }
    }
}