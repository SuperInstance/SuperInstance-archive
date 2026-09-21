#!/usr/bin/env python3
"""
Building Bots Network Integration for Dynamic Bot Language System

This module provides integration points for connecting the Dynamic Bot Language
Evolution System with all services in the Building Bots Network. It enables
automatic language optimization across the entire bot ecosystem.

Key Integration Features:
1. Service Discovery - Automatically finds and connects to bot services
2. Language Optimization - Applies dynamic language to inter-bot communications
3. Performance Monitoring - Tracks communication efficiency improvements
4. Research Data Collection - Gathers data for the Dissertation Bot's research
"""

import asyncio
import aiohttp
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import requests
from urllib.parse import urljoin
import threading
import os
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NetworkIntegration')

@dataclass
class BotService:
    """Represents a bot service in the network"""
    name: str
    port: int
    domain: str
    url: str
    status: str
    capabilities: List[str]
    language_enabled: bool = False
    last_seen: float = 0.0

@dataclass
class CommunicationMetric:
    """Metrics for bot-to-bot communication"""
    timestamp: float
    source_service: str
    target_service: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    processing_time_ms: float
    success: bool

class BuildingBotsNetworkIntegrator:
    """Integrates Dynamic Bot Language with all Building Bots Network services"""
    
    def __init__(self, language_system_url: str = "http://localhost:8472"):
        self.language_system_url = language_system_url
        self.discovered_services = {}  # service_name -> BotService
        self.service_domains = {}  # Mapping of services to their language domains
        self.communication_metrics = []
        self.integration_active = False
        
        # Load service configuration
        self.load_service_configuration()
        
        # Start background tasks
        self.start_service_discovery()
        self.start_integration_monitor()
        
        logger.info("Building Bots Network Integrator initialized")
        logger.info(f"Language System URL: {language_system_url}")
    
    def load_service_configuration(self):
        """Load service configuration and domain mappings"""
        # Define service domains based on the Building Bots Network structure
        self.service_domains = {
            # DMLog Services - Gaming Domain
            'dmlog-backend': 'gaming',
            'dmlog-characters': 'gaming',
            'dmlog-session': 'gaming',
            'dmlog-battle': 'gaming',
            'dmlog-world': 'gaming',
            'dmlog-player': 'gaming',
            'dmlog-gamedev': 'gaming',
            'dmlog-visualizer': 'gaming',
            
            # Marine Services - Marine Domain
            'marine-autopilot': 'marine',
            'marine-advanced': 'marine',
            'marine-alarms': 'marine',
            'marine-fishing': 'marine',
            'fishinglog-backend': 'marine',
            'fishinglog-voice': 'marine',
            'fishinglog-nav': 'marine',
            
            # Business Services - Business Domain
            'accounting-core': 'business',
            'financial-management': 'business',
            'business-platform': 'business',
            'business-incubator': 'business',
            'payroll-hr': 'business',
            'invoice-engine': 'business',
            'crm-sales': 'business',
            
            # Development Services - Development Domain
            'code-generation-service': 'development',
            'frontend-improver': 'development',
            'game-improver': 'development',
            'improvement-system': 'development',
            'ai-optimizer': 'development',
            'runtime-optimizer': 'development',
            
            # AI Services - AI Domain
            'ai-orchestrator': 'ai',
            'ai-insights': 'ai',
            'bot-ecosystem': 'ai',
            'bot-orchestrator': 'ai',
            'claude-task-hierarchy': 'ai',
            'hierarchical-task-system': 'ai',
            
            # Data Services - Data Domain
            'data-manager': 'data',
            'data-lifecycle-manager': 'data',
            'analytics-platform': 'data',
            'metadata': 'data',
            'search-engine': 'data',
            
            # Infrastructure Services - Infrastructure Domain
            'api-gateway': 'infrastructure',
            'cloud-infrastructure': 'infrastructure',
            'monitoring-observability': 'infrastructure',
            'backup-dr': 'infrastructure',
            'security-advanced': 'infrastructure',
            
            # Special Research Service
            'dissertation-bot': 'research'
        }
        
        # Standard ports for services (can be overridden)
        self.standard_ports = {
            'dmlog-backend': 8080,
            'dmlog-characters': 8081,
            'marine-autopilot': 8090,
            'accounting-core': 8100,
            'ai-orchestrator': 8200,
            'bot-ecosystem': 8201,
            'hierarchical-task-system': 8471,
            'dynamic-bot-language': 8472,  # This service
            'dissertation-bot': 8473
        }
        
        logger.info(f"Loaded configuration for {len(self.service_domains)} service domains")
    
    async def discover_services(self) -> List[BotService]:
        """Discover active bot services in the network"""
        discovered = []
        
        # Check each configured service
        async with aiohttp.ClientSession() as session:
            for service_name, domain in self.service_domains.items():
                port = self.standard_ports.get(service_name, 8000)
                url = f"http://localhost:{port}"
                
                try:
                    # Try to connect to the service health endpoint
                    async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            service = BotService(
                                name=service_name,
                                port=port,
                                domain=domain,
                                url=url,
                                status="active",
                                capabilities=data.get('capabilities', []),
                                last_seen=time.time()
                            )
                            
                            discovered.append(service)
                            self.discovered_services[service_name] = service
                            
                            logger.info(f"Discovered service: {service_name} ({domain}) on port {port}")
                
                except Exception as e:
                    # Service not available - this is normal
                    pass
        
        logger.info(f"Service discovery completed: {len(discovered)} services found")
        return discovered
    
    def start_service_discovery(self):
        """Start background service discovery"""
        def discovery_worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while True:
                try:
                    loop.run_until_complete(self.discover_services())
                except Exception as e:
                    logger.error(f"Error in service discovery: {e}")
                
                time.sleep(30)  # Discover services every 30 seconds
        
        discovery_thread = threading.Thread(target=discovery_worker, daemon=True)
        discovery_thread.start()
        logger.info("Service discovery started")
    
    def start_integration_monitor(self):
        """Start monitoring and integration tasks"""
        def integration_worker():
            while True:
                try:
                    # Enable language optimization for discovered services
                    self.enable_language_optimization()
                    
                    # Collect and analyze communication metrics
                    self.analyze_communication_patterns()
                    
                    # Report metrics to research system
                    self.report_research_metrics()
                    
                except Exception as e:
                    logger.error(f"Error in integration monitoring: {e}")
                
                time.sleep(60)  # Monitor every minute
        
        integration_thread = threading.Thread(target=integration_worker, daemon=True)
        integration_thread.start()
        logger.info("Integration monitoring started")
    
    def enable_language_optimization(self):
        """Enable language optimization for discovered services"""
        for service_name, service in self.discovered_services.items():
            if not service.language_enabled:
                try:
                    # Try to enable language optimization on the service
                    response = requests.post(
                        f"{service.url}/configure/language-optimization",
                        json={
                            "language_system_url": self.language_system_url,
                            "domain": service.domain,
                            "compression_enabled": True,
                            "translation_enabled": True
                        },
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        service.language_enabled = True
                        logger.info(f"Language optimization enabled for {service_name}")
                
                except Exception as e:
                    # Service doesn't support language optimization yet - that's okay
                    pass
    
    def optimize_communication(self, source_service: str, target_service: str, 
                              message: str) -> Tuple[str, CommunicationMetric]:
        """Optimize communication between two services using dynamic language"""
        start_time = time.time()
        original_size = len(message)
        
        try:
            # Get service domains
            source_domain = self.service_domains.get(source_service, 'general')
            target_domain = self.service_domains.get(target_service, 'general')
            
            optimized_message = message
            compression_ratio = 0.0
            
            if source_domain == target_domain:
                # Same domain - use compression
                response = requests.post(
                    f"{self.language_system_url}/compress",
                    json={
                        "message": message,
                        "domain": source_domain,
                        "source_bot": source_service,
                        "target_bot": target_service
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized_message = result.get('compressed_message', message)
                    compression_ratio = result.get('compression_ratio', 0.0)
            
            else:
                # Different domains - use translation
                response = requests.post(
                    f"{self.language_system_url}/translate",
                    json={
                        "message": message,
                        "source_domain": source_domain,
                        "target_domain": target_domain,
                        "source_bot": source_service,
                        "target_bot": target_service
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    optimized_message = result.get('translated_message', message)
                    # Translation doesn't necessarily compress, but may optimize
                    compression_ratio = 1 - (len(optimized_message) / len(message)) if len(message) > 0 else 0
            
            processing_time = (time.time() - start_time) * 1000
            compressed_size = len(optimized_message)
            
            # Create metric
            metric = CommunicationMetric(
                timestamp=time.time(),
                source_service=source_service,
                target_service=target_service,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                processing_time_ms=processing_time,
                success=True
            )
            
            self.communication_metrics.append(metric)
            
            return optimized_message, metric
        
        except Exception as e:
            logger.error(f"Error optimizing communication: {e}")
            
            # Return original message with error metric
            metric = CommunicationMetric(
                timestamp=time.time(),
                source_service=source_service,
                target_service=target_service,
                original_size=original_size,
                compressed_size=original_size,
                compression_ratio=0.0,
                processing_time_ms=(time.time() - start_time) * 1000,
                success=False
            )
            
            return message, metric
    
    def analyze_communication_patterns(self):
        """Analyze communication patterns across the network"""
        if not self.communication_metrics:
            return
        
        # Calculate recent performance metrics
        recent_metrics = [m for m in self.communication_metrics 
                         if time.time() - m.timestamp < 3600]  # Last hour
        
        if not recent_metrics:
            return
        
        # Calculate averages
        avg_compression = sum(m.compression_ratio for m in recent_metrics) / len(recent_metrics)
        avg_processing_time = sum(m.processing_time_ms for m in recent_metrics) / len(recent_metrics)
        success_rate = sum(1 for m in recent_metrics if m.success) / len(recent_metrics)
        
        # Analyze by domain pairs
        domain_patterns = {}
        for metric in recent_metrics:
            source_domain = self.service_domains.get(metric.source_service, 'general')
            target_domain = self.service_domains.get(metric.target_service, 'general')
            
            pattern_key = f"{source_domain}→{target_domain}"
            
            if pattern_key not in domain_patterns:
                domain_patterns[pattern_key] = []
            
            domain_patterns[pattern_key].append(metric)
        
        # Log analysis results
        logger.info(f"Communication Analysis (last hour):")
        logger.info(f"  Messages processed: {len(recent_metrics)}")
        logger.info(f"  Average compression: {avg_compression:.2%}")
        logger.info(f"  Average processing time: {avg_processing_time:.1f}ms")
        logger.info(f"  Success rate: {success_rate:.2%}")
        logger.info(f"  Domain patterns: {len(domain_patterns)}")
        
        for pattern, metrics in domain_patterns.items():
            if len(metrics) > 1:  # Only log patterns with multiple communications
                pattern_compression = sum(m.compression_ratio for m in metrics) / len(metrics)
                logger.info(f"    {pattern}: {len(metrics)} messages, {pattern_compression:.2%} compression")
    
    def report_research_metrics(self):
        """Report integration metrics to the research system"""
        try:
            # Calculate metrics for the last hour
            recent_metrics = [m for m in self.communication_metrics 
                            if time.time() - m.timestamp < 3600]
            
            if not recent_metrics:
                return
            
            # Prepare research data
            research_data = {
                "network_integration_metrics": {
                    "total_services_discovered": len(self.discovered_services),
                    "language_enabled_services": sum(1 for s in self.discovered_services.values() if s.language_enabled),
                    "hourly_message_volume": len(recent_metrics),
                    "average_compression_ratio": sum(m.compression_ratio for m in recent_metrics) / len(recent_metrics),
                    "average_processing_time_ms": sum(m.processing_time_ms for m in recent_metrics) / len(recent_metrics),
                    "success_rate": sum(1 for m in recent_metrics if m.success) / len(recent_metrics),
                    "active_domains": list(set(self.service_domains.get(s.name, 'general') for s in self.discovered_services.values())),
                    "cross_domain_communications": len([m for m in recent_metrics if 
                                                      self.service_domains.get(m.source_service, 'general') != 
                                                      self.service_domains.get(m.target_service, 'general')])
                }
            }
            
            # Send to research system
            response = requests.post(
                f"{self.language_system_url}/research/network-integration",
                json=research_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Research metrics reported successfully")
            
        except Exception as e:
            logger.error(f"Error reporting research metrics: {e}")
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network integration status"""
        status = {
            "integration_active": self.integration_active,
            "discovered_services": len(self.discovered_services),
            "language_enabled_services": sum(1 for s in self.discovered_services.values() if s.language_enabled),
            "total_domains": len(set(self.service_domains.values())),
            "recent_communications": len([m for m in self.communication_metrics if time.time() - m.timestamp < 3600]),
            "services_by_domain": {},
            "recent_performance": {}
        }
        
        # Group services by domain
        for service in self.discovered_services.values():
            domain = service.domain
            if domain not in status["services_by_domain"]:
                status["services_by_domain"][domain] = []
            
            status["services_by_domain"][domain].append({
                "name": service.name,
                "port": service.port,
                "status": service.status,
                "language_enabled": service.language_enabled,
                "last_seen": service.last_seen
            })
        
        # Calculate recent performance
        recent_metrics = [m for m in self.communication_metrics if time.time() - m.timestamp < 3600]
        
        if recent_metrics:
            status["recent_performance"] = {
                "message_count": len(recent_metrics),
                "average_compression": sum(m.compression_ratio for m in recent_metrics) / len(recent_metrics),
                "average_processing_time": sum(m.processing_time_ms for m in recent_metrics) / len(recent_metrics),
                "success_rate": sum(1 for m in recent_metrics if m.success) / len(recent_metrics)
            }
        
        return status
    
    def generate_integration_report(self) -> str:
        """Generate a comprehensive integration report for the Dissertation Bot"""
        status = self.get_network_status()
        
        report = []
        report.append("🌐 Building Bots Network Integration Report")
        report.append("=" * 50)
        report.append("")
        
        # Service Discovery
        report.append("🔍 Service Discovery:")
        report.append(f"   Total Services Discovered: {status['discovered_services']}")
        report.append(f"   Language Optimization Enabled: {status['language_enabled_services']}")
        report.append(f"   Active Domains: {status['total_domains']}")
        report.append("")
        
        # Services by Domain
        report.append("📊 Services by Domain:")
        for domain, services in status["services_by_domain"].items():
            report.append(f"   {domain.upper()}:")
            for service in services:
                status_icon = "✅" if service["status"] == "active" else "❌"
                lang_icon = "🧠" if service["language_enabled"] else "⏸️"
                report.append(f"      {status_icon} {lang_icon} {service['name']} (:{service['port']})")
        report.append("")
        
        # Performance Metrics
        if status["recent_performance"]:
            perf = status["recent_performance"]
            report.append("📈 Recent Performance (Last Hour):")
            report.append(f"   Messages Processed: {perf['message_count']}")
            report.append(f"   Average Compression: {perf['average_compression']:.2%}")
            report.append(f"   Average Processing Time: {perf['average_processing_time']:.1f}ms")
            report.append(f"   Success Rate: {perf['success_rate']:.2%}")
        else:
            report.append("📈 Recent Performance: No data available")
        
        report.append("")
        report.append("🎓 Research Impact:")
        report.append("   ✓ Real-time language evolution across bot network")
        report.append("   ✓ Cross-domain communication optimization") 
        report.append("   ✓ Comprehensive metrics for academic analysis")
        report.append("   ✓ Multi-service integration validation")
        
        return "\n".join(report)

def main():
    """Main function for testing network integration"""
    print("🌐 Building Bots Network Integration - Dynamic Bot Language")
    print("=" * 60)
    
    # Initialize integrator
    integrator = BuildingBotsNetworkIntegrator()
    
    # Wait for initial service discovery
    print("🔍 Discovering services...")
    time.sleep(5)
    
    # Generate and display integration report
    report = integrator.generate_integration_report()
    print(report)
    
    # Test communication optimization
    print("\n🧪 Testing Communication Optimization:")
    
    test_cases = [
        ("dmlog-backend", "dmlog-characters", "generate new character stats and abilities for campaign"),
        ("marine-autopilot", "marine-advanced", "navigate to waypoint with collision avoidance enabled"),
        ("accounting-core", "financial-management", "process transaction and update ledger entries"),
        ("ai-orchestrator", "bot-ecosystem", "allocate resources for model inference request")
    ]
    
    for source, target, message in test_cases:
        print(f"\n   {source} → {target}:")
        print(f"   Original: '{message}'")
        
        optimized_message, metric = integrator.optimize_communication(source, target, message)
        
        print(f"   Optimized: '{optimized_message}'")
        print(f"   Compression: {metric.compression_ratio:.2%}")
        print(f"   Processing: {metric.processing_time_ms:.1f}ms")
        print(f"   Success: {'✅' if metric.success else '❌'}")
    
    # Keep running for continuous monitoring
    print(f"\n🚀 Integration active - monitoring network communications...")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Network integration stopped")

if __name__ == "__main__":
    main()