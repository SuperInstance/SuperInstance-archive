#!/usr/bin/env python3
"""
Generate Deployment Package for SuperInstance ML Ecosystem
Creates ready-to-deploy package for widespread adoption
"""

import os
import sys
import shutil
import tempfile
import argparse
from deployment_system import (
    DeploymentOrchestrator, 
    create_development_config, 
    create_production_config
)

def main():
    """Generate deployment package"""
    
    parser = argparse.ArgumentParser(
        description='Generate SuperInstance ML Ecosystem deployment package'
    )
    parser.add_argument(
        '--environment', 
        choices=['dev', 'staging', 'production'], 
        default='production',
        help='Target deployment environment'
    )
    parser.add_argument(
        '--output-dir', 
        default='/tmp/superinstance-ml-deployment',
        help='Output directory for deployment package'
    )
    parser.add_argument(
        '--build-image', 
        action='store_true',
        help='Build Docker image'
    )
    
    args = parser.parse_args()
    
    print(f"🚀 Generating SuperInstance ML Ecosystem deployment package")
    print(f"📦 Environment: {args.environment}")
    print(f"📂 Output: {args.output_dir}")
    
    # Create configuration
    if args.environment == 'dev':
        config = create_development_config()
    else:
        config = create_production_config()
        config.environment = args.environment
        config.deployment_name = f"superinstance-ml-{args.environment}"
    
    # Create deployment orchestrator
    orchestrator = DeploymentOrchestrator()
    
    # Generate package
    try:
        # Clean output directory
        if os.path.exists(args.output_dir):
            shutil.rmtree(args.output_dir)
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Create deployment package
        orchestrator.create_deployment_package(config, args.output_dir)
        
        # Build Docker image if requested
        if args.build_image:
            try:
                image = orchestrator.docker_deployment.build_image(
                    args.output_dir,
                    f"superinstance-ml-ecosystem:{args.environment}"
                )
                print(f"✅ Built Docker image: {image.tags}")
            except Exception as e:
                print(f"⚠️ Docker image build failed: {e}")
                print("📝 You can build it later with: docker build -t superinstance-ml-ecosystem .")
        
        print(f"\n🎉 Deployment package ready!")
        print(f"📦 Location: {args.output_dir}")
        print(f"🚀 Quick start: cd {args.output_dir} && ./scripts/deploy-docker.sh")
        print(f"📚 Documentation: {args.output_dir}/docs/README.md")
        
        # Show deployment options
        print(f"\n📋 Available deployment methods:")
        print(f"  🐳 Docker Compose: ./scripts/deploy-docker.sh")
        print(f"  ☸️ Kubernetes: ./scripts/deploy-k8s.sh")
        print(f"  ⎈ Helm: ./scripts/deploy-helm.sh")
        
        return 0
        
    except Exception as e:
        print(f"❌ Failed to generate deployment package: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())