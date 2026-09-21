#!/usr/bin/env python3
"""
Product Marketplace Demo Server - Comprehensive hardware marketplace demonstration
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from main import app, marketplace_service
from hardware.design_system import HardwareDesignSystem
from devices.activelog_catalog import ActivelogCatalog
from solar.camera_systems import SolarCameraMarketplace

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketplaceDemoServer:
    """Demo server for the product marketplace"""
    
    def __init__(self):
        self.design_system = HardwareDesignSystem()
        self.device_catalog = ActivelogCatalog()
        self.solar_cameras = SolarCameraMarketplace()
        
    async def populate_demo_data(self):
        """Populate the marketplace with comprehensive demo data"""
        logger.info("🚀 Populating marketplace with demo data...")
        
        # Create sample products from design templates
        await self._create_sample_products()
        
        # Create sample designers
        await self._create_sample_designers()
        
        # Create sample orders
        await self._create_sample_orders()
        
        # Create sample reviews
        await self._create_sample_reviews()
        
        # Create sample patents
        await self._create_sample_patents()
        
        logger.info("✅ Demo data population completed!")
    
    async def _create_sample_products(self):
        """Create sample products from design templates"""
        
        # Solar Camera System
        solar_camera_product = {
            "name": "WildTracker Pro 4K Solar Camera",
            "category": "solar_cameras",
            "description": "Professional-grade solar wildlife camera with 4K video, advanced AI species detection, and 6-month battery autonomy. Perfect for remote wildlife monitoring and research applications.",
            "price": 899.00,
            "creator_name": "NatureTech Systems",
            "technical_specs": {
                "camera_resolution": "20MP",
                "video_resolution": "4K@30fps",
                "night_vision_range": "25 meters",
                "battery_life": "6 months",
                "solar_panel": "12W monocrystalline",
                "connectivity": ["LoRaWAN", "WiFi", "Cellular"],
                "ai_features": ["Species detection", "Behavior analysis", "Object counting"],
                "environmental_rating": "IP67",
                "operating_temperature": "-30°C to +60°C"
            },
            "tags": ["wildlife", "4k", "ai", "professional", "long_range", "weatherproof"],
            "patent_protected": False,
            "license_type": "Creative Commons BY-SA",
            "revenue_sharing_enabled": True,
            "revenue_sharing_percent": 15.0,
            "difficulty_level": "intermediate",
            "assembly_time_hours": 4.0,
            "tools_required": ["Screwdriver", "Drill", "Level", "Multimeter"],
            "materials_included": [
                "Camera housing",
                "Solar panel",
                "Battery pack",
                "Mounting hardware",
                "Cables",
                "SD card (32GB)",
                "User manual"
            ],
            "images": [
                "/api/images/wildtracker-pro-main.jpg",
                "/api/images/wildtracker-pro-setup.jpg",
                "/api/images/wildtracker-pro-night.jpg"
            ],
            "design_files": [
                "/api/files/wildtracker-pro-manual.pdf",
                "/api/files/wildtracker-pro-setup-guide.pdf"
            ]
        }
        
        # Fish Counter System
        fish_counter_product = {
            "name": "AquaCount Pro Fish Counter",
            "category": "fish_counters",
            "description": "Automated fish counting system using computer vision and AI for accurate aquaculture and fisheries management. Provides real-time fish counting, size estimation, and species classification.",
            "price": 2499.00,
            "creator_name": "Marine Tech Solutions",
            "technical_specs": {
                "detection_method": "Stereo vision + AI",
                "accuracy": "95%+",
                "counting_rate": "Up to 10 fish/second",
                "species_classification": "15+ species",
                "size_estimation": "±5mm accuracy",
                "connectivity": ["LoRaWAN", "Ethernet", "4G"],
                "power_consumption": "8W average",
                "environmental_rating": "IP68",
                "depth_rating": "5 meters"
            },
            "tags": ["fish", "counting", "aquaculture", "computer_vision", "underwater", "research"],
            "patent_protected": True,
            "patent_number": "US10,123,456",
            "license_type": "GPL v3",
            "revenue_sharing_enabled": True,
            "revenue_sharing_percent": 20.0,
            "difficulty_level": "advanced",
            "assembly_time_hours": 8.0,
            "tools_required": ["Waterproofing tools", "Precision screwdrivers", "Calibration equipment"],
            "materials_included": [
                "Waterproof housing",
                "Stereo camera system",
                "Processing unit",
                "Mounting brackets",
                "Cables",
                "Calibration targets",
                "Software license"
            ]
        }
        
        # Environmental Sensor Package
        sensor_package_product = {
            "name": "EcoSense Multi-Parameter Sensor",
            "category": "sensor_packages",
            "description": "Comprehensive environmental monitoring sensor package with solar power, wireless connectivity, and real-time data streaming. Measures temperature, humidity, pressure, air quality, and more.",
            "price": 349.00,
            "creator_name": "Environmental Sensors Inc",
            "technical_specs": {
                "parameters": ["Temperature", "Humidity", "Pressure", "Light", "UV", "Air Quality", "Soil Moisture"],
                "accuracy": "Research grade",
                "data_rate": "1 minute to 24 hours",
                "connectivity": ["LoRaWAN", "WiFi"],
                "power": "Solar + battery",
                "battery_life": "2+ years",
                "range": "10km line-of-sight",
                "environmental_rating": "IP65"
            },
            "tags": ["sensors", "environmental", "wireless", "solar", "research", "monitoring"],
            "patent_protected": False,
            "license_type": "MIT",
            "revenue_sharing_enabled": False,
            "difficulty_level": "beginner",
            "assembly_time_hours": 2.0,
            "tools_required": ["Screwdriver", "Wire strippers"],
            "materials_included": [
                "Sensor housing",
                "Solar panel",
                "Battery",
                "Sensors (7x)",
                "Antenna",
                "Mounting kit"
            ]
        }
        
        # DIY Security Camera Kit
        diy_security_kit = {
            "name": "DIY Solar Security Camera Kit",
            "category": "activelog_devices",
            "description": "Complete DIY kit for building your own solar-powered security camera with Activelog integration. Perfect for learning and customization.",
            "price": 199.00,
            "creator_name": "Maker Security Co",
            "technical_specs": {
                "camera": "1080p HD",
                "night_vision": "Up to 10 meters",
                "storage": "Local SD + cloud",
                "power": "6W solar panel",
                "battery": "Li-ion 18650",
                "connectivity": ["WiFi", "LoRa"],
                "features": ["Motion detection", "Mobile alerts", "Two-way audio"]
            },
            "tags": ["diy", "security", "solar", "kit", "learning", "customizable"],
            "patent_protected": False,
            "license_type": "Open Hardware",
            "revenue_sharing_enabled": True,
            "revenue_sharing_percent": 10.0,
            "difficulty_level": "beginner",
            "assembly_time_hours": 3.0,
            "tools_required": ["Soldering iron", "Screwdriver set", "Wire strippers", "Multimeter"],
            "materials_included": [
                "PCB (assembled)",
                "Camera module",
                "Solar panel (6W)",
                "Battery holder",
                "Enclosure parts",
                "Hardware kit",
                "Detailed assembly guide"
            ]
        }
        
        # Gateway Device
        gateway_product = {
            "name": "Activelog Gateway Pro",
            "category": "activelog_devices",
            "description": "Professional-grade central gateway for large Activelog deployments with advanced networking, edge computing, and device management capabilities.",
            "price": 899.00,
            "creator_name": "Activelog Systems",
            "technical_specs": {
                "processor": "ARM Cortex-A78 Quad-core",
                "memory": "8GB DDR4",
                "storage": "1TB NVMe SSD",
                "connectivity": ["Ethernet", "WiFi 6", "4G/5G", "LoRaWAN"],
                "device_capacity": "1000+ devices",
                "power": "PoE+ or 12-24V DC",
                "environmental_rating": "IP40",
                "form_factor": "19\" rack mount"
            },
            "tags": ["gateway", "professional", "enterprise", "networking", "edge_computing"],
            "patent_protected": True,
            "patent_number": "US10,987,654",
            "license_type": "Commercial",
            "revenue_sharing_enabled": False,
            "difficulty_level": "advanced",
            "assembly_time_hours": 1.0,  # Pre-assembled
            "tools_required": ["None - pre-assembled"],
            "materials_included": [
                "Gateway unit",
                "Power adapter",
                "Ethernet cable",
                "Antennas (4x)",
                "Rack mount kit",
                "User manual",
                "Software license"
            ]
        }
        
        products = [
            solar_camera_product,
            fish_counter_product,
            sensor_package_product,
            diy_security_kit,
            gateway_product
        ]
        
        for product_data in products:
            try:
                # This would normally use the database, but for demo we'll simulate
                print(f"Created product: {product_data['name']} - ${product_data['price']}")
            except Exception as e:
                logger.error(f"Error creating product {product_data['name']}: {e}")
    
    async def _create_sample_designers(self):
        """Create sample designer profiles"""
        designers = [
            {
                "id": "naturetech_systems",
                "name": "NatureTech Systems",
                "email": "contact@naturetech.com",
                "bio": "Leading manufacturer of solar-powered wildlife monitoring equipment with over 15 years of experience in environmental technology.",
                "location": "Portland, Oregon, USA",
                "specialties": ["wildlife_cameras", "solar_power", "ai_detection"],
                "verified": True,
                "reputation_score": 4.8,
                "patent_holder": False
            },
            {
                "id": "marine_tech_solutions",
                "name": "Marine Tech Solutions",
                "email": "info@marinetech.com",
                "bio": "Specialists in underwater technology and automated fish counting systems for aquaculture and fisheries research.",
                "location": "Vancouver, BC, Canada",
                "specialties": ["fish_counting", "underwater_tech", "computer_vision"],
                "verified": True,
                "reputation_score": 4.9,
                "patent_holder": True
            },
            {
                "id": "environmental_sensors",
                "name": "Environmental Sensors Inc",
                "email": "sales@envsensors.com",
                "bio": "Manufacturer of precision environmental monitoring equipment for research and commercial applications.",
                "location": "Boulder, Colorado, USA",
                "specialties": ["environmental_sensors", "research_equipment", "data_logging"],
                "verified": True,
                "reputation_score": 4.7,
                "patent_holder": False
            },
            {
                "id": "maker_security",
                "name": "Maker Security Co",
                "email": "hello@makersecurity.io",
                "bio": "Open-source security solutions and DIY kits for makers and hobbyists. Promoting accessible security technology.",
                "location": "Austin, Texas, USA",
                "specialties": ["diy_kits", "security", "open_source"],
                "verified": True,
                "reputation_score": 4.6,
                "patent_holder": False
            },
            {
                "id": "activelog_systems",
                "name": "Activelog Systems",
                "email": "enterprise@activelog.com",
                "bio": "Creator of the Activelog platform and professional-grade IoT infrastructure solutions.",
                "location": "San Francisco, California, USA",
                "specialties": ["iot_platforms", "gateways", "enterprise_solutions"],
                "verified": True,
                "reputation_score": 4.9,
                "patent_holder": True
            }
        ]
        
        for designer in designers:
            print(f"Created designer: {designer['name']} - {designer['reputation_score']} stars")
    
    async def _create_sample_orders(self):
        """Create sample orders"""
        orders = [
            {
                "customer_id": "user_001",
                "customer_email": "researcher@university.edu",
                "product_id": "wildtracker_pro",
                "product_name": "WildTracker Pro 4K Solar Camera",
                "quantity": 3,
                "unit_price": 899.00,
                "total_amount": 2697.00,
                "order_type": "physical",
                "assembly_service": True,
                "installation_service": False
            },
            {
                "customer_id": "user_002", 
                "customer_email": "farm@aquaculture.com",
                "product_id": "aquacount_pro",
                "product_name": "AquaCount Pro Fish Counter",
                "quantity": 1,
                "unit_price": 2499.00,
                "total_amount": 2499.00,
                "order_type": "physical",
                "assembly_service": False,
                "installation_service": True
            }
        ]
        
        for order_data in orders:
            print(f"Created order: {order_data['product_name']} x{order_data['quantity']} - ${order_data['total_amount']}")
    
    async def _create_sample_reviews(self):
        """Create sample product reviews"""
        reviews = [
            {
                "product_id": "wildtracker_pro",
                "customer_name": "Dr. Sarah Johnson",
                "rating": 5,
                "title": "Excellent for Long-term Wildlife Studies",
                "review_text": "We've been using these cameras for 8 months in our bear study. The AI species detection is remarkably accurate, and the solar charging has kept them running through winter. Highly recommended for research applications.",
                "verified_purchase": True
            },
            {
                "product_id": "wildtracker_pro",
                "customer_name": "Mike Hunter",
                "rating": 4,
                "title": "Great Camera, Setup Could Be Easier",
                "review_text": "Image quality is outstanding, especially the night vision. Setup took longer than expected, but customer support was very helpful. Battery life is as advertised - 6 months and counting.",
                "verified_purchase": True
            },
            {
                "product_id": "aquacount_pro",
                "customer_name": "AquaTech Farms",
                "rating": 5,
                "title": "Game Changer for Aquaculture",
                "review_text": "This system has revolutionized our fish counting process. 95%+ accuracy as claimed, and the species classification helps us track our stock composition. ROI achieved in 6 months.",
                "verified_purchase": True
            }
        ]
        
        for review in reviews:
            print(f"Created review: {review['title']} - {review['rating']} stars")
    
    async def _create_sample_patents(self):
        """Create sample patent records"""
        patents = [
            {
                "patent_number": "US10,123,456",
                "title": "Automated Fish Counting System Using Stereo Vision",
                "description": "A system and method for automatically counting fish using stereo vision cameras and machine learning algorithms for species classification and size estimation.",
                "inventor_name": "Dr. Alex Chen",
                "inventor_id": "marine_tech_solutions",
                "filing_date": "2020-03-15",
                "grant_date": "2022-08-20",
                "status": "granted",
                "licensing_available": True,
                "license_fee_percent": 5.0
            },
            {
                "patent_number": "US10,987,654",
                "title": "IoT Gateway with Edge Computing Capabilities",
                "description": "An Internet of Things gateway device with integrated edge computing, device management, and secure data processing capabilities for large-scale deployments.",
                "inventor_name": "Activelog Engineering Team",
                "inventor_id": "activelog_systems", 
                "filing_date": "2019-11-08",
                "grant_date": "2021-06-12",
                "status": "granted",
                "licensing_available": False,
                "license_fee_percent": 0.0
            }
        ]
        
        for patent in patents:
            print(f"Created patent: {patent['patent_number']} - {patent['title']}")
    
    def print_demo_summary(self):
        """Print comprehensive demo summary"""
        print("\n" + "="*80)
        print("🏪 ACTIVELOG PRODUCT MARKETPLACE - DEMO OVERVIEW")
        print("="*80)
        
        print("\n📦 PRODUCT CATEGORIES:")
        print("• Custom Hardware Designs - Complete PCB and schematic designs")
        print("• Activelog-Ready Devices - Certified compatible devices")
        print("• Solar Camera Systems - Wildlife, security, and research cameras")
        print("• Fish Counter Solutions - Automated aquaculture monitoring")
        print("• Sensor Packages - Environmental and scientific sensors")
        print("• DIY Kits - Build-your-own hardware projects")
        print("• Assembly Services - Professional assembly and installation")
        
        print("\n🔧 KEY FEATURES:")
        print("• Hardware design system with CAD integration")
        print("• Component libraries and BOM generation")
        print("• Patent protection and revenue sharing")
        print("• Viral product tracking and analytics")
        print("• AI-powered product recommendations")
        print("• Integration with manufacturing partners")
        print("• Community design collaboration")
        
        print("\n🌟 SAMPLE PRODUCTS:")
        print("• WildTracker Pro 4K Solar Camera - $899 (Wildlife monitoring)")
        print("• AquaCount Pro Fish Counter - $2,499 (Aquaculture)")
        print("• EcoSense Multi-Parameter Sensor - $349 (Environmental)")
        print("• DIY Solar Security Camera Kit - $199 (Education)")
        print("• Activelog Gateway Pro - $899 (Enterprise)")
        
        print("\n🔬 TECHNICAL CAPABILITIES:")
        print("• CAD file management and version control")
        print("• Component search and compatibility checking")
        print("• Automated BOM generation and cost estimation")
        print("• 3D rendering and visualization")
        print("• Design validation and rule checking")
        print("• Manufacturing partner integration")
        
        print("\n💰 BUSINESS FEATURES:")
        print("• Revenue sharing with creators")
        print("• Patent protection services")
        print("• Viral marketing and product tracking")
        print("• ROI calculators and cost analysis")
        print("• Market trends and analytics")
        print("• Customer reviews and ratings")
        
        print("\n🌐 API ENDPOINTS:")
        print("GET  /products - List all products with filtering")
        print("POST /products - Create new product listing")
        print("GET  /products/{id} - Get detailed product information")
        print("GET  /featured-products - Get featured products")
        print("GET  /viral-products - Get trending/viral products")
        print("POST /orders - Create new order")
        print("GET  /designers/{id} - Get designer profile and products")
        print("GET  /analytics/viral-trends - Get viral trends analytics")
        print("POST /products/{id}/viral-action - Track viral actions")
        
        print("\n🎯 TARGET MARKETS:")
        print("• Wildlife researchers and conservationists")
        print("• Aquaculture and fisheries operators")
        print("• Environmental monitoring agencies")
        print("• Security system integrators")
        print("• Educational institutions and makers")
        print("• IoT system developers")
        
        print("\n" + "="*80)

async def main():
    """Main demo server function"""
    print("🚀 Starting Activelog Product Marketplace Demo Server...")
    
    # Initialize demo server
    demo_server = MarketplaceDemoServer()
    
    # Populate with demo data
    await demo_server.populate_demo_data()
    
    # Print demo summary
    demo_server.print_demo_summary()
    
    print(f"\n🌐 Server starting on port 8380...")
    print(f"📖 API Documentation: http://localhost:8380/docs")
    print(f"🔍 Interactive API: http://localhost:8380/redoc")
    print(f"📊 Health Check: http://localhost:8380/")
    
    # Start the FastAPI server
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8380, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())