{
  "trigger_patterns": {
    "infrastructure_puzzles": {
      "trigger": "k8s.*blocked|docker.*failed|network.*timeout",
      "inject_to": "infrastructure",
      "knowledge": {
        "title": "Container Orchestration Fallback Strategies",
        "content": "When K8s fails: 1) Use Docker Compose in services/ dir, 2) Check /home/activeloguser/activelog/docker_compose_services.yml, 3) Verify network bridges with 'docker network ls', 4) Use host networking as last resort",
        "confidence": "high",
        "trigger": "Any container orchestration failure"
      }
    },
    "database_puzzles": {
      "trigger": "postgres.*error|database.*blocked|migration.*failed",
      "inject_to": "services",
      "knowledge": {
        "title": "Database Recovery and Schema Management",
        "content": "For DB issues: 1) Check connection string format, 2) Use SQLite fallback in dev, 3) Schema conflicts require manual merge, 4) Always backup before migrations, 5) Use /home/activeloguser/activelog/activelog_fitness_schema.sql as reference",
        "confidence": "high", 
        "trigger": "Database connection or schema issues"
      }
    },
    "auth_integration_puzzles": {
      "trigger": "auth.*blocked|jwt.*error|token.*invalid",
      "inject_to": ["services", "domains"],
      "knowledge": {
        "title": "Authentication Integration Patterns",
        "content": "For auth issues: 1) Use jwt_middleware_template.py in all domains, 2) Verify SECRET_KEY consistency, 3) Check token expiry settings, 4) Test /auth/verify endpoint first, 5) CORS settings for cross-origin requests",
        "confidence": "high",
        "trigger": "Authentication or JWT token issues"
      }
    },
    "domain_deployment_puzzles": {
      "trigger": "domain.*deploy.*blocked|service.*mesh.*error",
      "inject_to": "domains",
      "knowledge": {
        "title": "Domain Service Deployment Best Practices",
        "content": "For domain deployment: 1) Always check auth-service health first, 2) Use provided fitness schema from activelog_fitness_schema.sql, 3) Test cross-domain APIs with curl, 4) Monitor service discovery, 5) ActiveLog fitness domain has SuperInstance priority",
        "confidence": "high",
        "trigger": "Domain service deployment issues"
      }
    }
  },
  "proactive_knowledge_schedule": {
    "phase_transitions": {
      "infrastructure_to_services": {
        "condition": "k8s-ready.flag exists OR docker-fallback active",
        "inject": [
          {
            "bot": "services",
            "knowledge_type": "deployment_templates",
            "files": ["k8s_auth_service_manifest.yaml", "docker_compose_services.yml"]
          }
        ]
      },
      "services_to_domains": {
        "condition": "auth-service-ready.flag exists",
        "inject": [
          {
            "bot": "domains", 
            "knowledge_type": "auth_integration",
            "files": ["jwt_middleware_template.py", "activelog_fitness_schema.sql"]
          }
        ]
      },
      "domains_active": {
        "condition": "activelog.*START OR fitness.*schema",
        "inject": [
          {
            "bot": "domains",
            "knowledge_type": "cross_domain_patterns", 
            "content": "SuperInstance rebranding priority: ActiveLog fitness domain must demonstrate cross-domain value creation through productivity correlations"
          }
        ]
      }
    }
  },
  "quality_assurance_triggers": {
    "right_first_time_patterns": {
      "high_rework_detected": {
        "condition": "fix|retry|redo|rollback count > 3 in last 20 updates",
        "action": "inject_testing_templates",
        "target": "all_bots"
      },
      "recurring_puzzle_type": {
        "condition": "same puzzle category > 2 times",
        "action": "create_troubleshooting_guide",
        "target": "specific_bot"
      },
      "successful_completion": {
        "condition": "COMPLETE without prior BLOCKED",
        "action": "capture_success_pattern",
        "target": "knowledge_base"
      }
    }
  },
  "communication_optimization_triggers": {
    "stuck_task_escalation": {
      "condition": "BLOCKED status > 10 minutes",
      "action": "inject_alternative_approaches",
      "escalate_to": "foreman_direct_assistance"
    },
    "parallel_work_opportunities": {
      "condition": "bot waiting for dependency",
      "action": "inject_preparatory_tasks", 
      "maintain_productivity": true
    }
  }
}