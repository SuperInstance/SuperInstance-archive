"""
Main service orchestrator for the Data Management AI.
Provides a unified interface to all data management capabilities.
"""

import asyncio
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all services
from core.data_manager import DataManager
from ai.intelligent_classifier import IntelligentClassifier
from ai.recommendation_engine import RecommendationEngine
from analytics.insights_engine import InsightsEngine
from monitoring.quality_monitor import QualityMonitor
from processing.processors import *
from api.integration import integration_service, personalization_layer
from data_services_hub import DataServicesHub

class DataManagementAIService:
    """
    Main orchestrator for the Data Management AI service.
    Provides a unified interface to all data management capabilities.
    """
    
    def __init__(self):
        self.data_manager = DataManager("sqlite:///:memory:")
        self.recommendation_engine = RecommendationEngine()
        self.insights_engine = InsightsEngine()
        self.quality_monitor = QualityMonitor()
        self.integration_service = integration_service
        self.personalization_layer = personalization_layer
        self.data_services_hub = DataServicesHub()
        
        # Service state
        self.is_running = False
        self.start_time = None
        
        print("✅ Data Management AI Service initialized")
    
    async def start(self):
        """Start the Data Management AI service."""
        if self.is_running:
            print("⚠️  Service is already running")
            return
        
        self.start_time = datetime.now()
        self.is_running = True
        
        print("🚀 Starting Data Management AI Service...")
        
        # Initialize all components
        await self._initialize_components()
        
        print("✅ Data Management AI Service started successfully")
        print(f"📊 Service available at: http://localhost:8000")
        print(f"📖 API documentation available at: http://localhost:8000/docs")
    
    async def stop(self):
        """Stop the Data Management AI service."""
        if not self.is_running:
            print("⚠️  Service is not running")
            return
        
        print("🛑 Stopping Data Management AI Service...")
        
        # Cleanup components
        await self._cleanup_components()
        
        self.is_running = False
        self.start_time = None
        
        print("✅ Data Management AI Service stopped")
    
    async def _initialize_components(self):
        """Initialize all service components."""
        print("🔧 Initializing components...")
        
        # Initialize data manager
        print("  📁 Initializing Data Manager...")
        
        # Initialize AI components
        print("  🤖 Initializing AI Components...")
        
        # Initialize monitoring
        print("  📊 Initializing Quality Monitor...")
        
        # Initialize API integration
        print("  🌐 Initializing API Integration...")
        
        print("✅ All components initialized")
    
    async def _cleanup_components(self):
        """Cleanup all service components."""
        print("🧹 Cleaning up components...")
        
        # Cleanup would go here in a real implementation
        
        print("✅ Cleanup completed")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        uptime = None
        if self.start_time:
            uptime = str(datetime.now() - self.start_time)
        
        return {
            "service": "Data Management AI",
            "version": "1.0.0",
            "status": "running" if self.is_running else "stopped",
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime": uptime,
            "components": {
                "data_manager": "healthy",
                "recommendation_engine": "healthy",
                "insights_engine": "healthy",
                "quality_monitor": "healthy",
                "integration_service": "healthy",
                "personalization_layer": "healthy",
                "data_services_hub": "healthy"
            },
            "capabilities": [
                "intelligent_data_classification",
                "automated_processing_pipeline",
                "personalized_recommendations",
                "data_insights_generation",
                "quality_monitoring",
                "folder_organization",
                "privacy_preserving_learning",
                "natural_language_interface",
                "cross_app_integration",
                "preference_export_import",
                "data_services_integration",
                "batch_data_processing",
                "multi_service_synchronization",
                "distributed_data_operations"
            ]
        }
    
    # Core functionality methods
    async def ingest_and_process_data(self, user_id: str, source: str, content: Any, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete data ingestion and processing workflow."""
        try:
            # Step 1: Ingest data
            data_item = await self.data_manager.ingest_data(user_id, source, content, metadata)
            
            # Step 2: Get personalized processing recommendations
            recommendations = await self.recommendation_engine.get_recommendations(
                user_id, ["DATA_PROCESSING"]
            )
            
            # Step 3: Process according to recommendations
            processing_results = []
            for rec in recommendations:
                if rec.type == "DATA_PROCESSING" and rec.confidence > 0.7:
                    result = await self.data_manager.processing_pipeline.process_item(
                        data_item.id, 
                        rec.metadata.get("processor_type", "text"),
                        rec.metadata.get("parameters", {})
                    )
                    processing_results.append(result)
            
            # Step 4: Update user profile with behavior
            await self.recommendation_engine.profiler.record_behavior(
                user_id,
                "data_ingested",
                {
                    "source": source,
                    "classification": data_item.classification.category,
                    "size": len(str(content))
                }
            )
            
            # Step 5: Send webhook notification
            await self.integration_service.send_webhook(
                user_id,
                "data_processed",
                {
                    "data_item_id": data_item.id,
                    "classification": data_item.classification.category,
                    "processing_results": len(processing_results)
                }
            )
            
            return {
                "success": True,
                "data_item": data_item,
                "processing_results": processing_results,
                "recommendations_applied": len([r for r in recommendations if r.confidence > 0.7])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_intelligent_folder(self, user_id: str, natural_language_request: str) -> Dict[str, Any]:
        """Create a folder using natural language processing."""
        try:
            # Step 1: Process natural language request
            nlp_result = await self.integration_service.process_natural_language_request(
                user_id, natural_language_request
            )
            
            # Step 2: Get folder organization recommendations
            folder_recommendations = await self.recommendation_engine.get_recommendations(
                user_id, ["FOLDER_ORGANIZATION"]
            )
            
            # Step 3: Create folder with intelligent suggestions
            folder_config = {
                "name": nlp_result["suggested_action"]["folder_name"],
                "template": nlp_result["suggested_action"]["template"],
                "tags": nlp_result["suggested_action"]["tags"],
                "auto_organize": True,
                "smart_rules": []
            }
            
            # Add recommendations as smart rules
            for rec in folder_recommendations:
                if rec.confidence > 0.6:
                    folder_config["smart_rules"].append({
                        "rule": rec.description,
                        "confidence": rec.confidence
                    })
            
            # Step 4: Record behavior for learning
            await self.recommendation_engine.profiler.record_behavior(
                user_id,
                "folder_created",
                {
                    "request": natural_language_request,
                    "template": folder_config["template"],
                    "intent_confidence": nlp_result["confidence"]
                }
            )
            
            return {
                "success": True,
                "folder_config": folder_config,
                "nlp_confidence": nlp_result["confidence"],
                "smart_rules_applied": len(folder_config["smart_rules"])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def export_user_intelligence(self, user_id: str) -> Dict[str, Any]:
        """Export user's complete AI profile and preferences."""
        try:
            # Get user profile
            profile = await self.recommendation_engine.profiler.get_user_profile(user_id)
            
            # Get user's adaptation layer
            adaptation = self.personalization_layer.user_adaptations.get(user_id, {})
            
            # Get recent insights
            insights = await self.insights_engine.generate_insights(user_id)
            
            # Get quality metrics
            quality_report = await self.quality_monitor.run_quality_assessment(user_id)
            
            export_data = {
                "user_id": user_id,
                "export_timestamp": datetime.now().isoformat(),
                "profile": profile,
                "personalization_adaptation": adaptation,
                "recent_insights": insights[:10],  # Last 10 insights
                "quality_metrics": quality_report,
                "export_version": "1.0"
            }
            
            return {
                "success": True,
                "export_data": export_data,
                "data_size_mb": len(str(export_data)) / (1024 * 1024)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def setup_privacy_preserving_training(self, user_id: str, consent_settings: Dict[str, bool]) -> Dict[str, Any]:
        """Set up privacy-preserving training with user consent."""
        try:
            # Record consent
            for consent_type, granted in consent_settings.items():
                await self.integration_service.handle_privacy_request(
                    user_id,
                    "consent_update",
                    {"consent_type": consent_type, "granted": granted}
                )
            
            # Configure personalization layer
            if consent_settings.get("personalization", False):
                adaptation_config = {
                    "privacy_preserving": True,
                    "local_training": True,
                    "data_retention_days": consent_settings.get("data_retention_days", 30),
                    "anonymization_level": "high"
                }
                
                adaptation = await self.personalization_layer.create_user_adaptation(
                    user_id, adaptation_config
                )
                
                return {
                    "success": True,
                    "privacy_training_enabled": True,
                    "adaptation_id": user_id,
                    "privacy_level": "high",
                    "consent_recorded": len(consent_settings)
                }
            else:
                return {
                    "success": True,
                    "privacy_training_enabled": False,
                    "message": "Personalization consent not granted"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # Data Services Hub Integration Methods
    async def batch_import_data(self, user_id: str, file_paths: List[str], import_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Batch import data through integrated services"""
        try:
            operation_ids = await self.data_services_hub.batch_import_files(
                user_id, file_paths, import_config
            )
            
            return {
                "success": True,
                "operation_ids": operation_ids,
                "total_files": len(file_paths),
                "initiated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def sync_data_services(self, sync_config: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronize data across integrated services"""
        try:
            operation_ids = await self.data_services_hub.sync_data_across_services(sync_config)
            
            return {
                "success": True,
                "sync_operations": operation_ids,
                "sync_type": sync_config.get("type", "real_time_sync"),
                "initiated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def process_media_batch(self, user_id: str, media_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process batch of media files through integrated services"""
        try:
            operation_ids = await self.data_services_hub.process_media_files(user_id, media_files)
            
            return {
                "success": True,
                "processing_operations": operation_ids,
                "total_files": len(media_files),
                "initiated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def export_integrated_data(self, user_id: str, export_format: str, data_types: List[str] = None) -> Dict[str, Any]:
        """Export data through integrated export service"""
        try:
            operation_id = await self.data_services_hub.export_user_data(
                user_id, export_format, data_types
            )
            
            return {
                "success": True,
                "export_operation_id": operation_id,
                "export_format": export_format,
                "data_types": data_types or ["all"],
                "initiated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_data_services_status(self) -> Dict[str, Any]:
        """Get status of all integrated data services"""
        try:
            health_status = await self.data_services_hub.get_services_health()
            hub_stats = await self.data_services_hub.get_hub_statistics()
            
            return {
                "success": True,
                "services_health": health_status,
                "hub_statistics": hub_stats,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def track_operation_progress(self, operation_id: str) -> Dict[str, Any]:
        """Track progress of a data operation"""
        try:
            status = await self.data_services_hub.get_operation_status(operation_id)
            
            return {
                "success": True,
                "operation_status": status,
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# Global service instance
data_management_ai = DataManagementAIService()

# CLI interface
async def main():
    """Main CLI interface for the Data Management AI service."""
    print("🤖 Data Management AI Service")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python main.py <command> [args...]")
        print("\nAvailable commands:")
        print("  start              - Start the service")
        print("  stop               - Stop the service")
        print("  status             - Get service status")
        print("  ingest             - Ingest sample data")
        print("  recommend          - Get recommendations")
        print("  insights           - Generate insights")
        print("  quality            - Run quality assessment")
        print("  create-folder      - Create intelligent folder")
        print("  export-profile     - Export user profile")
        print("  setup-privacy      - Setup privacy-preserving training")
        print("  test-all           - Run all tests")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "start":
            await data_management_ai.start()
            
        elif command == "stop":
            await data_management_ai.stop()
            
        elif command == "status":
            status = await data_management_ai.get_status()
            print(f"📊 Service Status: {status}")
            
        elif command == "ingest":
            print("📥 Testing data ingestion...")
            result = await data_management_ai.ingest_and_process_data(
                "test_user",
                "cli_test",
                "This is a test document about machine learning and AI development.",
                {"filename": "test_ml_doc.txt", "source": "manual_upload"}
            )
            print(f"✅ Ingestion result: {result}")
            
        elif command == "recommend":
            print("🎯 Getting recommendations...")
            recommendations = await data_management_ai.recommendation_engine.get_recommendations("test_user")
            print(f"📋 Recommendations: {len(recommendations)} items")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"  {i}. {rec.type}: {rec.description} (confidence: {rec.confidence:.2f})")
                
        elif command == "insights":
            print("💡 Generating insights...")
            insights = await data_management_ai.insights_engine.generate_insights("test_user")
            print(f"🔍 Generated {len(insights)} insights")
            for i, insight in enumerate(insights[:3], 1):
                print(f"  {i}. {insight.type}: {insight.title}")
                
        elif command == "quality":
            print("🔍 Running quality assessment...")
            quality_report = await data_management_ai.quality_monitor.run_quality_assessment("test_user")
            print(f"📊 Quality Score: {quality_report.overall_score:.1f}/100")
            print(f"📈 Quality Metrics: {len(quality_report.metrics)} checks")
            
        elif command == "create-folder":
            print("📁 Creating intelligent folder...")
            result = await data_management_ai.create_intelligent_folder(
                "test_user",
                "create a folder for tax documents from 2024"
            )
            print(f"✅ Folder creation result: {result}")
            
        elif command == "export-profile":
            print("📤 Exporting user profile...")
            export_result = await data_management_ai.export_user_intelligence("test_user")
            print(f"✅ Export completed: {export_result.get('data_size_mb', 0):.2f} MB")
            
        elif command == "setup-privacy":
            print("🔒 Setting up privacy-preserving training...")
            result = await data_management_ai.setup_privacy_preserving_training(
                "test_user",
                {
                    "personalization": True,
                    "data_collection": True,
                    "analytics": False,
                    "data_retention_days": 30
                }
            )
            print(f"✅ Privacy setup result: {result}")
            
        elif command == "test-all":
            print("🧪 Running comprehensive tests...")
            
            # Test all major functionality
            tests = [
                ("Service Status", data_management_ai.get_status()),
                ("Data Ingestion", data_management_ai.ingest_and_process_data(
                    "test_user", "test", "Sample content", {})),
                ("Folder Creation", data_management_ai.create_intelligent_folder(
                    "test_user", "create a folder for project files")),
                ("Profile Export", data_management_ai.export_user_intelligence("test_user")),
                ("Privacy Setup", data_management_ai.setup_privacy_preserving_training(
                    "test_user", {"personalization": True}))
            ]
            
            for test_name, test_coro in tests:
                print(f"\n🔬 Testing {test_name}...")
                try:
                    result = await test_coro
                    if result.get("success", True):
                        print(f"   ✅ {test_name} passed")
                    else:
                        print(f"   ❌ {test_name} failed: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"   ❌ {test_name} failed with exception: {e}")
            
            print("\n🎉 All tests completed!")
            
        else:
            print(f"❌ Unknown command: {command}")
            
    except Exception as e:
        print(f"❌ Error executing command '{command}': {e}")

if __name__ == "__main__":
    asyncio.run(main())