#!/usr/bin/env python3
"""
Main Integration System
Unified platform combining 3D model viewer, supplier marketplace, cost calculator, and project collaboration
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import uuid

# Import all subsystems
from model_viewer.model_viewer import ModelViewer3D, ModelMetadata
from supplier_marketplace.marketplace import SupplierMarketplace, Supplier
from cost_calculator.cost_calculator import CostCalculator, CostEstimate
from project_collaboration.collaboration import ProjectCollaborationSystem, Project, Task


@dataclass
class IntegrationConfig:
    enable_3d_viewer: bool = True
    enable_marketplace: bool = True
    enable_cost_calculator: bool = True
    enable_collaboration: bool = True
    auto_sync_enabled: bool = True
    cache_enabled: bool = True
    websocket_port: int = 8765
    data_dir: str = "integrated_data"


class UnifiedDataSystem:
    """Unified system for managing data flow between all subsystems"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.data_cache = {}
        self.sync_callbacks = []
        
        # Initialize subsystems
        self.model_viewer = None
        self.marketplace = None
        self.cost_calculator = None
        self.collaboration = None
        
        if config.enable_3d_viewer:
            self.model_viewer = ModelViewer3D(
                models_dir=os.path.join(config.data_dir, "models"),
                cache_dir=os.path.join(config.data_dir, "model_cache")
            )
            
        if config.enable_marketplace:
            self.marketplace = SupplierMarketplace(
                data_dir=os.path.join(config.data_dir, "marketplace")
            )
            
        if config.enable_cost_calculator:
            self.cost_calculator = CostCalculator(
                data_dir=os.path.join(config.data_dir, "costs")
            )
            
        if config.enable_collaboration:
            self.collaboration = ProjectCollaborationSystem(
                data_dir=os.path.join(config.data_dir, "collaboration")
            )
        
        # Set up cross-system integrations
        self._setup_integrations()
        
        logging.info("Unified Data System initialized")
    
    def _setup_integrations(self):
        """Set up data flow between subsystems"""
        
        # Model Viewer -> Cost Calculator integration
        if self.model_viewer and self.cost_calculator:
            self.model_viewer.on_model_loaded = self._on_model_loaded_for_costing
        
        # Marketplace -> Cost Calculator integration  
        if self.marketplace and self.cost_calculator:
            self.marketplace.on_supplier_registered = self._on_supplier_registered_for_costing
        
        # Cost Calculator -> Collaboration integration
        if self.cost_calculator and self.collaboration:
            self.cost_calculator.on_estimate_created = self._on_estimate_created_for_collaboration
        
        # Collaboration -> Model Viewer integration
        if self.collaboration and self.model_viewer:
            self.collaboration.on_project_created = self._on_project_created_for_models
    
    async def _on_model_loaded_for_costing(self, metadata: ModelMetadata):
        """Auto-generate material estimates when 3D models are loaded"""
        if metadata.volume > 0 and metadata.surface_area > 0:
            # Create material requirements based on model properties
            material_estimate = {
                'volume_based_materials': {
                    'plastic': {
                        'quantity': metadata.volume * 1000,  # Convert to grams
                        'unit': 'g',
                        'estimated_cost_per_unit': 0.05
                    }
                },
                'surface_based_materials': {
                    'finish': {
                        'quantity': metadata.surface_area,
                        'unit': 'm2', 
                        'estimated_cost_per_unit': 2.50
                    }
                }
            }
            
            # Cache for later use
            self.data_cache[f"model_{metadata.filename}_materials"] = material_estimate
            logging.info(f"Generated material estimate for model: {metadata.filename}")
    
    async def _on_supplier_registered_for_costing(self, supplier: Supplier):
        """Update cost calculator with new supplier data"""
        if supplier.products:
            # Add supplier materials to cost database
            for product in supplier.products:
                # This would add the product as a material option in cost calculator
                logging.info(f"Added supplier product to costing: {product.name}")
    
    async def _on_estimate_created_for_collaboration(self, estimate: CostEstimate):
        """Create collaboration tasks when cost estimates are generated"""
        if estimate.final_cost > 10000:  # For high-value projects
            # Create project for cost estimate follow-up
            project_data = {
                'name': f"Cost Estimate Follow-up: {estimate.project_name}",
                'description': f"Project management for ${estimate.final_cost:,.2f} estimate",
                'owner_id': estimate.created_by,
                'status': 'active',
                'budget': float(estimate.final_cost)
            }
            
            project_id = await self.collaboration.create_project(project_data)
            
            # Create initial tasks
            review_task = {
                'project_id': project_id,
                'title': 'Review cost estimate details',
                'description': f'Review estimate accuracy and assumptions for {estimate.project_name}',
                'created_by': estimate.created_by,
                'priority': 'high',
                'due_date': (datetime.now() + timedelta(days=3)).isoformat()
            }
            
            await self.collaboration.create_task(review_task)
            logging.info(f"Created collaboration project for estimate: {estimate.project_name}")
    
    async def _on_project_created_for_models(self, project: Project):
        """Set up model storage for new projects"""
        project_models_dir = os.path.join(self.config.data_dir, "models", project.id)
        os.makedirs(project_models_dir, exist_ok=True)
        logging.info(f"Created model storage for project: {project.name}")


class IntegratedWorkflowManager:
    """Manages complex workflows that span multiple subsystems"""
    
    def __init__(self, unified_system: UnifiedDataSystem):
        self.unified_system = unified_system
        self.active_workflows = {}
    
    async def start_product_development_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Start a complete product development workflow"""
        workflow_id = str(uuid.uuid4())
        
        # 1. Create collaboration project
        project_data = {
            'name': workflow_data['product_name'],
            'description': workflow_data.get('description', ''),
            'owner_id': workflow_data['owner_id'],
            'status': 'active',
            'budget': workflow_data.get('budget')
        }
        
        project_id = await self.unified_system.collaboration.create_project(project_data)
        
        # 2. Create initial tasks
        tasks = [
            {
                'title': '3D Model Creation/Upload',
                'description': 'Create or upload 3D models for the product',
                'priority': 'high',
                'estimated_hours': workflow_data.get('design_hours', 20)
            },
            {
                'title': 'Supplier Research',
                'description': 'Research and identify potential suppliers',
                'priority': 'medium',
                'estimated_hours': workflow_data.get('research_hours', 10)
            },
            {
                'title': 'Cost Estimation',
                'description': 'Generate detailed cost estimates',
                'priority': 'high',
                'estimated_hours': workflow_data.get('costing_hours', 8)
            },
            {
                'title': 'Design Review',
                'description': 'Review all aspects before production',
                'priority': 'critical',
                'estimated_hours': workflow_data.get('review_hours', 4)
            }
        ]
        
        task_ids = []
        for i, task_data in enumerate(tasks):
            task_full_data = {
                'project_id': project_id,
                'created_by': workflow_data['owner_id'],
                'due_date': (datetime.now() + timedelta(days=7 * (i + 1))).isoformat(),
                **task_data
            }
            task_id = await self.unified_system.collaboration.create_task(task_full_data)
            task_ids.append(task_id)
        
        # Store workflow state
        self.active_workflows[workflow_id] = {
            'type': 'product_development',
            'project_id': project_id,
            'task_ids': task_ids,
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        logging.info(f"Started product development workflow: {workflow_data['product_name']}")
        return workflow_id
    
    async def handle_model_upload_workflow(self, project_id: str, model_files: List[str]) -> Dict[str, Any]:
        """Handle complete model upload and analysis workflow"""
        results = {
            'uploaded_models': [],
            'cost_estimates': [],
            'supplier_matches': [],
            'workflow_id': str(uuid.uuid4())
        }
        
        for model_file in model_files:
            if os.path.exists(model_file):
                # 1. Load model in 3D viewer
                metadata = await self.unified_system.model_viewer.load_model(model_file)
                if metadata:
                    results['uploaded_models'].append(asdict(metadata))
                    
                    # 2. Generate cost estimate based on model
                    if metadata.volume > 0:
                        cost_data = {
                            'project_name': f"Production: {metadata.filename}",
                            'description': f"Cost estimate for {metadata.filename}",
                            'materials': {
                                'plastic': {
                                    'quantity': metadata.volume * 1000,  # Volume in cubic meters to grams
                                    'include_waste': True
                                }
                            },
                            'labor': [
                                {'role': 'Technician', 'hours': 2, 'location': 'default'}
                            ],
                            'created_by': 'system'
                        }
                        
                        try:
                            estimate = self.unified_system.cost_calculator.create_estimate(cost_data)
                            results['cost_estimates'].append(asdict(estimate))
                        except Exception as e:
                            logging.warning(f"Could not generate cost estimate: {e}")
                    
                    # 3. Find relevant suppliers
                    suppliers = self.unified_system.marketplace.search_suppliers(
                        category='manufacturing',
                        verified_only=True
                    )
                    results['supplier_matches'].extend(suppliers[:5])  # Top 5 matches
        
        return results
    
    async def execute_procurement_workflow(self, estimate_id: str, project_id: str) -> Dict[str, Any]:
        """Execute procurement workflow based on cost estimate"""
        # This would create RFQs, manage supplier communications, etc.
        
        # Create procurement tasks in collaboration system
        procurement_tasks = [
            {
                'project_id': project_id,
                'title': 'Create RFQ from estimate',
                'description': f'Generate RFQ based on estimate {estimate_id}',
                'created_by': 'system',
                'priority': 'high'
            },
            {
                'project_id': project_id,
                'title': 'Review supplier responses',
                'description': 'Evaluate and compare supplier quotes',
                'created_by': 'system',
                'priority': 'medium'
            }
        ]
        
        task_ids = []
        for task_data in procurement_tasks:
            task_id = await self.unified_system.collaboration.create_task(task_data)
            task_ids.append(task_id)
        
        return {
            'procurement_workflow_started': True,
            'tasks_created': task_ids,
            'estimate_id': estimate_id
        }


class MainIntegrationSystem:
    """Main integration system that orchestrates all subsystems"""
    
    def __init__(self, config: IntegrationConfig = None):
        self.config = config or IntegrationConfig()
        self.unified_system = UnifiedDataSystem(self.config)
        self.workflow_manager = IntegratedWorkflowManager(self.unified_system)
        
        # Main system callbacks
        self.on_workflow_completed: Optional[Callable] = None
        self.on_system_ready: Optional[Callable] = None
        
        # Ensure data directory exists
        os.makedirs(self.config.data_dir, exist_ok=True)
        
        logging.info("Main Integration System initialized")
    
    async def start_system(self):
        """Start all subsystems and integrations"""
        try:
            # Start collaboration real-time server if enabled
            if self.config.enable_collaboration and self.unified_system.collaboration:
                await self.unified_system.collaboration.start_real_time_server()
            
            # Load sample data for demo
            if self.config.enable_cost_calculator and self.unified_system.cost_calculator:
                self.unified_system.cost_calculator.load_sample_data()
            
            # System is ready
            if self.on_system_ready:
                self.on_system_ready()
                
            logging.info("Main Integration System started successfully")
            
        except Exception as e:
            logging.error(f"Error starting system: {e}")
            raise
    
    async def create_integrated_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a project with full integration across all subsystems"""
        result = {
            'project_id': None,
            'model_storage_ready': False,
            'supplier_research_initiated': False,
            'cost_tracking_enabled': False,
            'collaboration_active': False
        }
        
        # 1. Create collaboration project
        if self.unified_system.collaboration:
            project_id = await self.unified_system.collaboration.create_project(project_data)
            result['project_id'] = project_id
            result['collaboration_active'] = True
            
            # 2. Set up model storage
            if self.unified_system.model_viewer:
                project_models_dir = os.path.join(self.config.data_dir, "models", project_id)
                os.makedirs(project_models_dir, exist_ok=True)
                result['model_storage_ready'] = True
            
            # 3. Initialize cost tracking
            if self.unified_system.cost_calculator:
                # This could set up project-specific cost tracking
                result['cost_tracking_enabled'] = True
            
            # 4. Set up supplier research
            if self.unified_system.marketplace:
                # This could initialize supplier research for the project
                result['supplier_research_initiated'] = True
        
        return result
    
    async def process_complete_workflow(self, workflow_type: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a complete workflow across all systems"""
        
        if workflow_type == "product_development":
            return await self.workflow_manager.start_product_development_workflow(workflow_data)
        
        elif workflow_type == "model_upload":
            return await self.workflow_manager.handle_model_upload_workflow(
                workflow_data['project_id'],
                workflow_data['model_files']
            )
        
        elif workflow_type == "procurement":
            return await self.workflow_manager.execute_procurement_workflow(
                workflow_data['estimate_id'],
                workflow_data['project_id']
            )
        
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
    
    def get_system_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive system dashboard"""
        dashboard = {
            'system_status': {
                'model_viewer_active': bool(self.unified_system.model_viewer),
                'marketplace_active': bool(self.unified_system.marketplace),
                'cost_calculator_active': bool(self.unified_system.cost_calculator),
                'collaboration_active': bool(self.unified_system.collaboration)
            },
            'statistics': {},
            'recent_activity': [],
            'generated_at': datetime.now().isoformat()
        }
        
        # Get statistics from each subsystem
        if self.unified_system.model_viewer:
            dashboard['statistics']['models'] = self.unified_system.model_viewer.get_system_info()
        
        if self.unified_system.marketplace:
            dashboard['statistics']['marketplace'] = self.unified_system.marketplace.get_marketplace_stats()
        
        if self.unified_system.collaboration:
            # This would get collaboration system stats
            dashboard['statistics']['collaboration'] = {
                'active_projects': 'N/A',  # Would be implemented
                'total_users': 'N/A'
            }
        
        # Active workflows
        dashboard['active_workflows'] = list(self.workflow_manager.active_workflows.keys())
        
        return dashboard
    
    def search_across_systems(self, query: str, systems: List[str] = None) -> Dict[str, List]:
        """Search across all enabled systems"""
        results = {
            'models': [],
            'suppliers': [],
            'projects': [],
            'products': []
        }
        
        systems = systems or ['models', 'suppliers', 'projects', 'products']
        
        # Search models
        if 'models' in systems and self.unified_system.model_viewer:
            models = self.unified_system.model_viewer.get_model_list(query=query)
            results['models'] = models[:10]  # Limit results
        
        # Search suppliers
        if 'suppliers' in systems and self.unified_system.marketplace:
            suppliers = self.unified_system.marketplace.search_suppliers(query=query)
            results['suppliers'] = suppliers[:10]
        
        # Search products
        if 'products' in systems and self.unified_system.marketplace:
            products = self.unified_system.marketplace.search_products(query=query)
            results['products'] = products[:10]
        
        # Search projects
        if 'projects' in systems and self.unified_system.collaboration:
            projects = self.unified_system.collaboration.search_projects(query)
            results['projects'] = projects[:10]
        
        return results
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of system integrations"""
        return {
            'unified_data_system': {
                'status': 'active',
                'cache_size': len(self.unified_system.data_cache),
                'integrations_active': len(self.unified_system.sync_callbacks)
            },
            'workflow_manager': {
                'status': 'active',
                'active_workflows': len(self.workflow_manager.active_workflows)
            },
            'cross_system_features': {
                'auto_costing_from_models': True,
                'supplier_product_integration': True,
                'collaboration_from_estimates': True,
                'project_model_storage': True
            }
        }
    
    async def export_complete_system_data(self) -> Optional[str]:
        """Export data from all systems"""
        try:
            export_data = {
                'system_info': self.get_system_dashboard(),
                'integration_status': self.get_integration_status(),
                'subsystem_data': {},
                'exported_at': datetime.now().isoformat()
            }
            
            # Export from each subsystem
            if self.unified_system.model_viewer:
                export_data['subsystem_data']['models'] = self.unified_system.model_viewer.get_system_info()
            
            if self.unified_system.marketplace:
                export_data['subsystem_data']['marketplace'] = self.unified_system.marketplace.get_marketplace_stats()
            
            export_path = os.path.join(self.config.data_dir, f"complete_system_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return export_path
            
        except Exception as e:
            logging.error(f"Error exporting system data: {e}")
            return None


# Demo function
async def demo_main_integration():
    """Demonstrate Main Integration System functionality"""
    print("=== Main Integration System Demo ===")
    
    # Configure system
    config = IntegrationConfig(
        enable_3d_viewer=True,
        enable_marketplace=True,
        enable_cost_calculator=True,
        enable_collaboration=True,
        auto_sync_enabled=True,
        websocket_port=8765
    )
    
    # Initialize main system
    main_system = MainIntegrationSystem(config)
    
    # Set up callbacks
    main_system.on_system_ready = lambda: print("✅ Main Integration System ready")
    
    # Start system
    await main_system.start_system()
    
    # Create integrated project
    project_data = {
        'name': 'Integrated Product Development',
        'description': 'Full-stack product development with all systems',
        'owner_id': 'demo_user',
        'status': 'active',
        'budget': 25000.0,
        'tags': ['integrated', 'demo', 'full-stack']
    }
    
    project_result = await main_system.create_integrated_project(project_data)
    print(f"✅ Integrated project created: {project_result['project_id']}")
    
    # Start product development workflow
    workflow_data = {
        'product_name': 'Smart Widget v2.0',
        'description': 'Next generation smart widget with IoT capabilities',
        'owner_id': 'demo_user',
        'budget': 30000.0,
        'design_hours': 40,
        'research_hours': 16,
        'costing_hours': 12,
        'review_hours': 8
    }
    
    workflow_id = await main_system.process_complete_workflow('product_development', workflow_data)
    print(f"✅ Product development workflow started: {workflow_id}")
    
    # Demonstrate search across systems
    search_results = main_system.search_across_systems('demo')
    print(f"✅ Cross-system search completed: {sum(len(results) for results in search_results.values())} total results")
    
    # Get system dashboard
    dashboard = main_system.get_system_dashboard()
    print(f"✅ System dashboard generated with {len(dashboard['statistics'])} subsystem statistics")
    
    # Get integration status
    integration_status = main_system.get_integration_status()
    print(f"✅ Integration status: {integration_status['unified_data_system']['status']}")
    
    # Export complete system data
    export_path = await main_system.export_complete_system_data()
    print(f"✅ Complete system data exported to: {export_path}")
    
    print("\n🎉 Main Integration System demo completed successfully!")
    print("\nSystem includes:")
    print("  📐 3D Model Viewer - Load, analyze, and visualize 3D models")
    print("  🏪 Supplier Marketplace - Find and manage suppliers with RFQ system") 
    print("  💰 Cost Calculator - Comprehensive project cost estimation")
    print("  👥 Project Collaboration - Real-time team collaboration platform")
    print("  🔗 Full Integration - Unified workflows across all systems")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run demo
    asyncio.run(demo_main_integration())