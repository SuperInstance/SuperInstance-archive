# ActiveLog System Audit Report

**Generated:** 2025-08-22 22:17:17

## Executive Summary

- **Total Services:** 66
- **Dockerized Services:** 11
- **Total Code Files:** 669
- **Security Issues Found:** 190
- **TODO/FIXME Items:** 396

## Services Overview

### sync-v2

**Description:** ActiveLog.ai Sync Service v2 - Main Entry Point

Unified sync service orchestrating all synchronization components.
**Dockerized:** ❌ No
**Files:** 9
**Dependencies:** 33
**API Endpoints:** 0
**AI Integrations:** None

### notification

**Description:** 
**Dockerized:** ✅ Yes
**Files:** 0
**Dependencies:** 0
**API Endpoints:** 0
**AI Integrations:** None

### quantum-ready

**Description:** Quantum-Ready Services for ActiveLog
Preparing for the quantum computing era with quantum-resistant algorithms,
quantum algorithm interfaces, and post-quantum cryptography
**Dockerized:** ❌ No
**Files:** 13
**Dependencies:** 58
**API Endpoints:** 0
**AI Integrations:** None

### graphql

**Description:** 
**Dockerized:** ❌ No
**Files:** 0
**Dependencies:** 0
**API Endpoints:** 0
**AI Integrations:** None

### activeledger

**Description:** ActiveLedger Configuration Settings
**Dockerized:** ❌ No
**Files:** 21
**Dependencies:** 32
**API Endpoints:** 0
**AI Integrations:** None

### api-gateway

**Description:** Initialize Redis connection
**Dockerized:** ❌ No
**Files:** 2
**Dependencies:** 17
**API Endpoints:** 4
**AI Integrations:** None

**API Endpoints:**
- `/metrics`
- `/health`
- `/auth/validate`
- `/`

### dmlog-ai-dm

**Description:** AI DM Assistant Main Service

Orchestrates all AI DM components to provide comprehensive DM assistance
**Dockerized:** ❌ No
**Files:** 10
**Dependencies:** 30
**API Endpoints:** 8
**AI Integrations:** openai

**API Endpoints:**
- `/campaigns/{campaign_id}/sessions`
- `/sessions/{session_id}/actions`
- `/campaigns/{campaign_id}`
- `/campaigns`
- `/health`
- `/sessions/{session_id}`
- `/stats`
- `/sessions/{session_id}/assistance`

### dmlog-session

**Description:** D&D Session Management Service

Main orchestrator that coordinates all session management features including
audio recording, transcription, notes, highlights, scheduling, virtual tabletop,
content sharing, ambiance, analytics, and feedback collection.
**Dockerized:** ❌ No
**Files:** 18
**Dependencies:** 74
**API Endpoints:** 8
**AI Integrations:** torch, transformers

**API Endpoints:**
- `/sessions/{session_id}/end`
- `/sessions/{session_id}/start`
- `/sessions`
- `/health`
- `/sessions/{session_id}/analytics`
- `/sessions/{session_id}/feedback`
- `/sessions/{session_id}/status`
- `/sessions/{session_id}/recap`

### multiverse

**Description:** Multiverse Reality Layers Management System

This module provides comprehensive multiverse reality management with shared reality layers,
consensus verification, parallel universe navigation, quantum communication, and 
cross-dimensional asset management.

Key Features:
- Shared reality layers between users and dimensions
- Consensus reality verification and validation
- Parallel universe browsing and navigation
- Time-locked message system with temporal encryption
- Spatial data persistence across dimensions
- Cross-reality asset transfer and validation
- Dimensional data bridging and synchronization
- Reality fork detection and analysis
- Merge conflict resolution for reality splits
- Probability wave collapse logging and analysis
- Quantum entanglement communication channels
- Multiverse portfolio management and optimization
**Dockerized:** ❌ No
**Files:** 1
**Dependencies:** 17
**API Endpoints:** 0
**AI Integrations:** None

### dmlog-templates

**Description:** D&D Template System Main Service

Main orchestrator that provides unified access to all template generators
including adventures, characters, encounters, mysteries, political intrigue,
and horror elements.
**Dockerized:** ❌ No
**Files:** 21
**Dependencies:** 46
**API Endpoints:** 23
**AI Integrations:** torch

**API Endpoints:**
- `/characters/backstories`
- `/horror/scenarios`
- `/heists/plans`
- `/templates/{template_type}/suggestions`
- `/encounters/social`
- `/characters/npcs`
- `/quick/puzzle`
- `/encounters/puzzles`
- `/cache/clear`
- `/mysteries`
- `/quick/npc`
- `/encounters/chases`
- `/health`
- `/stats`
- `/plots/twists`
- `/encounters/traps`
- `/encounters/sequences`
- `/campaigns`
- `/oneshots`
- `/adventures`
- `/quick/adventure`
- `/horror/atmosphere`
- `/politics/intrigue`

### emotional-ai

**Description:** Mood Detection from Writing Patterns
Analyzes text to detect emotional states and mood patterns
**Dockerized:** ❌ No
**Files:** 6
**Dependencies:** 27
**API Endpoints:** 0
**AI Integrations:** None

### marine-advanced

**Description:** ActiveLog Marine Advanced Suite - Sail Trim Optimization Using Wind Sensors

Advanced sail trim optimization system with real-time wind sensor analysis,
performance calculations, and AI-driven recommendations for optimal sailing configuration.
**Dockerized:** ❌ No
**Files:** 6
**Dependencies:** 30
**API Endpoints:** 0
**AI Integrations:** None

### workflows

**Description:** ActiveLog Workflows Service

Comprehensive workflow automation service with:
- IFTTT-style triggers and actions
- Zapier-compatible webhook system
- Custom workflow designer API
- Scheduled workflows (cron-style)
- Conditional logic and branching
- Integration with external services
- Workflow templates marketplace
**Dockerized:** ❌ No
**Files:** 23
**Dependencies:** 66
**API Endpoints:** 20
**AI Integrations:** None

**API Endpoints:**
- `author_name`
- `/designer/actions`
- `/designer/conditions`
- `/workflows/{workflow_id}/execute`
- `/`
- `/dev/test-workflow`
- `/workflows`
- `/webhooks/{endpoint_id}`
- `/workflows/{workflow_id}`
- `/dev/reset-db`
- `/workflows/{workflow_id}/webhooks`
- `/workflows/{workflow_id}/executions`
- `/designer/validate-workflow`
- `/health`
- `/executions/{execution_id}`
- `/marketplace/featured`
- `/designer/triggers`
- `/webhook/{endpoint_id}`
- `/metrics`
- `/executions/{execution_id}/cancel`

### dmlog-core

**Description:** Configuration settings for DMLog Core RPG Rules Engine.
**Dockerized:** ✅ Yes
**Files:** 38
**Dependencies:** 69
**API Endpoints:** 150
**AI Integrations:** None

**API Endpoints:**
- `/{spell_id}`
- `/probability/advantage`
- `/generate/batch`
- `/{character_id}/level-up`
- `/`
- `/{campaign_id}/events/`
- `/{npc_id}/stats/combat`
- `/inventories/{inventory_id}/items/{item_id}/attune`
- `/templates/`
- `/character-types`
- `/treasure/hoard/{challenge_rating}`
- `/calculate`
- `/templates/create`
- `/multipliers`
- `/items/search`
- `/{encounter_id}`
- `/quick-reference/{game_system}/{category}`
- `/{rule_id}/interpretations/`
- `/campaigns/{campaign_id}/cliques`
- `/{character_id}/damage`
- `/items/generate`
- `/characters/{character_id}/inventory/`
- `/presets`
- `/{character_id}`
- `/encounters/{encounter_id}/status`
- `/roll`
- `/roll/multiple`
- `/inventories/{inventory_id}/currency`
- `/{campaign_id}/statistics`
- `/relationships/batch`
- `/{campaign_id}/events/{event_id}/relationships`
- `/{campaign_id}/sessions/{session_id}/complete`
- `/discovery/calculate`
- `/tables/`
- `/encounters/{encounter_id}/start`
- `/inventories/{inventory_id}/summary`
- `/encounters/{encounter_id}/initiative`
- `/conflicts/{game_system}`
- `/categories`
- `/{npc_id}`
- `/levels/{spell_level}/spells`
- `/generate/random`
- `/cr/{challenge_rating}/xp`
- `/characters/{character_id}/progression`
- `/characters/batch`
- `/types`
- `/campaigns/{campaign_id}/conflicts`
- `/milestones/{milestone_id}/complete`
- `/{campaign_id}/summary`
- `/tables/{table_id}/entries/`
- `/encounters/{encounter_id}/next-turn`
- `/encounters/{encounter_id}`
- `/calendar/templates`
- `/characters/{character_id}`
- `/generate`
- `/inventories/{inventory_id}/containers/`
- `/search`
- `/{campaign_id}/npcs/`
- `/inventories/{inventory_id}/items/remove`
- `/characters/{character_id}/centrality`
- `/{campaign_id}/timeline`
- `/{campaign_id}/locations/`
- `/schools`
- `/characters/{character_id}/analysis`
- `/campaigns/{campaign_id}/graph`
- `/roleplay/calculate`
- `/instances/{instance_id}/cast`
- `/{rule_id}/clarifications/`
- `/difficulty/thresholds`
- `/resources/{pool_id}/restore`
- `/{character_id}/summary`
- `/participants/{participant_id}/damage`
- `/characters/{character_id}/resources/`
- `/probability/single`
- `/statistics`
- `/award`
- `/encounters/{encounter_id}/participants/`
- `/levelup`
- `/participants/{participant_id}/conditions/{condition_name}`
- `/currency/generate`
- `/campaigns/{campaign_id}/statistics`
- `/balance/quick`
- `/inventories/{inventory_id}/value`
- `/{relationship_id}/history`
- `/items/{item_id}`
- `/health`
- `/characters/`
- `/{relationship_id}`
- `/encounters/{encounter_id}/actions/`
- `/encounters/{encounter_id}/end`
- `/batch/award`
- `/search/suggestions`
- `/characters/{character_id}/rest/long`
- `/transfer`
- `/validate`
- `/campaign/{campaign_id}/by-faction`
- `/history`
- `/characters/{character_id}/suggestions`
- `/{rule_id}`
- `/webs/`
- `/resources/{pool_id}/consume`
- `/inventories/{inventory_id}/items/add`
- `/characters/{character_id}/rest/short`
- `/batch/create`
- `/probability/target`
- `/validate/relationship`
- `/tables/xp-by-level`
- `/{campaign_id}`
- `/{npc_id}/interactions/`
- `/characters/{character_id}/spell-slots/configure`
- `/campaigns/{campaign_id}/milestones`
- `/characters/{character_id}/inventory`
- `/milestones/`
- `/save`
- `/probability/sum`
- `/rarities`
- `/items/`
- `/{character_id}/heal`
- `/instances/`
- `/{campaign_id}/calendar/advance`
- `/{campaign_id}/events/search`
- `/inventories/{inventory_id}/sort`
- `/generate/quick`
- `/event-types`
- `/tables/proficiency-bonus`
- `/combat/calculate`
- `/systems`
- `/quest/calculate`
- `/{relationship_id}/events/`
- `/balance/analyze`
- `/suggestions/random`
- `/collections`
- `/characters/{character_id}/spells`
- `/{rule_id}/related`
- `/participants/{participant_id}/conditions/`
- `/level/{level}/features`
- `/encounters/`
- `/recent`
- `/roles`
- `/treasure/individual/{challenge_rating}`
- `/{npc_id}/personality/analyze`
- `/popular`
- `/{campaign_id}/backup`
- `/{campaign_id}/calendar/`
- `/participants/{participant_id}/heal`
- `/{campaign_id}/sessions/`
- `/campaign/{campaign_id}/by-location`
- `/tables/{table_id}/generate`
- `/characters/search`
- `/inventories/{inventory_id}/encumbrance`

### cognitive

**Description:** 
**Dockerized:** ❌ No
**Files:** 0
**Dependencies:** 0
**API Endpoints:** 0
**AI Integrations:** None

### data-export

**Description:** ActiveLog Data Export Service

Comprehensive data export service providing multiple export formats:
- PDF documents with preserved metadata
- ZIP and tar.gz archives
- Static website generation
- Photo books and albums
- GDPR-compliant data exports
- Bulk export with progress tracking
- Cloud provider integration
**Dockerized:** ❌ No
**Files:** 12
**Dependencies:** 80
**API Endpoints:** 6
**AI Integrations:** None

**API Endpoints:**
- `/exports/progress/{export_id}`
- `/metrics`
- `/health`
- `/exports/{export_id}`
- `/exports/{export_id}/download`
- `/`

### file-sync

**Description:** 
**Dockerized:** ❌ No
**Files:** 1
**Dependencies:** 4
**API Endpoints:** 3
**AI Integrations:** None

**API Endpoints:**
- `/upload`
- `/health`
- `/`

### universal-translator

**Description:** Code Language Translation System

This module provides comprehensive code translation capabilities between different
programming languages, with focus on Python to Rust translation while maintaining
functionality, idioms, and best practices.
**Dockerized:** ❌ No
**Files:** 12
**Dependencies:** 25
**API Endpoints:** 0
**AI Integrations:** mediapipe

### social-ai

**Description:** Social Energy Tracker

AI-powered system for monitoring and optimizing social interaction patterns
to maintain healthy social energy levels and prevent burnout.
**Dockerized:** ❌ No
**Files:** 12
**Dependencies:** 17
**API Endpoints:** 0
**AI Integrations:** tensorflow

### predictive-ai

**Description:** Smart Pre-caching Engine - Intelligently pre-loads likely-needed files based on behavior prediction.
Uses predictive models to cache files before users need them, improving response times.
**Dockerized:** ❌ No
**Files:** 5
**Dependencies:** 14
**API Endpoints:** 0
**AI Integrations:** None

### ai-tools

**Description:** AI Tools Configuration Settings
**Dockerized:** ❌ No
**Files:** 18
**Dependencies:** 50
**API Endpoints:** 0
**AI Integrations:** huggingface, torch, anthropic, openai

### creative-suite

**Description:** ActiveLog Creative Suite - Style Transfer Between Mediums

This module provides intelligent style transfer capabilities across different creative mediums including:
- Visual style extraction and application (painting to digital, photo to illustration)
- Musical style analysis and cross-genre transfer
- Writing style adaptation between formats and genres
- Design pattern migration across mediums
- Color palette and mood translation
- Texture and material style conversion
- Temporal style mapping (vintage to modern, etc.)
- Cultural style interpretation and adaptation
**Dockerized:** ❌ No
**Files:** 2
**Dependencies:** 20
**API Endpoints:** 0
**AI Integrations:** None

### dmlog-characters

**Description:** Startup script for the Character AI Service.
**Dockerized:** ❌ No
**Files:** 24
**Dependencies:** 58
**API Endpoints:** 26
**AI Integrations:** torch

**API Endpoints:**
- `/dialogue/banter`
- `/faction/reputation/update`
- `/character/{character_id}/complete-interaction`
- `/mannerisms/generate`
- `/personality/generate`
- `/`
- `/memory/search`
- `/voice/clone`
- `/emotion/{character_id}`
- `/memory/create`
- `/gestures/generate`
- `/memory/recall`
- `/emotion/trigger`
- `/health`
- `/arc/{character_id}/analysis`
- `/dialogue/generate`
- `/arc/create`
- `/character/{character_id}/status`
- `/faction/reputation/{character_id}/analysis`
- `/portrait/generate`
- `/arc/progress`
- `/faction/reputation/{character_id}`
- `/personality/{character_id}/predict-behavior`
- `/voice/synthesize`
- `/portrait/templates`
- `/personality/{character_id}`

### education-ai

**Description:** Attention Tracking and Engagement Monitoring System

Advanced AI system for monitoring student attention and engagement during digital
learning sessions through behavioral analytics, interaction patterns, and
real-time feedback to optimize learning experiences and maintain focus.
**Dockerized:** ❌ No
**Files:** 10
**Dependencies:** 29
**API Endpoints:** 0
**AI Integrations:** None

### ambient

**Description:** Predictive Action Preparation System for Ambient Computing
Anticipates user needs and pre-loads resources, data, and actions based on behavior patterns and context
**Dockerized:** ❌ No
**Files:** 5
**Dependencies:** 16
**API Endpoints:** 0
**AI Integrations:** None

### backup

**Description:** ActiveLog Backup Service - Main FastAPI Application
Port: 8009
**Dockerized:** ❌ No
**Files:** 13
**Dependencies:** 52
**API Endpoints:** 21
**AI Integrations:** None

**API Endpoints:**
- `/api/v1/disaster-recovery/assessment`
- `/api/v1/recovery/full`
- `/api/v1/recovery/selective`
- `/`
- `/api/v1/disaster-recovery/test`
- `/api/v1/backups/full`
- `/api/v1/snapshots`
- `/api/v1/verification/history`
- `/api/v1/verification/restore-test/{snapshot_id}`
- `/health`
- `/api/v1/backups/incremental`
- `/api/v1/backups`
- `/api/v1/recovery/{recovery_id}/status`
- `/api/v1/recovery/point-in-time`
- `/api/v1/stats`
- `/api/v1/verification/integrity/{job_id}`
- `/api/v1/disaster-recovery/initialize`
- `/api/v1/disaster-recovery/status`
- `/api/v1/encryption/info`
- `/api/v1/backups/{job_id}/status`
- `/api/v1/encryption/rotate-keys`

### document-ai

**Description:** Simple run script for document AI service
**Dockerized:** ❌ No
**Files:** 26
**Dependencies:** 105
**API Endpoints:** 12
**AI Integrations:** torch, openai, transformers, huggingface, anthropic

**API Endpoints:**
- `/documents/upload`
- `/search/semantic`
- `/config/document-types`
- `/config/processing-options`
- `/documents/{job_id}/status`
- `/health`
- `/documents/{job_id}/results`
- `/config/languages`
- `/search/entities`
- `/search/text`
- `/analytics`
- `/documents/{job_id}/process`

### video-pipeline

**Description:** Video Pipeline Configuration Settings
**Dockerized:** ✅ Yes
**Files:** 15
**Dependencies:** 59
**API Endpoints:** 12
**AI Integrations:** torch, transformers

**API Endpoints:**
- `/api/videos/upload`
- `/api/jobs/{job_id}`
- `/api/videos/{video_id}`
- `/api/ai-callback`
- `/metrics`
- `/health`
- `/api/videos/{video_id}/status`
- `/api/videos`
- `/api/status`
- `/api/videos/{video_id}/analyze`
- `/health/detailed`
- `/api/videos/{video_id}/transcode`

### data-manager

**Description:** Main service orchestrator for the Data Management AI.
Provides a unified interface to all data management capabilities.
**Dockerized:** ❌ No
**Files:** 9
**Dependencies:** 32
**API Endpoints:** 19
**AI Integrations:** None

**API Endpoints:**
- `/classify`
- `/recommendations/{user_id}`
- `/user-profile/{user_id}`
- `/status`
- `/folders/suggestions/{user_id}`
- `/export/preferences/{user_id}`
- `/quality/alerts/{user_id}`
- `/privacy/consent/{user_id}`
- `/data/batch-ingest`
- `/health`
- `/user-behavior/{user_id}`
- `/analytics/{user_id}`
- `/folders/create`
- `/process/{data_item_id}`
- `/quality/{user_id}`
- `/data/ingest`
- `/insights/{user_id}`
- `/import/preferences/{user_id}`
- `/processing/status/{job_id}`

### security-advanced

**Description:** Anonymous Credentials System
Cryptographic credentials that allow authentication without revealing identity
**Dockerized:** ❌ No
**Files:** 13
**Dependencies:** 39
**API Endpoints:** 1
**AI Integrations:** None

**API Endpoints:**
- `keystrokes`

### batch-import

**Description:** ActiveLog Batch Import Service
Monitors import folder and processes files in batches
**Dockerized:** ❌ No
**Files:** 17
**Dependencies:** 48
**API Endpoints:** 16
**AI Integrations:** None

**API Endpoints:**
- `/configuration`
- `/supported-formats`
- `/health`
- `/stats`
- `/active-batches`
- `/reports`
- `/trigger-scan`
- `/reports/weekly`
- `/cleanup-reports`
- `/`
- `/reports/daily`
- `/directories`
- `/health-report`
- `/pending-files`
- `/status`
- `/process-batch`

### biological

**Description:** Biological Integration System

This module provides comprehensive biological data integration including DNA storage,
biometric authentication, neural interfaces, cellular monitoring, and biological
optimization systems for human-computer integration.

Key Features:
- DNA data storage encoding and decoding
- Continuous biometric authentication
- Pheromone-based communication and notifications
- Neural interface preparation and calibration
- Biological clock synchronization
- Real-time cellular activity monitoring
- Genetic predisposition analysis and alerts
- Microbiome optimization recommendations
- Biorhythm-aware scheduling and optimization
- Hormone cycle tracking and prediction
- Neural pattern backup and restoration
- Synaptic activity mapping and analysis
**Dockerized:** ❌ No
**Files:** 1
**Dependencies:** 17
**API Endpoints:** 0
**AI Integrations:** None

### dmlog-battle

**Description:** Configuration for the Combat Simulation Service.
**Dockerized:** ❌ No
**Files:** 15
**Dependencies:** 31
**API Endpoints:** 11
**AI Integrations:** None

**API Endpoints:**
- `/encounters/{encounter_id}`
- `/encounters/{encounter_id}/start`
- `/encounters/{encounter_id}/preview-spell`
- `/health`
- `/encounters`
- `/encounters/{encounter_id}/actions`
- `/encounters/{encounter_id}/movement-path`
- `/`
- `/encounters/{encounter_id}/line-of-sight`
- `/encounters/{encounter_id}/auto-resolve`
- `/encounters/{encounter_id}/visualization`

### ar-layer

**Description:** Spatial Anchoring System - Anchors digital data to physical locations in 3D space.
Creates persistent spatial relationships between data and real-world coordinates.
**Dockerized:** ❌ No
**Files:** 10
**Dependencies:** 26
**API Endpoints:** 0
**AI Integrations:** mediapipe

### metadata

**Description:** Initialize Elasticsearch indices
**Dockerized:** ✅ Yes
**Files:** 7
**Dependencies:** 21
**API Endpoints:** 12
**AI Integrations:** None

**API Endpoints:**
- `/{file_metadata_id}`
- `/tags/assign`
- `/{metadata_id}/tags/{tag_id}`
- `/{metadata_id}/assign`
- `/webhook/file-sync`
- `/health`
- `/metadata`
- `/{metadata_id}`
- `/{tag_id}`
- `/aggregations`
- `/search`
- `/`

### dmlog-player

**Description:** Main player interface service - orchestrates all player management functionality
**Dockerized:** ❌ No
**Files:** 9
**Dependencies:** 16
**API Endpoints:** 15
**AI Integrations:** torch

**API Endpoints:**
- `/characters/{character_id}/session-prep`
- `/characters/{character_id}/inventory`
- `/characters/{character_id}/journal`
- `/parties`
- `/characters/{character_id}/dashboard`
- `/characters/{character_id}/spells/quick-reference`
- `/characters/{character_id}/quests`
- `/health`
- `/characters`
- `/characters/{character_id}/encumbrance`
- `/characters/{character_id}`
- `/characters/{character_id}/party`
- `/characters/{character_id}/spells`
- `/characters/{character_id}/relationships`
- `/characters/{character_id}/quests/active`

### api_gateway

**Description:** 
**Dockerized:** ✅ Yes
**Files:** 0
**Dependencies:** 0
**API Endpoints:** 0
**AI Integrations:** None

### file_processor

**Description:** 
**Dockerized:** ✅ Yes
**Files:** 0
**Dependencies:** 0
**API Endpoints:** 0
**AI Integrations:** None

### mobile-api

**Description:** ActiveLog Mobile API Service

High-performance mobile-optimized API server with:
- Protocol Buffers for binary communication
- Offline-first sync protocol
- Push notification support
- Image optimization
- Battery-efficient sync strategies
**Dockerized:** ❌ No
**Files:** 9
**Dependencies:** 72
**API Endpoints:** 22
**AI Integrations:** None

**API Endpoints:**
- `/sync`
- `/sync/offline-queue`
- `/sync/offline-queue/{operation_id}`
- `/`
- `/sync/history`
- `/biometric/authenticate`
- `/metrics/mobile`
- `/sync/upload-delta/{file_id}`
- `/devices`
- `/logout`
- `/change-password`
- `/sync/resolve-conflicts`
- `/refresh`
- `/health`
- `/devices/{device_id}`
- `/login`
- `/me`
- `/sync/status`
- `/sync/conflicts`
- `/sync/delta/{file_id}`
- `/sync/batch`
- `/biometric/setup`

### memory-preservation

**Description:** Automatic Biography Generation System

This module provides comprehensive biography generation capabilities including
life event analysis, narrative construction, and multi-modal content integration
for creating rich, personalized autobiographical content.
**Dockerized:** ❌ No
**Files:** 6
**Dependencies:** 11
**API Endpoints:** 0
**AI Integrations:** None

### dmlog-marketplace

**Description:** DMLog Marketplace - Main Service
A comprehensive D&D content marketplace for adventures, art, audio, and digital assets
**Dockerized:** ❌ No
**Files:** 14
**Dependencies:** 24
**API Endpoints:** 29
**AI Integrations:** torch

**API Endpoints:**
- `/art/commissions`
- `/supplements/`
- `/`
- `/reviews/{product_id}/featured`
- `/maps/featured`
- `/adventures/`
- `/art/artists`
- `/settings/`
- `/maps/`
- `/royalties/creator/{creator_id}/report`
- `/dice/`
- `/dashboard`
- `/miniatures/{design_id}`
- `/screens/interactive`
- `/miniatures/{design_id}/preview`
- `/supplements/trending`
- `/voices/`
- `/settings/beginner`
- `/reviews/{product_id}/stats`
- `/adventures/featured`
- `/miniatures/design`
- `/dice/trending`
- `/audio/`
- `/screens/`
- `/voices/recommendations`
- `/adventures/{adventure_id}`
- `/reviews/{product_id}`
- `/audio/recommendations/{scenario}`
- `/royalties/creator/{creator_id}/summary`

### health-integration

**Description:** Medication Reminder System for ActiveLog Health Suite
Smart medication management with reminders, tracking, and adherence monitoring
**Dockerized:** ❌ No
**Files:** 7
**Dependencies:** 28
**API Endpoints:** 0
**AI Integrations:** None

### simulation

**Description:** ActiveLog Simulation Engine - Business Process Simulation

This module provides comprehensive business process simulation capabilities including:
- Workflow modeling and optimization
- Resource allocation simulation
- Bottleneck identification and analysis
- Process performance prediction
- Cost and time optimization
- Quality and compliance modeling
- Multi-scenario business process analysis
- Real-time process monitoring and adjustment
**Dockerized:** ❌ No
**Files:** 5
**Dependencies:** 22
**API Endpoints:** 0
**AI Integrations:** None

### manufacturing

**Description:** ActiveLog Manufacturing Suite - Predictive Maintenance Scheduling

AI-powered predictive maintenance system using IoT sensors, machine learning,
and operational data to optimize equipment maintenance schedules.
**Dockerized:** ❌ No
**Files:** 13
**Dependencies:** 55
**API Endpoints:** 0
**AI Integrations:** tensorflow, torch

### __pycache__

**Description:** 
**Dockerized:** ❌ No
**Files:** 0
**Dependencies:** 0
**API Endpoints:** 0
**AI Integrations:** None

### blockchain

**Description:** ActiveLog Blockchain Services
Comprehensive Web3 infrastructure for decentralized features
**Dockerized:** ❌ No
**Files:** 16
**Dependencies:** 44
**API Endpoints:** 0
**AI Integrations:** None

### ads

**Description:** Ad Service - Main orchestrator for the ActiveLog advertising system.
Integrates ad management, AdSense, affiliate links, and revenue tracking.
**Dockerized:** ❌ No
**Files:** 5
**Dependencies:** 18
**API Endpoints:** 0
**AI Integrations:** None

### quantum-reality

**Description:** Consensus Reality Verification System
Verify and establish consensus reality through distributed validation and proof systems
**Dockerized:** ❌ No
**Files:** 6
**Dependencies:** 17
**API Endpoints:** 0
**AI Integrations:** None

### collaboration

**Description:** ActiveLog Collaboration Service

Real-time collaboration platform with:
- Real-time collaborative annotations
- Comments and discussions on files  
- Version control for documents
- Shared workspaces
- Activity feeds and timelines
- Team permissions management
- Guest access with expiry
**Dockerized:** ❌ No
**Files:** 24
**Dependencies:** 52
**API Endpoints:** 4
**AI Integrations:** None

**API Endpoints:**
- `/metrics`
- `/health`
- `/dev/reset-db`
- `/`

### dmlog-converter

**Description:** Main system converter service - orchestrates all conversion functionality
**Dockerized:** ❌ No
**Files:** 12
**Dependencies:** 21
**API Endpoints:** 12
**AI Integrations:** None

**API Endpoints:**
- `/systems`
- `/projects/{project_id}`
- `/health`
- `/convert`
- `/projects/{project_id}/execute`
- `/stats`
- `/convert/challenge-rating`
- `/compatibility`
- `/projects`
- `/preview`
- `/convert/dc`
- `/projects/{project_id}/content`

### ml-pipeline

**Description:** Embedding Fine-tuning Example

This example demonstrates how to fine-tune sentence embeddings for improved
semantic search and similarity matching on user-specific data.
**Dockerized:** ✅ Yes
**Files:** 15
**Dependencies:** 74
**API Endpoints:** 22
**AI Integrations:** torch, transformers

**API Endpoints:**
- `/api/stats/overview`
- `/api/training/embeddings`
- `/api/models/rollback`
- `/api/jobs`
- `/api/config/classifier`
- `/api/ab-testing/start`
- `/api/models/{model_id}/promote`
- `/api/experiments`
- `/api/models/compare`
- `/api/training/classifier`
- `/api/jobs/{job_id}`
- `/api/maintenance/cleanup`
- `/health`
- `/api/experiments/{experiment_name}/runs`
- `/api/training/batch`
- `/api/config/embeddings`
- `/api/models/{model_id}`
- `/api/active-learning/iteration`
- `/api/config/active-learning`
- `/api/models`
- `/api/training/hyperparameter-optimization`
- `/api/models/{model_id}/lineage`

### p2p-sync

**Description:** Configuration settings for P2P sync service
**Dockerized:** ❌ No
**Files:** 2
**Dependencies:** 14
**API Endpoints:** 0
**AI Integrations:** None

### ai_orchestrator

**Description:** 
**Dockerized:** ✅ Yes
**Files:** 0
**Dependencies:** 0
**API Endpoints:** 0
**AI Integrations:** None

### dmlog-world

**Description:** Test script for the DM Log World Building Service
**Dockerized:** ❌ No
**Files:** 14
**Dependencies:** 37
**API Endpoints:** 18
**AI Integrations:** torch

**API Endpoints:**
- `/maps/dungeon`
- `/locations/describe`
- `/religion/pantheon/generate`
- `/maps/settlement`
- `/health`
- `/maps/world`
- `/calendar/{calendar_id}/events`
- `/weather/generate`
- `/calendar/{calendar_id}/advance`
- `/religion/deity/generate`
- `/weather/query`
- `/random/name`
- `/maps/region`
- `/religion/query`
- `/calendar/create`
- `/`
- `/calendar/query`
- `/weather/events/create`

### ai-orchestrator

**Description:** Test script for Whisper Plugin
Tests audio transcription, metadata extraction, and Elasticsearch storage
**Dockerized:** ❌ No
**Files:** 10
**Dependencies:** 39
**API Endpoints:** 20
**AI Integrations:** openai

**API Endpoints:**
- `/ollama/generate`
- `/ollama/models/pull`
- `/ai/analyze/image`
- `/`
- `/plugins`
- `/whisper/transcript/{file_hash}`
- `/ollama/models`
- `/whisper/transcribe`
- `/ollama/embeddings`
- `/ai/tags`
- `/ollama/models/{model_name}`
- `/analyze/file`
- `/batch/analyze`
- `/ai/analyze`
- `/ai/embeddings`
- `/health`
- `/ai/generate/image`
- `/plugins/stats`
- `/ollama/chat`
- `/whisper/search`

### smart-folders

**Description:** ActiveLog Smart Folders Service

Intelligent folder management with dynamic content organization:
- Dynamic folders based on rules and conditions
- AI-suggested folder structures and organization
- Virtual folders without moving physical files
- Folder templates for common use cases
- Inheritance rules for nested hierarchies
- Folder sharing with granular permissions
**Dockerized:** ❌ No
**Files:** 20
**Dependencies:** 66
**API Endpoints:** 39
**AI Integrations:** transformers

**API Endpoints:**
- `/virtual-folders/{folder_id}/files/{reference_id}`
- `/shares/cleanup`
- `/folders/{folder_id}/content`
- `/folders/{folder_id}/hierarchy`
- `/suggestions`
- `/virtual-folders`
- `/`
- `/folders/{folder_id}/permissions`
- `/folders/suggestions/{user_id}`
- `/shares/{share_id}`
- `/shares/{share_id}/access`
- `/templates/{template_id}`
- `/templates/{template_id}/preview`
- `/folders/{folder_id}/propagate`
- `/folders/{folder_id}/effective-settings`
- `/folders/apply-template`
- `/search/templates`
- `/virtual-folders/{folder_id}`
- `/folders/{folder_id}/share`
- `/health`
- `/stats`
- `/hierarchy/validate`
- `/templates/categories`
- `/folders/{folder_id}/permissions/{user_id}/{permission}`
- `/folders/{folder_id}/refresh`
- `/search/virtual-folders`
- `/metrics`
- `/folders/refresh/{folder_id}`
- `/templates`
- `/folders/{folder_id}/shares`
- `/folders`
- `/users/{user_id}/shared-folders`
- `/folders/{folder_id}`
- `/folders/{folder_id}/effective-rules`
- `/virtual-folders/{folder_id}/files`
- `/search/folders`
- `/folders/{parent_id}/children/{child_id}`
- `/virtual-folders/{folder_id}/content`
- `/templates/{template_id}/create`

### time-machine

**Description:** Parallel Timeline Comparisons for Time Machine
Advanced system for comparing different time periods, versions of events, and alternative timelines
**Dockerized:** ❌ No
**Files:** 4
**Dependencies:** 20
**API Endpoints:** 0
**AI Integrations:** None

### notifications

**Description:** ActiveLog Notification Service - Simplified Main Application
Port: 8006
**Dockerized:** ❌ No
**Files:** 18
**Dependencies:** 53
**API Endpoints:** 30
**AI Integrations:** None

**API Endpoints:**
- `/digest/send/{user_id}`
- `/api/v1/system/broadcast`
- `/preferences/{user_id}`
- `/`
- `/sms/history/{user_id}`
- `/api/v1/users/{user_id}/notifications`
- `/webhooks/endpoints/{endpoint_id}/test`
- `/api/v1/users/{user_id}/preferences`
- `/notifications/send`
- `/templates/{template_id}`
- `/notifications/webhook`
- `/digest/queue`
- `/webhooks/endpoints/{endpoint_id}`
- `/preferences/{user_id}/bulk`
- `/api/v1/notifications/{notification_id}/read`
- `/templates/{template_id}/render`
- `/health`
- `/stats`
- `/retry/failed`
- `/notifications/email`
- `/notifications/{notification_id}/status`
- `/notifications/sms`
- `/webhooks/endpoints`
- `/api/v1/notifications`
- `/sms/account-info`
- `/api/v1/stats`
- `/templates`
- `/system/configuration`
- `/webhooks/endpoints/{user_id}`
- `/sms/validate-phone`

### video-processor

**Description:** Simple run script for video processor service
**Dockerized:** ✅ Yes
**Files:** 13
**Dependencies:** 50
**API Endpoints:** 11
**AI Integrations:** anthropic, openai, transformers

**API Endpoints:**
- `/streaming/sessions/{session_id}`
- `/statistics`
- `/files/keyframes/{job_id}/{filename}`
- `/videos/upload`
- `/health`
- `/files/thumbnails/{job_id}/{filename}`
- `/search`
- `/jobs/{job_id}/results`
- `/videos/{job_id}/process`
- `/jobs/{job_id}/status`
- `/streaming/sessions`

### cache

**Description:** Redis Client for ActiveLog
Provides centralized Redis connection management and caching utilities
**Dockerized:** ❌ No
**Files:** 7
**Dependencies:** 25
**API Endpoints:** 0
**AI Integrations:** None

### file-watcher

**Description:** Core file watcher implementation using watchdog
**Dockerized:** ✅ Yes
**Files:** 7
**Dependencies:** 40
**API Endpoints:** 19
**AI Integrations:** None

**API Endpoints:**
- `/monitoring/system`
- `/config`
- `/monitoring/detailed`
- `/ignore/patterns`
- `/health`
- `/stats`
- `/import/stats`
- `/monitoring/reset-stats`
- `/monitoring/health-check`
- `/watch/remove`
- `/queue/flush`
- `/watch/add`
- `/queue/reconnect`
- `/rescan`
- `/metrics`
- `/ignore/remove`
- `/ignore/add`
- `/import/batch`
- `/watch/directories`

### predictive

**Description:** Predictive Analytics Engine

This module provides comprehensive predictive analytics and early warning systems
across multiple domains including relationships, health, devices, career, finance,
social dynamics, mental health, education, business, environment, and infrastructure.

Key Features:
- Relationship maintenance predictions and intervention timing
- Health issue early warning with biomarker analysis
- Device failure prediction using telemetry and usage patterns
- Career trajectory optimization with skill gap analysis
- Financial crisis prevention with risk modeling
- Social conflict early warning through sentiment analysis
- Mental health intervention timing with behavioral indicators
- Educational intervention points with learning analytics
- Business pivot indicators with market trend analysis
- Environmental hazard detection with sensor networks
- Infrastructure failure prediction with stress analysis
- Community health metrics with population analytics
**Dockerized:** ❌ No
**Files:** 1
**Dependencies:** 19
**API Endpoints:** 0
**AI Integrations:** None

### auth

**Description:** UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
**Dockerized:** ✅ Yes
**Files:** 6
**Dependencies:** 21
**API Endpoints:** 13
**AI Integrations:** None

**API Endpoints:**
- `/change-password`
- `/refresh`
- `/register`
- `/logout-all`
- `/health`
- `/login`
- `/users`
- `/me`
- `/admin-only`
- `/`
- `/users/{user_id}`
- `/logout`
- `/protected`

### gaming-platform

**Description:** Team Coordination Analytics Module for Gaming Platform
Advanced analysis of team coordination, synergy, and communication patterns
**Dockerized:** ❌ No
**Files:** 4
**Dependencies:** 22
**API Endpoints:** 0
**AI Integrations:** None

### analytics

**Description:** ActiveLog Analytics Service - Simplified Main Application
Port: 8005
**Dockerized:** ❌ No
**Files:** 19
**Dependencies:** 35
**API Endpoints:** 36
**AI Integrations:** None

**API Endpoints:**
- `/api/v1/tenants/{tenant_id}/summary`
- `/api/v1/users/{user_id}/summary`
- `/api/v1/dashboard/overview`
- `/metrics/top`
- `/api/v1/metrics/ai-operation`
- `/costs/track/file-processing`
- `/metrics/dashboard`
- `/costs/calculate/storage`
- `/costs/user/{user_id}`
- `/api/v1/dashboard/charts`
- `/usage/track/api-call`
- `/api/v1/reports/usage`
- `/api/v1/metrics/file-upload`
- `/reports/exports`
- `/api/v1/export/usage`
- `/system/database/cleanup`
- `/costs/tenant/{tenant_id}`
- `/reports/generate/performance`
- `/api/v1/metrics/api-call`
- `/reports/generate/storage`
- `/reports/export/{format}`
- `/reports/download/{filename}`
- `/health`
- `/api/v1/reports/cost`
- `/api/v1/dashboard/top-users`
- `/usage/track/file-upload`
- `/reports/cleanup`
- `/usage/global`
- `/system/database/stats`
- `/reports/generate/usage`
- `/system/configuration`
- `/costs/track/ai-operation`
- `/usage/tenant/{tenant_id}`
- `/api/v1/export/cost`
- `/usage/user/{user_id}`
- `/metrics/file-types`

### sync-engine

**Description:** Delta sync and chunked upload implementation
Provides efficient file synchronization using binary deltas and resumable uploads
**Dockerized:** ❌ No
**Files:** 8
**Dependencies:** 48
**API Endpoints:** 10
**AI Integrations:** None

**API Endpoints:**
- `/sync/rules/{rule_id}`
- `/sync/upload`
- `/health`
- `/sync/rules`
- `/sync/trigger`
- `/sync/status/{job_id}`
- `files`
- `/sync/workers/stats`
- `/`
- `/sync/queue/stats`

## Service Dependency Graph

- **sync-v2** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, gaming-platform, time-machine, collaboration
- **notification** has no internal dependencies
- **quantum-ready** depends on: simulation, time-machine
- **graphql** has no internal dependencies
- **activeledger** depends on: analytics
- **api-gateway** depends on: time-machine
- **dmlog-ai-dm** has no internal dependencies
- **dmlog-session** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, analytics, notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications
- **multiverse** depends on: time-machine
- **dmlog-templates** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, dmlog-characters
- **emotional-ai** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **marine-advanced** depends on: notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications
- **workflows** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, auth, time-machine
- **dmlog-core** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, time-machine, dmlog-characters, api-gateway, api_gateway, mobile-api
- **cognitive** has no internal dependencies
- **data-export** depends on: metadata, auth, time-machine, auth, notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications, auth, auth
- **file-sync** has no internal dependencies
- **universal-translator** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications
- **social-ai** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **predictive-ai** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **ai-tools** depends on: cache
- **creative-suite** depends on: notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications
- **dmlog-characters** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, memory-preservation, emotional-ai, dmlog-characters
- **education-ai** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, time-machine
- **ambient** depends on: predictive
- **backup** depends on: backup, backup, time-machine
- **document-ai** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications
- **video-pipeline** depends on: video-pipeline, video-processor, analytics, time-machine
- **data-manager** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, analytics
- **security-advanced** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, auth
- **batch-import** depends on: notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications, time-machine
- **biological** depends on: time-machine
- **dmlog-battle** has no internal dependencies
- **ar-layer** depends on: notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications
- **metadata** has no internal dependencies
- **dmlog-player** has no internal dependencies
- **api_gateway** has no internal dependencies
- **file_processor** has no internal dependencies
- **mobile-api** depends on: auth, notification, notifications, notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications, auth, auth, time-machine
- **memory-preservation** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **dmlog-marketplace** has no internal dependencies
- **health-integration** depends on: notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications
- **simulation** depends on: time-machine
- **manufacturing** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications, time-machine
- **__pycache__** has no internal dependencies
- **blockchain** depends on: blockchain, time-machine, blockchain
- **ads** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, ads
- **quantum-reality** has no internal dependencies
- **collaboration** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **dmlog-converter** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **ml-pipeline** depends on: time-machine
- **p2p-sync** has no internal dependencies
- **ai_orchestrator** has no internal dependencies
- **dmlog-world** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **ai-orchestrator** depends on: notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications, time-machine
- **smart-folders** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, auth, cache, time-machine
- **time-machine** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **notifications** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive
- **video-processor** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, time-machine
- **cache** depends on: cache, cache, metadata, cache, time-machine
- **file-watcher** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, file-watcher, time-machine
- **predictive** depends on: time-machine
- **auth** depends on: auth, auth, auth
- **gaming-platform** depends on: analytics
- **analytics** depends on: notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications
- **sync-engine** depends on: quantum-ready, dmlog-core, predictive-ai, creative-suite, memory-preservation, quantum-reality, predictive, notification, dmlog-session, emotional-ai, education-ai, biological, memory-preservation, health-integration, simulation, collaboration, notifications, time-machine

## Security Issues

- **HIGH** exposed_secret in `generate_audit_report.py:159`
- **HIGH** exposed_secret in `generate_audit_report.py:159`
- **HIGH** exposed_secret in `generate_audit_report.py:159`
- **HIGH** exposed_secret in `generate_audit_report.py:159`
- **HIGH** exposed_secret in `generate_audit_report.py:159`
- **HIGH** exposed_secret in `generate_audit_report.py:159`
- **HIGH** hardcoded_key in `services/main.py:17`
- **MEDIUM** sql_injection in `services/main.py:61`
- **MEDIUM** weak_crypto in `services/sync-v2/protocols/sync_protocol.py:64`
- **MEDIUM** dangerous_eval in `services/sync-v2/strategies/bandwidth_aware.py:151`
- **MEDIUM** dangerous_eval in `services/sync-v2/strategies/bandwidth_aware.py:162`
- **MEDIUM** dangerous_eval in `services/sync-v2/strategies/bandwidth_aware.py:173`
- **MEDIUM** dangerous_eval in `services/sync-v2/strategies/bandwidth_aware.py:204`
- **MEDIUM** dangerous_eval in `services/sync-v2/strategies/bandwidth_aware.py:233`
- **MEDIUM** weak_crypto in `services/sync-v2/core/sync_engine.py:755`
- **MEDIUM** weak_crypto in `services/dmlog-ai-dm/utils/lore_consistency_checker.py:126`
- **MEDIUM** weak_crypto in `services/emotional-ai/mood/mood_detector.py:698`
- **MEDIUM** weak_crypto in `services/emotional-ai/journey/emotional_journey_mapper.py:253`
- **MEDIUM** weak_crypto in `services/emotional-ai/journey/emotional_journey_mapper.py:321`
- **MEDIUM** weak_crypto in `services/emotional-ai/journey/emotional_journey_mapper.py:465`
- **MEDIUM** weak_crypto in `services/emotional-ai/journey/emotional_journey_mapper.py:696`
- **MEDIUM** weak_crypto in `services/emotional-ai/journey/emotional_journey_mapper.py:723`
- **MEDIUM** weak_crypto in `services/emotional-ai/journey/emotional_journey_mapper.py:745`
- **MEDIUM** weak_crypto in `services/emotional-ai/stress/stress_detector.py:354`
- **MEDIUM** weak_crypto in `services/emotional-ai/stress/stress_detector.py:476`
- **MEDIUM** weak_crypto in `services/emotional-ai/stress/stress_detector.py:796`
- **MEDIUM** weak_crypto in `services/emotional-ai/stress/stress_detector.py:890`
- **HIGH** hardcoded_key in `services/workflows/src/integrations/integration_manager.py:38`
- **MEDIUM** weak_crypto in `services/universal-translator/speech_translation.py:376`
- **MEDIUM** weak_crypto in `services/predictive-ai/caching/smart_precaching.py:305`
- **MEDIUM** weak_crypto in `services/predictive-ai/caching/smart_precaching.py:336`
- **MEDIUM** weak_crypto in `services/predictive-ai/caching/smart_precaching.py:354`
- **MEDIUM** weak_crypto in `services/predictive-ai/caching/smart_precaching.py:388`
- **MEDIUM** weak_crypto in `services/predictive-ai/caching/smart_precaching.py:434`
- **MEDIUM** weak_crypto in `services/predictive-ai/caching/smart_precaching.py:456`
- **MEDIUM** weak_crypto in `services/predictive-ai/analytics/relationship_mapping.py:236`
- **MEDIUM** weak_crypto in `services/predictive-ai/analytics/relationship_mapping.py:561`
- **MEDIUM** dangerous_eval in `services/ai-tools/services/training/lora_trainer.py:473`
- **MEDIUM** dangerous_eval in `services/ai-tools/services/compute/optimizer.py:212`
- **MEDIUM** weak_crypto in `services/ai-tools/services/video/video_generator.py:733`
- **MEDIUM** weak_crypto in `services/ai-tools/services/marketplace/model_marketplace.py:550`
- **MEDIUM** weak_crypto in `services/dmlog-characters/services/portrait_service.py:630`
- **MEDIUM** weak_crypto in `services/document-ai/processors/table_extractor.py:553`
- **MEDIUM** dangerous_eval in `services/video-pipeline/src/processors/analysis.py:832`
- **MEDIUM** dangerous_eval in `services/video-pipeline/src/processors/transcoding.py:475`
- **MEDIUM** dangerous_eval in `services/video-pipeline/src/processors/transcoding.py:558`
- **MEDIUM** dangerous_eval in `services/video-pipeline/src/processors/transcoding.py:608`
- **MEDIUM** weak_crypto in `services/data-manager/api/integration.py:308`
- **MEDIUM** weak_crypto in `services/ar-layer/spatial/spatial_anchoring.py:514`
- **MEDIUM** weak_crypto in `services/ar-layer/spatial/spatial_anchoring.py:519`
- **MEDIUM** weak_crypto in `services/ar-layer/overlay/contextual_overlay.py:433`
- **MEDIUM** weak_crypto in `services/ar-layer/overlay/contextual_overlay.py:753`
- **MEDIUM** weak_crypto in `services/ar-layer/recognition/object_recognition.py:215`
- **MEDIUM** weak_crypto in `services/ar-layer/recognition/object_recognition.py:717`
- **MEDIUM** weak_crypto in `services/ar-layer/recognition/object_recognition.py:721`
- **MEDIUM** weak_crypto in `services/ar-layer/biometrics/facial_recognition.py:583`
- **MEDIUM** weak_crypto in `services/ar-layer/biometrics/facial_recognition.py:669`
- **MEDIUM** sql_injection in `services/metadata/embeddings.py:140`
- **MEDIUM** sql_injection in `services/metadata/embeddings.py:154`
- **HIGH** hardcoded_key in `services/metadata/database.py:13`
- **MEDIUM** sql_injection in `services/metadata/database.py:161`
- **MEDIUM** sql_injection in `services/metadata/database.py:173`
- **MEDIUM** sql_injection in `services/metadata/database.py:219`
- **MEDIUM** sql_injection in `services/metadata/database.py:272`
- **MEDIUM** sql_injection in `services/metadata/database.py:284`
- **MEDIUM** sql_injection in `services/metadata/relationships.py:163`
- **MEDIUM** weak_crypto in `services/mobile-api/services/media_optimization.py:398`
- **MEDIUM** dangerous_eval in `services/mobile-api/src/services/SyncService.ts:170`
- **HIGH** hardcoded_key in `services/health-integration/nutrition/nutrition_logging.py:1081`
- **HIGH** exposed_secret in `services/manufacturing/suppliers/reputation_tracker.py:1296`
- **HIGH** exposed_secret in `services/manufacturing/compliance/compliance_automation.py:1387`
- **HIGH** hardcoded_key in `services/blockchain/config/blockchain_config.py:25`
- **HIGH** hardcoded_key in `services/blockchain/config/blockchain_config.py:26`
- **HIGH** hardcoded_key in `services/ads/ad_service.py:56`
- **HIGH** hardcoded_key in `services/ads/integrations/adsense_integration.py:751`
- **MEDIUM** weak_crypto in `services/ads/affiliate/affiliate_manager.py:192`
- **MEDIUM** weak_crypto in `services/quantum-reality/spatial_data_persistence.py:813`
- **MEDIUM** dangerous_eval in `services/ml-pipeline/src/training/classifier_trainer.py:535`
- **MEDIUM** dangerous_eval in `services/ml-pipeline/src/training/classifier_trainer.py:668`
- **HIGH** hardcoded_key in `services/ai-orchestrator/test_openai_plugin.py:39`
- **HIGH** hardcoded_key in `services/ai-orchestrator/test_openai_plugin.py:206`
- **MEDIUM** weak_crypto in `services/ai-orchestrator/plugins/ollama_plugin.py:136`
- **MEDIUM** weak_crypto in `services/ai-orchestrator/plugins/whisper_plugin.py:266`
- **MEDIUM** weak_crypto in `services/smart-folders/src/virtual/virtual_folder_manager.py:42`
- **MEDIUM** dangerous_eval in `services/video-processor/processors/subtitle_processor.py:158`
- **MEDIUM** dangerous_eval in `services/video-processor/processors/subtitle_processor.py:209`
- **MEDIUM** dangerous_eval in `services/video-processor/processors/thumbnail_generator.py:282`
- **MEDIUM** dangerous_eval in `services/video-processor/processors/thumbnail_generator.py:337`
- **MEDIUM** dangerous_eval in `services/video-processor/processors/thumbnail_generator.py:391`
- **MEDIUM** dangerous_eval in `services/video-processor/processors/scene_detector.py:403`
- **MEDIUM** dangerous_eval in `services/video-processor/processors/scene_detector.py:645`
- **MEDIUM** dangerous_eval in `services/video-processor/src/thumbnailGenerator.js:292`
- **MEDIUM** weak_crypto in `services/cache/redis_client.py:438`
- **MEDIUM** weak_crypto in `services/cache/redis_client.py:470`
- **MEDIUM** weak_crypto in `services/cache/metadata_cache.py:475`
- **MEDIUM** dangerous_eval in `services/cache/distributed_locks.py:200`
- **MEDIUM** dangerous_eval in `services/cache/distributed_locks.py:243`
- **MEDIUM** dangerous_eval in `services/cache/distributed_locks.py:289`
- **MEDIUM** weak_crypto in `services/cache/api_cache.py:217`
- **HIGH** hardcoded_key in `services/auth/auth_models.py:12`
- **MEDIUM** weak_crypto in `services/gaming-platform/team/coordination_analytics.py:321`
- **MEDIUM** weak_crypto in `services/gaming-platform/team/coordination_analytics.py:515`
- **MEDIUM** weak_crypto in `services/gaming-platform/team/coordination_analytics.py:698`
- **MEDIUM** weak_crypto in `services/gaming-platform/team/coordination_analytics.py:793`
- **MEDIUM** weak_crypto in `services/gaming-platform/replay/replay_analyzer.py:300`
- **MEDIUM** weak_crypto in `services/gaming-platform/replay/replay_analyzer.py:331`
- **MEDIUM** weak_crypto in `services/gaming-platform/replay/replay_analyzer.py:669`
- **MEDIUM** weak_crypto in `services/gaming-platform/replay/replay_analyzer.py:695`
- **MEDIUM** weak_crypto in `services/gaming-platform/replay/replay_analyzer.py:736`
- **MEDIUM** weak_crypto in `services/gaming-platform/replay/replay_analyzer.py:759`
- **MEDIUM** dangerous_eval in `services/sync-engine/delta_sync.py:481`
- **MEDIUM** weak_crypto in `optimizations/caching/cache_headers.py:205`
- **MEDIUM** weak_crypto in `optimizations/cdn/static_serving.py:180`
- **MEDIUM** weak_crypto in `optimizations/cdn/static_serving.py:481`
- **HIGH** hardcoded_key in `optimizations/benchmarks/load_testing.py:47`
- **HIGH** hardcoded_key in `optimizations/benchmarks/load_testing.py:283`
- **HIGH** hardcoded_key in `migrations/rollback/rollback_manager.py:195`
- **HIGH** hardcoded_key in `migrations/rollback/rollback_manager.py:372`
- **MEDIUM** dangerous_eval in `migrations/rollback/rollback_manager.py:173`
- **MEDIUM** dangerous_eval in `migrations/rollback/rollback_manager.py:203`
- **MEDIUM** dangerous_eval in `migrations/rollback/rollback_manager.py:350`
- **MEDIUM** dangerous_eval in `migrations/rollback/rollback_manager.py:377`
- **MEDIUM** weak_crypto in `migrations/anonymization/data_anonymizer.py:248`
- **MEDIUM** weak_crypto in `migrations/anonymization/data_anonymizer.py:250`
- **HIGH** exposed_secret in `dev-tools/visualization/dependency_visualizer.py:415`
- **HIGH** exposed_secret in `dev-tools/templates/generate_service.py:1021`
- **MEDIUM** dangerous_eval in `security-audit/tests/test_xss_prevention.py:91`
- **MEDIUM** dangerous_eval in `security-audit/tests/test_xss_prevention.py:212`
- **HIGH** hardcoded_key in `security-audit/tests/test_sql_injection.py:549`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:65`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:75`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:152`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:163`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:172`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:182`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:248`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:261`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:429`
- **HIGH** exposed_secret in `modules/legal/matters/tests/test_matter_management.py:485`
- **MEDIUM** weak_crypto in `modules/legal/contracts/src/contract_analyzer.py:666`
- **HIGH** hardcoded_key in `modules/legal/redaction/src/redaction_tools.py:52`
- **MEDIUM** weak_crypto in `modules/legal/custody/src/chain_of_custody.py:147`
- **MEDIUM** weak_crypto in `modules/legal/custody/src/chain_of_custody.py:175`
- **HIGH** hardcoded_key in `modules/healthcare/hl7-fhir/tests/test_fhir.py:16`
- **MEDIUM** sql_injection in `security/audit/audit-logger.py:584`
- **MEDIUM** sql_injection in `security/secrets/rotation-service.py:293`
- **MEDIUM** dangerous_eval in `security/api-keys/api-key-service.py:333`
- **MEDIUM** sql_injection in `security/auth/two-factor-auth.py:213`
- **MEDIUM** sql_injection in `security/auth/two-factor-auth.py:369`
- **MEDIUM** sql_injection in `security/auth/two-factor-auth.py:432`
- **MEDIUM** sql_injection in `security/auth/two-factor-auth.py:465`
- **MEDIUM** dangerous_eval in `infrastructure/terraform/modules/lambda/lambda_code/virus_scanner.py:266`
- **MEDIUM** dangerous_eval in `infrastructure/terraform/modules/lambda/lambda_code/virus_scanner.py:268`
- **MEDIUM** weak_crypto in `infrastructure/terraform/modules/lambda/lambda_code/virus_scanner.py:212`
- **MEDIUM** weak_crypto in `infrastructure/terraform/modules/lambda/lambda_code/virus_scanner.py:213`
- **MEDIUM** weak_crypto in `edge/offline-sync/sync-queue.py:284`
- **MEDIUM** dangerous_eval in `edge/device-discovery/discovery-agent.py:501`
- **HIGH** exposed_secret in `edge/management-dashboard/dashboard.py:530`
- **HIGH** exposed_secret in `edge/iot-integration/lorawan-gateway.py:483`
- **MEDIUM** dangerous_eval in `edge/jetson-nano/jetson-ai-agent.py:117`
- **MEDIUM** dangerous_eval in `edge/jetson-nano/jetson-ai-agent.py:125`
- **MEDIUM** weak_crypto in `sdk/python/activelog_plugin_sdk/decorators.py:130`
- **MEDIUM** dangerous_eval in `sdk/runtime/plugin-executor.py:336`
- **MEDIUM** weak_crypto in `production/caching/redis_cache_manager.py:476`
- **MEDIUM** weak_crypto in `production/configs/rate-limiting/rate_limiter.py:294`
- **MEDIUM** dangerous_eval in `src/plugins/cache.ts:224`
- **MEDIUM** dangerous_eval in `src/plugins/rateLimit.ts:136`
- **MEDIUM** dangerous_eval in `src/plugins/rateLimit.ts:198`
- **MEDIUM** weak_crypto in `tests/docker/mock_server.py:47`
- **MEDIUM** weak_crypto in `tests/docker/mock_server.py:204`
- **HIGH** hardcoded_key in `tests/unit/test_api_gateway.py:178`
- **HIGH** hardcoded_key in `tests/unit/test_api_gateway.py:231`
- **HIGH** exposed_secret in `tests/unit/test_api_gateway.py:413`
- **HIGH** exposed_secret in `tests/unit/test_ai_orchestrator.py:121`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:29`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:40`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:50`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:51`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:61`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:223`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:237`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:246`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:256`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:317`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:442`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:443`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:488`
- **HIGH** hardcoded_key in `tests/unit/test_auth_service.py:515`
- **MEDIUM** weak_crypto in `tests/mocks/s3_mock.py:97`
- **MEDIUM** weak_crypto in `tests/mocks/s3_mock.py:247`

## TODO/FIXME Items

- **TODO** `generate_audit_report.py:130` - def find_todos_and_fixmes(self) -> List[Dict[str, str]]:
- **TODO** `generate_audit_report.py:131` - """Find all TODO and FIXME comments in code"""
- **TODO** `generate_audit_report.py:132` - todos = []
- **TODO** `generate_audit_report.py:140` - if re.search(r'(TODO|FIXME|HACK|BUG)', line, re.IGNORECASE):
- **TODO** `generate_audit_report.py:141` - todos.append({
- **TODO** `generate_audit_report.py:145` - 'type': re.search(r'(TODO|FIXME|HACK|BUG)', line, re.IGNORECASE).group(1).upper()
- **TODO** `generate_audit_report.py:150` - return todos
- **TODO** `generate_audit_report.py:245` - - **TODO/FIXME Items:** {len(data.get('todos_fixmes', []))}
- **TODO** `generate_audit_report.py:286` - if data.get('todos_fixmes'):
- **TODO** `generate_audit_report.py:287` - md += "\n## TODO/FIXME Items\n\n"
- **TODO** `generate_audit_report.py:288` - for todo in data.get('todos_fixmes', []):
- **TODO** `generate_audit_report.py:289` - md += f"- **{todo['type']}** `{todo['file']}:{todo['line']}` - {todo['content']}\n"
- **TODO** `generate_audit_report.py:306` - print("Finding TODO/FIXME comments...")
- **TODO** `generate_audit_report.py:307` - todos_fixmes = self.find_todos_and_fixmes()
- **TODO** `generate_audit_report.py:322` - 'todos_fixmes': todos_fixmes,
- **TODO** `generate_audit_report.py:330` - 'total_todos': len(todos_fixmes),
- **BUG** `services/sync-v2/strategies/bandwidth_aware.py:108` - self.logger.debug(f"Network metrics: {metrics.bandwidth_down:.1f}Mbps down, "
- **BUG** `services/sync-v2/core/sync_engine.py:554` - self.logger.debug(f"Sync already in progress for item: {item.item_id}")
- **BUG** `services/sync-v2/tests/test_sync_engine.py:388` - "log_level": "DEBUG"
- **BUG** `services/quantum-ready/random/quantum_rng.py:171` - logger.debug(f"Refilled pool {pool.pool_id} with {len(result.random_bits)} bits")
- **BUG** `services/graphql/src/schema/plugin.ts:538` - DEBUG
- **BUG** `services/activeledger/config/settings.py:180` - debug: bool = Field(default=False)
- **BUG** `services/activeledger/services/enterprise/billing_manager.py:624` - logger.debug(
- **BUG** `services/dmlog-session/config.py:16` - DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
- **BUG** `services/dmlog-session/services/notes_service.py:466` - logger.debug(f"Note '{note.title}' linked to {len(linked_segments)} segments")
- **BUG** `services/dmlog-templates/config.py:12` - "debug": os.getenv("DEBUG", "false").lower() == "true",
- **BUG** `services/emotional-ai/stress/stress_detector.py:395` - logger.debug(f"Added stress indicator: {indicator_type} = {value}")
- **BUG** `services/workflows/main.py:247` - if settings.DEBUG:
- **BUG** `services/workflows/main.py:309` - # Development endpoints (only in debug mode)
- **BUG** `services/workflows/main.py:310` - if settings.DEBUG:
- **BUG** `services/workflows/main.py:367` - reload=settings.DEBUG,
- **BUG** `services/workflows/main.py:369` - log_level="debug" if settings.DEBUG else "info",
- **BUG** `services/workflows/src/webhooks/webhook_manager.py:656` - logger.debug("Webhook cleanup completed")
- **BUG** `services/workflows/src/workflow/actions.py:700` - logger.debug(f"Registered action type: {action_type}")
- **BUG** `services/workflows/src/workflow/context.py:47` - logger.debug(f"Set variable '{name}' = {value if not is_sensitive else '[REDACTED]'}")
- **BUG** `services/workflows/src/workflow/triggers.py:357` - logger.debug(f"Registered trigger type: {trigger_type}")
- **BUG** `services/workflows/src/core/config.py:15` - DEBUG: bool = Field(default=False, description="Debug mode")
- **BUG** `services/workflows/src/core/config.py:120` - "level": "DEBUG" if settings.DEBUG else "INFO",
- **BUG** `services/workflows/src/core/config.py:131` - "level": "DEBUG" if settings.DEBUG else "INFO",
- **BUG** `services/workflows/src/core/database.py:29` - echo=settings.DEBUG
- **BUG** `services/dmlog-core/config.py:21` - DEBUG: bool = False
- **BUG** `services/dmlog-core/main.py:125` - logger.info(f"Debug mode: {settings.DEBUG}")
- **BUG** `services/dmlog-core/main.py:141` - debug=settings.DEBUG,
- **TODO** `services/dmlog-core/services/combat_service.py:555` - # TODO: Add ability modifier based on save_attribute
- **BUG** `services/dmlog-core/services/encounter_service.py:183` - {"name": "Bugbear", "hp": 27, "ac": 16, "xp": 200, "type": "humanoid"},
- **BUG** `services/data-export/main.py:242` - reload=settings.DEBUG,
- **BUG** `services/data-export/main.py:243` - log_level="info" if not settings.DEBUG else "debug",
- **BUG** `services/data-export/main.py:244` - workers=1 if settings.DEBUG else settings.WORKERS
- **BUG** `services/data-export/src/utils/progress_tracker.py:85` - logger.debug(f"Progress updated for job {self.job_id}: {current}/{self.total} ({snapshot.percentage:.1f}%)")
- **BUG** `services/data-export/src/utils/bulk_exporter.py:267` - logger.debug(f"Worker {worker_name} waiting: {reason}")
- **TODO** `services/data-export/src/core/export_manager.py:325` - # TODO: Implement notification service integration
- **BUG** `services/data-export/src/core/config.py:99` - debug: bool = Field(default=False)
- **BUG** `services/data-export/src/core/config.py:130` - valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
- **TODO** `services/universal-translator/code_language_translation.py:528` - rust_code += "    // TODO: Implement function body\n"
- **TODO** `services/universal-translator/code_language_translation.py:534` - return f"// TODO: Translate {element.element_type} {element.name}"
- **TODO** `services/universal-translator/code_language_translation.py:545` - rust_code += "    // TODO: Add fields\n"
- **TODO** `services/universal-translator/code_language_translation.py:553` - rust_code += "        // TODO: Implement method\n"
- **TODO** `services/universal-translator/code_language_translation.py:561` - return f"// TODO: Translate {element.element_type} {element.name}"
- **TODO** `services/universal-translator/code_language_translation.py:571` - return f"let {element.name} = /* TODO: implement value */;"
- **TODO** `services/universal-translator/code_language_translation.py:573` - return f"// TODO: Translate variable {element.name}"
- **TODO** `services/universal-translator/code_language_translation.py:802` - if "TODO" in element:
- **TODO** `services/universal-translator/code_language_translation.py:803` - warnings.append("Contains TODO items requiring manual implementation")
- **HACK** `services/social-ai/introductions/introduction_facilitator.py:748` - bio="Marketing director with expertise in growth hacking and data analytics",
- **HACK** `services/social-ai/introductions/introduction_facilitator.py:749` - interests=["data analytics", "growth hacking", "photography", "travel"],
- **BUG** `services/ai-tools/config/settings.py:194` - debug: bool = Field(default=False)
- **BUG** `services/ai-tools/services/compute/optimizer.py:170` - logger.debug(f"GPU detection failed: {str(e)}")
- **BUG** `services/ai-tools/services/compute/optimizer.py:203` - logger.debug(f"nvidia-smi fallback failed: {str(e2)}")
- **BUG** `services/ai-tools/services/compute/optimizer.py:742` - """Force selection of a specific provider (for testing/debugging)"""
- **BUG** `services/ai-tools/models/ai_operations.py:22` - echo=settings.debug
- **BUG** `services/dmlog-characters/config.py:15` - DEBUG: bool = False
- **BUG** `services/dmlog-characters/services/memory_service.py:605` - logger.debug(f"Reinforced memory {memory.id}, new strength: {memory.current_strength}")
- **BUG** `services/ambient/predictive_actions.py:470` - logger.debug(f"Cleaned up expired preparation: {key}")
- **BUG** `services/ambient/predictive_actions.py:610` - logger.debug("Updated prediction models with new data")
- **BUG** `services/ambient/environmental_adapter.py:569` - logger.debug(f"Setting {capability.value} to {value}")
- **BUG** `services/ambient/environmental_adapter.py:574` - logger.debug(f"Gradually setting {capability.value} to {target_value}")
- **BUG** `services/ambient/context_switcher.py:632` - logger.debug(f"Environmental adjustment: {setting} = {value}")
- **BUG** `services/ambient/context_switcher.py:637` - logger.debug(f"Configuring notifications: {notification_config}")
- **BUG** `services/ambient/context_switcher.py:642` - logger.debug(f"Configuring audio: {audio_config}")
- **BUG** `services/ambient/context_switcher.py:648` - logger.debug(f"Executing auto action: {action}")
- **BUG** `services/ambient/context_switcher.py:653` - logger.debug(f"Preferred apps: {preferred}, Blocked apps: {blocked}")
- **BUG** `services/backup/main.py:638` - reload=settings.DEBUG,
- **BUG** `services/backup/services/verification.py:209` - logger.debug(f"Verification passed: {file_path}")
- **BUG** `services/backup/recovery/recovery_service.py:395` - logger.debug(f"File recovered: {file_path}")
- **BUG** `services/backup/backup_engines/rsync_engine.py:197` - logger.debug(f"Built file list with {len(files)} entries for {root_path}")
- **BUG** `services/backup/backup_engines/rsync_engine.py:230` - logger.debug(f"New file: {rel_path}")
- **BUG** `services/backup/backup_engines/rsync_engine.py:237` - logger.debug(f"Size changed: {rel_path} ({dest_info.size} -> {source_info.size})")
- **BUG** `services/backup/backup_engines/rsync_engine.py:240` - logger.debug(f"Timestamp changed: {rel_path}")
- **BUG** `services/backup/backup_engines/rsync_engine.py:252` - logger.debug(f"Checksum changed: {rel_path}")
- **BUG** `services/backup/backup_engines/rsync_engine.py:267` - logger.debug(f"File to delete: {rel_path}")
- **HACK** `services/backup/backup_engines/rsync_engine.py:272` - """Get base path from file dictionary (hack for now)"""
- **HACK** `services/backup/backup_engines/rsync_engine.py:273` - # This is a bit of a hack - in a real implementation,
- **BUG** `services/backup/backup_engines/rsync_engine.py:303` - logger.debug(f"Transferred: {rel_path} ({bytes_copied} bytes)")
- **BUG** `services/backup/backup_engines/rsync_engine.py:362` - logger.debug(f"Deleted file: {rel_path}")
- **BUG** `services/backup/backup_engines/rsync_engine.py:367` - logger.debug(f"Deleted empty directory: {rel_path}")
- **BUG** `services/backup/backup_engines/rsync_engine.py:370` - logger.debug(f"Skipping non-empty directory: {rel_path}")
- **BUG** `services/backup/crypto/encryption.py:345` - logger.debug(f"File encrypted: {input_file} -> {output_file}")
- **BUG** `services/backup/crypto/encryption.py:416` - logger.debug(f"File decrypted: {input_file} -> {output_file}")
- **BUG** `services/backup/core/config.py:24` - DEBUG: bool = False
- **BUG** `services/backup/core/logging.py:48` - file_handler.setLevel(logging.DEBUG)
- **BUG** `services/backup/destinations/s3_destination.py:168` - logger.debug(f"Uploaded {local_path} to s3://{self.bucket_name}/{s3_key}")
- **BUG** `services/backup/destinations/s3_destination.py:206` - logger.debug(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
- **BUG** `services/backup/destinations/s3_destination.py:312` - logger.debug(f"Deleted s3://{self.bucket_name}/{s3_key}")
- **BUG** `services/backup/destinations/local_destination.py:118` - logger.debug(f"Copied {local_path} to {dest_path}")
- **BUG** `services/backup/destinations/local_destination.py:145` - logger.debug(f"Downloaded {source_path} to {local_path}")
- **BUG** `services/backup/destinations/local_destination.py:226` - logger.debug(f"Deleted file: {target_path}")
- **BUG** `services/backup/destinations/local_destination.py:231` - logger.debug(f"Deleted directory: {target_path}")
- **BUG** `services/document-ai/run.py:14` - reload=settings.debug,
- **BUG** `services/document-ai/main.py:761` - reload=settings.debug,
- **BUG** `services/document-ai/core/config.py:73` - debug: bool = Field(default=False)
- **BUG** `services/document-ai/core/config.py:115` - valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
- **BUG** `services/document-ai/core/logging.py:48` - file_handler.setLevel(logging.DEBUG)
- **BUG** `services/video-pipeline/config/settings.py:15` - debug: bool = False
- **BUG** `services/video-pipeline/src/services/message_queue.py:293` - logger.debug("Message published",
- **BUG** `services/video-pipeline/src/services/message_queue.py:324` - logger.debug("Message processed",
- **BUG** `services/video-pipeline/src/core/database.py:23` - echo=settings.debug,
- **BUG** `services/data-manager/api/integration.py:175` - self.logger.debug(f"Webhook payload: {webhook_payload}")
- **BUG** `services/data-manager/api/integration.py:176` - self.logger.debug(f"Webhook signature: {signature}")
- **BUG** `services/data-manager/ai/intelligent_classifier.py:145` - {'pattern': r'\[.*\]\s+(ERROR|WARN|INFO|DEBUG)', 'type': 'application_log', 'confidence': 0.8},
- **BUG** `services/data-manager/ai/intelligent_classifier.py:326` - 'programming': ['code', 'function', 'variable', 'algorithm', 'debug'],
- **BUG** `services/data-manager/ai/intelligent_classifier.py:793` - 'log': (['log', 'trace', 'debug'], 'text', 'log')
- **BUG** `services/data-manager/core/data_manager.py:253` - log_indicators = ['ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE']
- **BUG** `services/data-manager/core/data_manager.py:483` - logger.debug(f"Submitted task {task.task_id} with priority {priority.name}")
- **BUG** `services/data-manager/core/data_manager.py:553` - logger.debug(f"Task {task.task_id} status: {task.status.value}")
- **BUG** `services/data-manager/core/data_manager.py:871` - logger.debug("Generating background insights...")
- **BUG** `services/data-manager/core/data_manager.py:882` - logger.debug("Monitoring data quality...")
- **BUG** `services/security-advanced/secure_enclaves.py:54` - debug_enabled: bool
- **BUG** `services/security-advanced/secure_enclaves.py:212` - "debug": enclave["config"].debug_enabled,
- **BUG** `services/security-advanced/secure_enclaves.py:518` - debug_enabled=False,
- **BUG** `services/batch-import/main.py:175` - reload=settings.DEBUG,
- **BUG** `services/batch-import/services/minio_service.py:76` - logger.debug(f"Bucket exists: {self.bucket_name}")
- **BUG** `services/batch-import/services/minio_service.py:300` - logger.debug(f"Uploaded thumbnail: {thumb_object_name}")
- **BUG** `services/batch-import/services/import_monitor.py:147` - logger.debug(f"Skipping unsupported file format: {path}")
- **BUG** `services/batch-import/services/import_monitor.py:177` - logger.debug(f"Added file event: {event_type} - {path}")
- **BUG** `services/batch-import/services/import_monitor.py:233` - logger.debug("No stable files ready for processing")
- **BUG** `services/batch-import/services/import_monitor.py:303` - logger.debug(f"Cannot access file {path}: {e}")
- **BUG** `services/batch-import/services/thumbnail_generator.py:102` - logger.debug("Generated image thumbnail",
- **BUG** `services/batch-import/services/thumbnail_generator.py:158` - logger.debug("Generated video thumbnail",
- **BUG** `services/batch-import/services/thumbnail_generator.py:192` - logger.debug("Cleaned up thumbnail", path=thumb_path)
- **BUG** `services/batch-import/services/batch_processor.py:247` - logger.debug(f"Successfully processed: {path.name}")
- **BUG** `services/batch-import/services/batch_processor.py:337` - logger.debug(f"Could not extract image metadata: {e}")
- **BUG** `services/batch-import/services/batch_processor.py:353` - logger.debug(f"Could not extract video metadata: {e}")
- **BUG** `services/batch-import/services/batch_processor.py:384` - logger.debug(f"Could not extract audio metadata: {e}")
- **BUG** `services/batch-import/services/batch_processor.py:411` - logger.debug(f"Could not extract document metadata: {e}")
- **BUG** `services/batch-import/services/report_service.py:382` - logger.debug(f"Deleted old report: {report_file.name}")
- **BUG** `services/batch-import/services/minio_client.py:70` - logger.debug("MinIO bucket already exists", bucket=self.bucket_name)
- **BUG** `services/batch-import/services/minio_client.py:120` - logger.debug("File uploaded to MinIO",
- **BUG** `services/batch-import/services/minio_client.py:215` - logger.debug("File downloaded from MinIO",
- **BUG** `services/batch-import/services/minio_client.py:250` - logger.debug("File deleted from MinIO",
- **BUG** `services/batch-import/core/logging_config.py:48` - file_handler.setLevel(logging.DEBUG)
- **BUG** `services/batch-import/core/logging_config.py:58` - logging.getLogger("batch_import").setLevel(logging.DEBUG)
- **BUG** `services/batch-import/core/config.py:16` - DEBUG: bool = False
- **BUG** `services/dmlog-battle/services/visualization_service.py:217` - """Render visualization as ASCII art for debugging."""
- **TODO** `services/ar-layer/overlay/contextual_overlay.py:529` - elif any(word in tags_and_content for word in ['task', 'todo', 'reminder', 'deadline']):
- **BUG** `services/mobile-api/main.py:108` - docs_url="/docs" if settings.DEBUG else None,
- **BUG** `services/mobile-api/main.py:109` - redoc_url="/redoc" if settings.DEBUG else None
- **BUG** `services/mobile-api/main.py:319` - reload=settings.DEBUG,
- **BUG** `services/mobile-api/main.py:320` - log_level="info" if settings.DEBUG else "warning",
- **BUG** `services/mobile-api/main.py:321` - access_log=settings.DEBUG,
- **BUG** `services/mobile-api/services/push_notifications.py:148` - use_sandbox=settings.DEBUG
- **TODO** `services/mobile-api/services/push_notifications.py:752` - # TODO: Implement true batch sending for platforms that support it
- **BUG** `services/mobile-api/core/config.py:16` - DEBUG: bool = False
- **BUG** `services/mobile-api/src/utils/logger.ts:42` - debug(message: string, data?: any): void {
- **BUG** `services/mobile-api/src/utils/logger.ts:44` - console.debug(this.formatMessage('DEBUG', message, data));
- **BUG** `services/dmlog-marketplace/stores/miniature_designer.py:62` - "goblin": {"name": "Goblin", "variants": ["standard", "hobgoblin", "bugbear"]},
- **BUG** `services/simulation/traffic/pattern_modeler.py:474` - logger.debug(f"Vehicle {vehicle.vehicle_id} considering lane change")
- **BUG** `services/blockchain/tokens/reputation_token_manager.py:65` - BUG_REPORTING = "bug_reporting"
- **BUG** `services/blockchain/tokens/reputation_token_manager.py:243` - ReputationAction.BUG_REPORTING: Decimal("5.0"),
- **BUG** `services/blockchain/tokens/reputation_token_manager.py:627` - ReputationAction.BUG_REPORTING: ReputationCategory.COMMUNITY,
- **BUG** `services/ads/ad_service.py:25` - debug_mode: bool = False
- **BUG** `services/ads/ad_service.py:132` - if self.config.debug_mode:
- **BUG** `services/ads/ad_service.py:467` - debug_mode=True
- **HACK** `services/ads/integrations/adsense_integration.py:476` - "illegal_activities": ["drug", "illegal", "piracy", "hack"],
- **BUG** `services/collaboration/main.py:218` - if settings.DEBUG:
- **BUG** `services/collaboration/main.py:233` - # Development endpoints (only in debug mode)
- **BUG** `services/collaboration/main.py:234` - if settings.DEBUG:
- **BUG** `services/collaboration/main.py:252` - reload=settings.DEBUG,
- **BUG** `services/collaboration/main.py:254` - log_level="debug" if settings.DEBUG else "info",
- **TODO** `services/collaboration/src/guests/guest_manager.py:108` - # TODO: Check if created_by has admin permission on document
- **TODO** `services/collaboration/src/annotations/realtime_handler.py:85` - # TODO: Verify user has access to document
- **TODO** `services/collaboration/src/annotations/annotation_manager.py:133` - # TODO: Check if user has admin permissions
- **TODO** `services/collaboration/src/annotations/annotation_manager.py:204` - # TODO: Check if user has admin permissions
- **TODO** `services/collaboration/src/discussions/discussion_handler.py:85` - # TODO: Verify user has access to document
- **TODO** `services/collaboration/src/discussions/comment_manager.py:141` - # TODO: Check admin permissions
- **TODO** `services/collaboration/src/discussions/comment_manager.py:219` - # TODO: Check admin permissions
- **BUG** `services/collaboration/src/activity/activity_manager.py:125` - logger.debug(f"Logged activity {activity_id}: {activity_type.value}")
- **TODO** `services/collaboration/src/activity/activity_manager.py:139` - # TODO: Check if user has access to workspace
- **TODO** `services/collaboration/src/activity/activity_manager.py:184` - # TODO: Check if user has access to document
- **BUG** `services/collaboration/src/core/config.py:15` - DEBUG: bool = Field(default=False, description="Debug mode")
- **BUG** `services/collaboration/src/core/config.py:131` - "level": "DEBUG" if settings.DEBUG else "INFO",
- **BUG** `services/collaboration/src/core/config.py:142` - "level": "DEBUG" if settings.DEBUG else "INFO",
- **BUG** `services/collaboration/src/core/database.py:300` - self.engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
- **HACK** `services/dmlog-converter/converters/setting_adapter.py:198` - SettingTheme.CYBERPUNK: ["cyber", "hacker", "corporate", "dystopian"],
- **BUG** `services/ml-pipeline/src/utils/config.py:111` - debug: bool = True
- **BUG** `services/ml-pipeline/src/utils/config.py:146` - config_dict.setdefault("debug", os.getenv("ML_PIPELINE_DEBUG", "true").lower() == "true")
- **BUG** `services/ml-pipeline/src/utils/config.py:224` - debug=config_dict.get("debug", True)
- **BUG** `services/ml-pipeline/src/utils/config.py:247` - "debug": config.debug,
- **BUG** `services/ml-pipeline/src/utils/config.py:433` - print(f"  Debug: {config.debug}")
- **BUG** `services/p2p-sync/core/config.py:145` - debug: bool = Field(default=False)
- **BUG** `services/p2p-sync/core/config.py:201` - valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
- **BUG** `services/smart-folders/main.py:227` - reload=settings.DEBUG,
- **BUG** `services/smart-folders/main.py:228` - log_level="info" if not settings.DEBUG else "debug",
- **BUG** `services/smart-folders/main.py:229` - workers=1 if settings.DEBUG else settings.WORKERS
- **BUG** `services/smart-folders/src/ai/folder_suggester.py:489` - logger.debug(f"Error extracting keywords: {e}")
- **BUG** `services/smart-folders/src/core/config.py:86` - debug: bool = Field(default=False)
- **BUG** `services/smart-folders/src/core/config.py:118` - valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
- **BUG** `services/smart-folders/src/core/config.py:134` - def DEBUG(self) -> bool:
- **BUG** `services/smart-folders/src/core/config.py:136` - return self.debug
- **BUG** `services/smart-folders/src/core/rule_engine.py:134` - logger.debug(f"Could not read content from {self.file_path}: {e}")
- **BUG** `services/smart-folders/src/core/rule_engine.py:163` - logger.debug(f"Could not extract image metadata from {self.file_path}: {e}")
- **BUG** `services/smart-folders/src/core/rule_engine.py:168` - logger.debug(f"Error extracting metadata from {self.file_path}: {e}")
- **BUG** `services/smart-folders/src/core/rule_engine.py:257` - logger.debug(f"Error evaluating file {file_path}: {e}")
- **BUG** `services/smart-folders/src/core/rule_engine.py:324` - logger.debug(f"Error evaluating rule {rule}: {e}")
- **BUG** `services/smart-folders/src/core/rule_engine.py:356` - logger.debug(f"Error evaluating rule: {e}")
- **BUG** `services/smart-folders/src/core/smart_folder_manager.py:489` - logger.debug(f"Collected metrics: {json.dumps(metrics, default=str)}")
- **BUG** `services/notifications/main.py:227` - reload=settings.DEBUG,
- **BUG** `services/notifications/services/preference_service.py:172` - logger.debug(f"Updated preferences for user {user_id}, type {notification_type}")
- **BUG** `services/notifications/services/template_service.py:322` - logger.debug(f"Loaded default template: {template_data['template_id']}")
- **BUG** `services/notifications/services/sms_service.py:169` - logger.debug(f"SMS sent successfully: {notification_id} -> {to_phone}")
- **BUG** `services/notifications/services/sync_integration.py:149` - logger.debug(f"Sent sync complete notification for user {user_id}")
- **BUG** `services/notifications/services/webhook_service.py:180` - logger.debug(f"Webhook sent successfully: {notification_id} -> {webhook_url}")
- **BUG** `services/notifications/services/webhook_service.py:487` - logger.debug(f"Successfully retried webhook: {webhook['notification_id']}")
- **BUG** `services/notifications/services/email_service.py:225` - logger.debug(f"Email sent successfully via {provider}: {notification_id}")
- **BUG** `services/notifications/services/digest_service.py:178` - logger.debug(f"Sent digest email to user {user_id}")
- **BUG** `services/notifications/services/digest_service.py:419` - logger.debug(f"Scheduled {digest_type} digest for user {user_id} at {scheduled_for}")
- **BUG** `services/notifications/api/websocket.py:164` - logger.debug(f"Sent {len(notifications)} pending notifications to user {user_id}")
- **BUG** `services/notifications/api/websocket.py:406` - logger.debug(f"Sent notification to {sent_count} connections for user {user_id}")
- **BUG** `services/notifications/core/logging_config.py:48` - file_handler.setLevel(logging.DEBUG)
- **BUG** `services/notifications/core/logging_config.py:60` - logging.getLogger("notifications").setLevel(logging.DEBUG)
- **BUG** `services/notifications/core/config.py:16` - DEBUG: bool = False
- **BUG** `services/video-processor/run.py:14` - reload=settings.DEBUG,
- **BUG** `services/video-processor/main.py:512` - reload=settings.DEBUG,
- **BUG** `services/video-processor/processors/thumbnail_generator.py:301` - logger.debug(f"Created preview segment: {output_path}")
- **BUG** `services/video-processor/processors/thumbnail_generator.py:356` - logger.debug(f"Created short preview: {output_path}")
- **BUG** `services/video-processor/processors/thumbnail_generator.py:400` - logger.debug(f"Created GIF preview: {output_path}")
- **BUG** `services/video-processor/processors/scene_detector.py:654` - logger.debug(f"Created scene preview: {output_path}")
- **BUG** `services/video-processor/core/config.py:16` - DEBUG: bool = False
- **BUG** `services/video-processor/core/logging.py:48` - file_handler.setLevel(logging.DEBUG)
- **BUG** `services/video-processor/src/keyframeExtractor.js:99` - logger.debug(`Extracted keyframe at frame ${frameNumber} (${timestamp.toFixed(2)}s)`);
- **BUG** `services/cache/metadata_cache.py:68` - logger.debug(f"Cached metadata for file {file_id}")
- **BUG** `services/cache/metadata_cache.py:284` - logger.debug(f"Removed file {file_id} from cache")
- **BUG** `services/cache/metadata_cache.py:298` - logger.debug(f"Invalidated cache for user {user_id}")
- **BUG** `services/cache/distributed_locks.py:137` - logger.debug(f"Acquired lock {lock_id} for resource {resource}")
- **BUG** `services/cache/distributed_locks.py:247` - logger.debug(f"Released lock {lock_id} for resource {resource}")
- **BUG** `services/cache/invalidation.py:112` - logger.debug(f"Registered invalidation rule for {event_type}: {rule}")
- **BUG** `services/cache/invalidation.py:320` - logger.debug(f"Processed {processed} lazy invalidations")
- **BUG** `services/cache/api_cache.py:259` - response.headers['X-Cache-Key'] = cache_key[:16]  # Shortened for debugging
- **BUG** `services/cache/api_cache.py:328` - logger.debug(f"Cached response for {request.method} {request.url.path}")
- **BUG** `services/cache/api_cache.py:368` - logger.debug(f"Invalidated {invalidated_count} cached responses")
- **BUG** `services/file-watcher/watcher.py:75` - self.logger.debug(f"Ignoring file: {file_path}")
- **TODO** `services/file-watcher/watcher.py:376` - # TODO: Implement actual batch processing
- **BUG** `services/file-watcher/watcher.py:405` - self.logger.debug(f"Metrics: {metrics}")
- **TODO** `services/file-watcher/watcher.py:407` - # TODO: Store metrics in database or send to monitoring system
- **TODO** `services/file-watcher/watcher.py:455` - # TODO: Remove observer watch (requires tracking watch handles)
- **BUG** `services/file-watcher/batch_importer.py:151` - logger.debug(f"Skipping large file: {file_path} ({stat.st_size} bytes)")
- **BUG** `services/file-watcher/batch_importer.py:290` - logger.debug(f"Throttling: waiting {delay:.2f}s")
- **BUG** `services/file-watcher/event_queue.py:74` - logger.debug(f"Stream creation info: {e}")
- **BUG** `services/file-watcher/event_queue.py:172` - logger.debug(f"Event sent to NATS: {ack.seq}")
- **BUG** `services/file-watcher/event_queue.py:193` - logger.debug(f"Batch sent to NATS: {ack.seq}")
- **BUG** `services/file-watcher/event_queue.py:216` - logger.debug("Event sent to Redis queue")
- **BUG** `services/file-watcher/event_queue.py:230` - logger.debug(f"Event added to local queue (size: {len(self.local_queue)})")
- **BUG** `services/file-watcher/event_queue.py:346` - logger.debug(f"Notified sync engine of event: {event_data['file_path']}")
- **BUG** `services/file-watcher/main.py:122` - logger.debug(f"Batch queue result: {result}")
- **BUG** `services/analytics/services/usage_tracker.py:118` - logger.debug(f"Tracked file upload for user {user_id}: {filename}")
- **BUG** `services/analytics/services/usage_tracker.py:159` - logger.debug(f"Tracked API call for user {user_id}: {method} {endpoint}")
- **BUG** `services/analytics/services/usage_tracker.py:189` - logger.debug(f"Tracked storage usage for user {user_id}: {total_size} bytes")
- **BUG** `services/analytics/services/report_generator.py:510` - logger.debug(f"Deleted old export: {file_path.name}")
- **BUG** `services/analytics/services/dashboard_aggregator_backup.py:117` - result = {\n                    \"tenant_id\": tenant_id,\n                    \"time_range\": time_range,\n                    \"period\": {\n                        \"start_date\": start_date.isoformat(),\n                        \"end_date\": end_date.isoformat()\n                    },\n                    \"file_uploads\": {\n                        \"total\": upload_metrics[\"total_uploads\"] or 0,\n                        \"total_bytes\": upload_metrics[\"total_bytes\"] or 0,\n                        \"successful\": upload_metrics[\"successful_uploads\"] or 0,\n                        \"failed\": upload_metrics[\"failed_uploads\"] or 0,\n                        \"avg_upload_time_ms\": float(upload_metrics[\"avg_upload_time_ms\"] or 0),\n                        \"success_rate\": (\n                            (upload_metrics[\"successful_uploads\"] or 0) / max(upload_metrics[\"total_uploads\"] or 1, 1)\n                        )\n                    },\n                    \"api_calls\": {\n                        \"total\": api_metrics[\"total_calls\"] or 0,\n                        \"successful\": api_metrics[\"successful_calls\"] or 0,\n                        \"errors\": api_metrics[\"error_calls\"] or 0,\n                        \"avg_response_time_ms\": float(api_metrics[\"avg_response_time_ms\"] or 0),\n                        \"error_rate\": (\n                            (api_metrics[\"error_calls\"] or 0) / max(api_metrics[\"total_calls\"] or 1, 1)\n                        )\n                    },\n                    \"storage\": {\n                        \"total_bytes\": storage_metrics[\"total_storage_bytes\"] or 0,\n                        \"total_files\": storage_metrics[\"total_files\"] or 0\n                    },\n                    \"ai_operations\": {\n                        \"total\": ai_metrics[\"total_operations\"] or 0,\n                        \"total_tokens\": ai_metrics[\"total_tokens\"] or 0,\n                        \"total_cost_usd\": float(ai_metrics[\"total_ai_cost\"] or 0),\n                        \"models_used\": ai_metrics[\"models_used\"] or 0\n                    },\n                    \"users\": {\n                        \"active_users\": active_users or 0\n                    },\n                    \"costs\": {\n                        \"total_usd\": float(total_costs or 0)\n                    },\n                    \"generated_at\": datetime.now().isoformat()\n                }\n                \n                # Cache the result\n                self.cache[cache_key] = result\n                self.cache_timestamps[cache_key] = datetime.now()\n                self.stats[\"cache_misses\"] += 1\n                self.stats[\"aggregations_generated\"] += 1\n                \n                return result\n                \n        except Exception as e:\n            logger.error(\"Error generating overview metrics\", \n                        tenant_id=tenant_id, \n                        time_range=time_range,\n                        error=str(e))\n            return {}\n    \n    async def get_time_series_chart_data(self, metric: str, tenant_id: str = None,\n                                        time_range: str = \"24h\", interval: str = \"1h\") -> Dict[str, Any]:\n        \"\"\"Get time series data formatted for charts\"\"\"\n        cache_key = f\"timeseries_{metric}_{tenant_id}_{time_range}_{interval}\"\n        \n        # Check cache\n        if self._is_cache_valid(cache_key):\n            self.stats[\"cache_hits\"] += 1\n            return self.cache[cache_key]\n        \n        try:\n            start_date, end_date = self._parse_time_range(time_range)\n            \n            # Map intervals to PostgreSQL intervals\n            pg_intervals = {\n                \"1m\": \"1 minute\",\n                \"5m\": \"5 minutes\",\n                \"15m\": \"15 minutes\",\n                \"1h\": \"1 hour\",\n                \"4h\": \"4 hours\",\n                \"1d\": \"1 day\"\n            }\n            \n            pg_interval = pg_intervals.get(interval, \"1 hour\")\n            \n            async with db_manager.pool.acquire() as conn:\n                if metric == \"uploads\":\n                    data = await conn.fetch(\"\"\"\n                        SELECT \n                            time_bucket($1::interval, timestamp) as time_bucket,\n                            COUNT(*) as value,\n                            SUM(file_size) as total_bytes,\n                            COUNT(CASE WHEN upload_status = 'completed' THEN 1 END) as successful,\n                            COUNT(CASE WHEN upload_status = 'failed' THEN 1 END) as failed\n                        FROM file_uploads \n                        WHERE ($2::UUID IS NULL OR tenant_id = $2)\n                            AND timestamp >= $3 AND timestamp <= $4\n                        GROUP BY time_bucket\n                        ORDER BY time_bucket\n                    \"\"\", pg_interval, tenant_id, start_date, end_date)\n                    \n                elif metric == \"api_calls\":\n                    data = await conn.fetch(\"\"\"\n                        SELECT \n                            time_bucket($1::interval, timestamp) as time_bucket,\n                            COUNT(*) as value,\n                            AVG(response_time_ms) as avg_response_time,\n                            COUNT(CASE WHEN status_code < 400 THEN 1 END) as successful,\n                            COUNT(CASE WHEN status_code >= 400 THEN 1 END) as errors\n                        FROM api_calls \n                        WHERE ($2::UUID IS NULL OR tenant_id = $2)\n                            AND timestamp >= $3 AND timestamp <= $4\n                        GROUP BY time_bucket\n                        ORDER BY time_bucket\n                    \"\"\", pg_interval, tenant_id, start_date, end_date)\n                    \n                elif metric == \"ai_operations\":\n                    data = await conn.fetch(\"\"\"\n                        SELECT \n                            time_bucket($1::interval, timestamp) as time_bucket,\n                            COUNT(*) as value,\n                            SUM(input_tokens + output_tokens) as total_tokens,\n                            SUM(cost_usd) as total_cost\n                        FROM ai_operations \n                        WHERE ($2::UUID IS NULL OR tenant_id = $2)\n                            AND timestamp >= $3 AND timestamp <= $4\n                        GROUP BY time_bucket\n                        ORDER BY time_bucket\n                    \"\"\", pg_interval, tenant_id, start_date, end_date)\n                    \n                elif metric == \"costs\":\n                    data = await conn.fetch(\"\"\"\n                        SELECT \n                            time_bucket($1::interval, timestamp) as time_bucket,\n                            SUM(amount_usd) as value,\n                            cost_type\n                        FROM costs \n                        WHERE ($2::UUID IS NULL OR tenant_id = $2)\n                            AND timestamp >= $3 AND timestamp <= $4\n                        GROUP BY time_bucket, cost_type\n                        ORDER BY time_bucket, cost_type\n                    \"\"\", pg_interval, tenant_id, start_date, end_date)\n                    \n                else:\n                    raise ValueError(f\"Unknown metric: {metric}\")\n                \n                # Format data for charts\n                if metric == \"costs\":\n                    # Group by cost type for stacked chart\n                    chart_data = defaultdict(list)\n                    timestamps = set()\n                    \n                    for row in data:\n                        timestamp = row[\"time_bucket\"].isoformat()\n                        timestamps.add(timestamp)\n                        chart_data[row[\"cost_type\"]].append({\n                            \"timestamp\": timestamp,\n                            \"value\": float(row[\"value\"] or 0)\n                        })\n                    \n                    result = {\n                        \"metric\": metric,\n                        \"tenant_id\": tenant_id,\n                        \"time_range\": time_range,\n                        \"interval\": interval,\n                        \"chart_type\": \"stacked_area\",\n                        \"series\": dict(chart_data),\n                        \"timestamps\": sorted(list(timestamps))\n                    }\n                else:\n                    # Single series chart\n                    chart_data = []\n                    for row in data:\n                        point = {\n                            \"timestamp\": row[\"time_bucket\"].isoformat(),\n                            \"value\": float(row[\"value\"] or 0)\n                        }\n                        \n                        # Add metric-specific fields\n                        for key, value in dict(row).items():\n                            if key not in [\"time_bucket\", \"value\"] and value is not None:\n                                point[key] = float(value) if isinstance(value, (int, float)) else value\n                        \n                        chart_data.append(point)\n                    \n                    result = {\n                        \"metric\": metric,\n                        \"tenant_id\": tenant_id,\n                        \"time_range\": time_range,\n                        \"interval\": interval,\n                        \"chart_type\": \"line\",\n                        \"data\": chart_data\n                    }\n                \n                result[\"generated_at\"] = datetime.now().isoformat()\n                \n                # Cache the result\n                self.cache[cache_key] = result\n                self.cache_timestamps[cache_key] = datetime.now()\n                self.stats[\"cache_misses\"] += 1\n                self.stats[\"aggregations_generated\"] += 1\n                \n                return result\n                \n        except Exception as e:\n            logger.error(\"Error generating time series chart data\",\n                        metric=metric,\n                        tenant_id=tenant_id,\n                        error=str(e))\n            return {}\n    \n    async def get_top_lists(self, tenant_id: str = None, time_range: str = \"24h\") -> Dict[str, Any]:\n        \"\"\"Get top lists for dashboard (top users, endpoints, etc.)\"\"\"\n        cache_key = f\"toplists_{tenant_id}_{time_range}\"\n        \n        # Check cache\n        if self._is_cache_valid(cache_key):\n            self.stats[\"cache_hits\"] += 1\n            return self.cache[cache_key]\n        \n        try:\n            start_date, end_date = self._parse_time_range(time_range)\n            \n            async with db_manager.pool.acquire() as conn:\n                # Top users by upload volume\n                top_uploaders = await conn.fetch(\"\"\"\n                    SELECT \n                        user_id,\n                        COUNT(*) as upload_count,\n                        SUM(file_size) as total_bytes\n                    FROM file_uploads \n                    WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                        AND timestamp >= $2 AND timestamp <= $3\n                    GROUP BY user_id\n                    ORDER BY total_bytes DESC\n                    LIMIT 10\n                \"\"\", tenant_id, start_date, end_date)\n                \n                # Top API endpoints by call count\n                top_endpoints = await conn.fetch(\"\"\"\n                    SELECT \n                        endpoint,\n                        COUNT(*) as call_count,\n                        AVG(response_time_ms) as avg_response_time,\n                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count\n                    FROM api_calls \n                    WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                        AND timestamp >= $2 AND timestamp <= $3\n                    GROUP BY endpoint\n                    ORDER BY call_count DESC\n                    LIMIT 10\n                \"\"\", tenant_id, start_date, end_date)\n                \n                # Top file types by size\n                top_file_types = await conn.fetch(\"\"\"\n                    SELECT \n                        COALESCE(file_type, 'unknown') as file_type,\n                        COUNT(*) as count,\n                        SUM(file_size) as total_bytes\n                    FROM file_uploads \n                    WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                        AND timestamp >= $2 AND timestamp <= $3\n                    GROUP BY file_type\n                    ORDER BY total_bytes DESC\n                    LIMIT 10\n                \"\"\", tenant_id, start_date, end_date)\n                \n                # Top AI models by usage\n                top_ai_models = await conn.fetch(\"\"\"\n                    SELECT \n                        model_name,\n                        COUNT(*) as operation_count,\n                        SUM(input_tokens + output_tokens) as total_tokens,\n                        SUM(cost_usd) as total_cost\n                    FROM ai_operations \n                    WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                        AND timestamp >= $2 AND timestamp <= $3\n                    GROUP BY model_name\n                    ORDER BY total_cost DESC\n                    LIMIT 10\n                \"\"\", tenant_id, start_date, end_date)\n                \n                # Recent errors\n                recent_errors = await conn.fetch(\"\"\"\n                    (\n                        SELECT \n                            'file_upload' as error_type,\n                            filename as context,\n                            error_message,\n                            timestamp\n                        FROM file_uploads \n                        WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                            AND timestamp >= $2 AND timestamp <= $3\n                            AND upload_status = 'failed'\n                            AND error_message IS NOT NULL\n                    )\n                    UNION ALL\n                    (\n                        SELECT \n                            'api_call' as error_type,\n                            endpoint as context,\n                            error_message,\n                            timestamp\n                        FROM api_calls \n                        WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                            AND timestamp >= $2 AND timestamp <= $3\n                            AND status_code >= 400\n                            AND error_message IS NOT NULL\n                    )\n                    ORDER BY timestamp DESC\n                    LIMIT 20\n                \"\"\", tenant_id, start_date, end_date)\n                \n                result = {\n                    \"tenant_id\": tenant_id,\n                    \"time_range\": time_range,\n                    \"top_uploaders\": [dict(row) for row in top_uploaders],\n                    \"top_endpoints\": [dict(row) for row in top_endpoints],\n                    \"top_file_types\": [dict(row) for row in top_file_types],\n                    \"top_ai_models\": [dict(row) for row in top_ai_models],\n                    \"recent_errors\": [dict(row) for row in recent_errors],\n                    \"generated_at\": datetime.now().isoformat()\n                }\n                \n                # Cache the result\n                self.cache[cache_key] = result\n                self.cache_timestamps[cache_key] = datetime.now()\n                self.stats[\"cache_misses\"] += 1\n                self.stats[\"aggregations_generated\"] += 1\n                \n                return result\n                \n        except Exception as e:\n            logger.error(\"Error generating top lists\",\n                        tenant_id=tenant_id,\n                        error=str(e))\n            return {}\n    \n    async def get_real_time_metrics(self, tenant_id: str = None) -> Dict[str, Any]:\n        \"\"\"Get real-time metrics (last 5 minutes)\"\"\"\n        try:\n            # Real-time data is not cached\n            start_date = datetime.now() - timedelta(minutes=5)\n            end_date = datetime.now()\n            \n            async with db_manager.pool.acquire() as conn:\n                # Recent uploads\n                recent_uploads = await conn.fetchval(\"\"\"\n                    SELECT COUNT(*) FROM file_uploads \n                    WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                        AND timestamp >= $2\n                \"\"\", tenant_id, start_date)\n                \n                # Recent API calls\n                recent_api_calls = await conn.fetchval(\"\"\"\n                    SELECT COUNT(*) FROM api_calls \n                    WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                        AND timestamp >= $2\n                \"\"\", tenant_id, start_date)\n                \n                # Recent AI operations\n                recent_ai_ops = await conn.fetchval(\"\"\"\n                    SELECT COUNT(*) FROM ai_operations \n                    WHERE ($1::UUID IS NULL OR tenant_id = $1)\n                        AND timestamp >= $2\n                \"\"\", tenant_id, start_date)\n                \n                # Active processing (from metrics table)\n                active_processing = await conn.fetchval(\"\"\"\n                    SELECT COUNT(DISTINCT tags->>'user_id') \n                    FROM metrics \n                    WHERE metric_name = 'upload_status'\n                        AND metric_value = 1\n                        AND ($1::UUID IS NULL OR tenant_id = $1)\n                        AND timestamp >= $2\n                \"\"\", tenant_id, start_date)\n                \n                return {\n                    \"tenant_id\": tenant_id,\n                    \"period_minutes\": 5,\n                    \"metrics\": {\n                        \"recent_uploads\": recent_uploads or 0,\n                        \"recent_api_calls\": recent_api_calls or 0,\n                        \"recent_ai_operations\": recent_ai_ops or 0,\n                        \"active_processing\": active_processing or 0\n                    },\n                    \"timestamp\": datetime.now().isoformat()\n                }\n                \n        except Exception as e:\n            logger.error(\"Error getting real-time metrics\",\n                        tenant_id=tenant_id,\n                        error=str(e))\n            return {}\n    \n    def _parse_time_range(self, time_range: str) -> tuple[datetime, datetime]:\n        \"\"\"Parse time range string to datetime objects\"\"\"\n        end_date = datetime.now()\n        \n        if time_range == \"1h\":\n            start_date = end_date - timedelta(hours=1)\n        elif time_range == \"24h\":\n            start_date = end_date - timedelta(hours=24)\n        elif time_range == \"7d\":\n            start_date = end_date - timedelta(days=7)\n        elif time_range == \"30d\":\n            start_date = end_date - timedelta(days=30)\n        elif time_range == \"90d\":\n            start_date = end_date - timedelta(days=90)\n        else:\n            # Default to 24h\n            start_date = end_date - timedelta(hours=24)\n        \n        return start_date, end_date\n    \n    def _is_cache_valid(self, cache_key: str) -> bool:\n        \"\"\"Check if cache entry is still valid\"\"\"\n        if cache_key not in self.cache:\n            return False\n        \n        cache_time = self.cache_timestamps.get(cache_key)\n        if not cache_time:\n            return False\n        \n        age_seconds = (datetime.now() - cache_time).total_seconds()\n        return age_seconds < settings.DASHBOARD_CACHE_TTL\n    \n    async def _cache_cleanup_task(self):\n        \"\"\"Background task to clean up expired cache entries\"\"\"\n        while True:\n            try:\n                current_time = datetime.now()\n                expired_keys = []\n                \n                for cache_key, timestamp in self.cache_timestamps.items():\n                    age_seconds = (current_time - timestamp).total_seconds()\n                    if age_seconds > settings.DASHBOARD_CACHE_TTL * 2:  # Clean up after 2x TTL\n                        expired_keys.append(cache_key)\n                \n                # Remove expired entries\n                for key in expired_keys:\n                    self.cache.pop(key, None)\n                    self.cache_timestamps.pop(key, None)\n                \n                if expired_keys:\n                    logger.debug(\"Cleaned up expired cache entries\", count=len(expired_keys))\n                \n                # Sleep for 5 minutes\n                await asyncio.sleep(300)\n                \n            except Exception as e:\n                logger.error(\"Error in cache cleanup task\", error=str(e))\n                await asyncio.sleep(60)\n    \n    def get_stats(self) -> Dict[str, Any]:\n        \"\"\"Get dashboard aggregator statistics\"\"\"\n        stats = self.stats.copy()\n        stats[\"uptime_seconds\"] = (datetime.now() - stats[\"start_time\"]).total_seconds()\n        stats[\"cache_size\"] = len(self.cache)\n        stats[\"cache_hit_rate\"] = (\n            stats[\"cache_hits\"] / max(stats[\"cache_hits\"] + stats[\"cache_misses\"], 1)\n        )\n        return stats
- **BUG** `services/analytics/services/cost_tracker.py:103` - logger.debug(f"Tracked AI operation for user {user_id}: ${cost_usd:.6f}")
- **BUG** `services/analytics/services/cost_tracker.py:185` - logger.debug(f"Tracked file processing cost for user {user_id}: ${total_cost:.6f}")
- **BUG** `services/analytics/api/websocket.py:111` - logger.debug(f"Broadcasted to {len(subscribers)} subscribers of {subscription_type}")
- **BUG** `services/analytics/core/logging_config.py:48` - file_handler.setLevel(logging.DEBUG)
- **BUG** `services/analytics/core/logging_config.py:59` - logging.getLogger("analytics").setLevel(logging.DEBUG)
- **BUG** `services/analytics/core/config.py:16` - DEBUG: bool = False
- **BUG** `services/sync-engine/offline_queue.py:149` - logger.debug(f"Enqueued item {item_id} in SQLite: {operation} {file_path}")
- **BUG** `services/sync-engine/offline_queue.py:157` - logger.debug(f"Enqueued item {item_id} in Redis: {operation} {file_path}")
- **BUG** `services/sync-engine/workers.py:111` - logger.debug(f"Stream {config['name']} already exists")
- **BUG** `optimizations/compression/request_compression.py:384` - logger.debug(
- **BUG** `optimizations/database/query_optimizations.py:265` - logger.debug(f"Index already exists: {index_sql[:50]}...")
- **BUG** `optimizations/database/lazy_loading.py:60` - logger.debug(f"Lazy loaded field: {field_name}")
- **BUG** `optimizations/database/lazy_loading.py:304` - logger.debug(f"Lazy loaded page {page} with {len(items)} items")
- **BUG** `migrations/data-import/platform_importers.py:150` - self.logger.debug(f"Could not extract image metadata: {e}")
- **BUG** `migrations/data-import/platform_importers.py:167` - self.logger.debug(f"Could not extract video metadata: {e}")
- **BUG** `migrations/anonymization/data_anonymizer.py:444` - logger.debug(f"Processed {records_processed}/{total_records} records in {table_name}")
- **TODO** `migrations/database-migration/version_migrator.py:653` - template = f"""-- @description: {args.description or 'TODO: Add migration description'}
- **TODO** `migrations/database-migration/version_migrator.py:659` - -- TODO: Add your migration SQL here
- **TODO** `migrations/database-migration/version_migrator.py:668` - -- TODO: Add your rollback SQL here
- **BUG** `dev-tools/cli/activelog_cli.py:83` - level = logging.DEBUG if verbose else logging.INFO
- **BUG** `dev-tools/visualization/dependency_visualizer.py:228` - logger.debug(f"Error analyzing {file_path}: {e}")
- **BUG** `dev-tools/visualization/dependency_visualizer.py:381` - logger.debug(f"Error analyzing config {config_path}: {e}")
- **BUG** `dev-tools/visualization/dependency_visualizer.py:548` - logger.debug(f"Error analyzing {compose_file}: {e}")
- **BUG** `dev-tools/visualization/dependency_visualizer.py:965` - logging.getLogger().setLevel(logging.DEBUG)
- **BUG** `dev-tools/profiling/service_profiler.py:271` - logger.debug(f"Error testing endpoint {endpoint}: {e}")
- **BUG** `dev-tools/profiling/service_profiler.py:842` - logging.getLogger().setLevel(logging.DEBUG)
- **BUG** `dev-tools/templates/generate_service.py:484` - - `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- **BUG** `dev-tools/templates/generate_service.py:1013` - app.run(host='0.0.0.0', port={{SERVICE_PORT}}, debug=True)
- **BUG** `dev-tools/templates/service_templates/flask/app.py:79` - app.run(host='0.0.0.0', port={{SERVICE_PORT}}, debug=True)
- **BUG** `dev-tools/setup/dev_setup.py:390` - DEBUG=true
- **BUG** `dev-tools/setup/dev_setup.py:391` - LOG_LEVEL=DEBUG
- **BUG** `dev-tools/setup/dev_setup.py:435` - # Debug settings
- **BUG** `dev-tools/setup/dev_setup.py:436` - DEBUG=true
- **BUG** `dev-tools/setup/dev_setup.py:437` - LOG_LEVEL=DEBUG
- **BUG** `dev-tools/setup/dev_setup.py:458` - QUERY_DEBUG=true
- **BUG** `dev-tools/setup/dev_setup.py:933` - """Print the setup log for debugging."""
- **BUG** `dev-tools/setup/dev_setup.py:959` - logging.getLogger().setLevel(logging.DEBUG)
- **HACK** `security-audit/tests/test_sql_injection.py:63` - "admin'; INSERT INTO users (username, password) VALUES ('hacker', 'password')--",
- **BUG** `modules/healthcare/src/dicom/dicom_manager.py:559` - logger.debug(f"Cleaned up temp file: {temp_file}")
- **HACK** `modules/healthcare/src/compliance/hipaa_manager.py:408` - if incident_type in ["unauthorized_access", "data_theft", "system_hack", "lost_device"]:
- **BUG** `modules/healthcare/src/core/config.py:15` - DEBUG: bool = Field(default=False, description="Debug mode (should be False in production)")
- **BUG** `modules/healthcare/src/core/config.py:131` - @validator("DEBUG")
- **BUG** `modules/healthcare/src/core/config.py:132` - def validate_debug_in_production(cls, v, values):
- **BUG** `modules/healthcare/src/core/config.py:134` - raise ValueError("DEBUG must be False in production environment")
- **BUG** `modules/healthcare/src/core/config.py:183` - "level": "DEBUG" if settings.DEBUG else "INFO",
- **BUG** `modules/healthcare/src/core/config.py:194` - "level": "DEBUG" if settings.DEBUG else "INFO",
- **BUG** `deployment/stores/legal/privacy/privacy_policy_generator.py:86` - purpose="Technical support and debugging",
- **TODO** `security/auth/two-factor-auth.py:824` - # TODO: Also verify password
- **BUG** `edge/monitoring/remote-monitor.py:220` - self.logger.debug(f"Temperature reading failed: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:263` - self.logger.debug(f"Network latency measurement failed: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:280` - self.logger.debug(f"Error count failed: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:334` - self.logger.debug(f"Custom metrics collection failed: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:366` - self.logger.debug(f"ActiveLog agent metrics failed: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:388` - self.logger.debug(f"GPU metrics failed: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:420` - self.logger.debug(f"Docker metrics failed: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:633` - self.logger.debug(f"Version detection error: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:1251` - self.logger.debug(f"Maintenance window check error: {e}")
- **BUG** `edge/monitoring/remote-monitor.py:1300` - self.logger.debug("Report sent successfully")
- **BUG** `edge/monitoring/remote-monitor.py:1305` - self.logger.debug(f"Report sending failed: {e}")
- **BUG** `edge/security/edge-security.py:915` - self.logger.debug(f"Process check error: {e}")
- **BUG** `edge/security/edge-security.py:942` - self.logger.debug(f"File integrity check error for {file_path}: {e}")
- **BUG** `edge/security/edge-security.py:973` - self.logger.debug(f"Network connections check error: {e}")
- **BUG** `edge/offline-sync/sync-queue.py:160` - self.logger.debug(f"Added sync item: {item.id} ({item.operation_type})")
- **BUG** `edge/offline-sync/sync-queue.py:451` - self.logger.debug("No network connection - skipping sync")
- **BUG** `edge/offline-sync/sync-queue.py:517` - self.logger.debug(f"Successfully synced item: {item.id}")
- **BUG** `edge/camera-firmware/camera-agent.py:798` - self.logger.debug(f"Saved frame {frame_id} ({file_size} bytes)")
- **BUG** `edge/power-management/power-agent.py:237` - self.logger.debug(f"Failed to read temperature from {zone_name}: {e}")
- **BUG** `edge/power-management/power-agent.py:476` - self.logger.debug(f"Set CPU governor to: {governor}")
- **BUG** `edge/power-management/power-agent.py:495` - self.logger.debug(f"Set CPU frequency limit to {max_percent}%")
- **BUG** `edge/power-management/power-agent.py:517` - self.logger.debug(f"Set GPU power limit to {target_power}W ({power_percent}%)")
- **BUG** `edge/power-management/power-agent.py:519` - self.logger.debug(f"GPU power limit not set (NVIDIA GPU not available): {e}")
- **BUG** `edge/device-discovery/discovery-agent.py:262` - self.logger.debug(f"Could not get services for {addr}: {e}")
- **BUG** `edge/device-discovery/discovery-agent.py:783` - self.logger.debug(f"Updated device: {device.name} ({device.device_type})")
- **TODO** `edge/management-dashboard/dashboard.py:586` - # TODO: Actually send command to device
- **BUG** `edge/management-dashboard/dashboard.py:649` - def run(self, host='0.0.0.0', port=5000, debug=False):
- **BUG** `edge/management-dashboard/dashboard.py:651` - self.socketio.run(self.app, host=host, port=port, debug=debug)
- **BUG** `edge/management-dashboard/dashboard.py:800` - debug=False
- **BUG** `edge/iot-integration/azure-iot-hub.py:82` - self.logger.debug(f"Telemetry sent: {data}")
- **BUG** `edge/iot-integration/azure-iot-hub.py:103` - self.logger.debug(f"Reported properties updated: {properties}")
- **BUG** `edge/iot-integration/google-cloud-iot.py:162` - self.logger.debug(f"Message {mid} published successfully")
- **BUG** `edge/iot-integration/mqtt-broker.py:149` - self.logger.debug(f"Message received on {topic}: {payload}")
- **BUG** `edge/iot-integration/mqtt-broker.py:167` - self.logger.debug(f"Message {mid} published successfully")
- **BUG** `edge/iot-integration/mqtt-broker.py:171` - self.logger.debug(f"Subscription {mid} granted with QoS {granted_qos}")
- **BUG** `edge/iot-integration/mqtt-broker.py:175` - self.logger.debug(f"Unsubscription {mid} confirmed")
- **BUG** `edge/iot-integration/lorawan-gateway.py:145` - self.logger.debug(f"PUSH_ACK received with token {token}")
- **BUG** `edge/iot-integration/lorawan-gateway.py:488` - self.logger.debug(f"TX ACK received for token {token}")
- **BUG** `edge/iot-integration/integration-manager.py:269` - self.logger.debug(f"Telemetry published to {platform_name}")
- **BUG** `edge/iot-integration/integration-manager.py:362` - self.logger.debug(f"Stored {data_type} data locally: {filepath}")
- **BUG** `sdk/python/setup.py:20` - "Bug Tracker": "https://github.com/activelog/plugin-sdk-python/issues",
- **BUG** `sdk/python/activelog_plugin_sdk/types.py:391` - def debug(self, message: str, *args: Any) -> None:
- **BUG** `sdk/python/activelog_plugin_sdk/plugin.py:98` - if level == 'debug':
- **BUG** `sdk/python/activelog_plugin_sdk/plugin.py:99` - logger.debug(message, *args)
- **BUG** `sdk/typescript/src/core/Plugin.ts:144` - protected log(level: 'debug' | 'info' | 'warn' | 'error', message: string, data?: any): void {
- **BUG** `sdk/typescript/src/core/Plugin.ts:149` - case 'debug':
- **BUG** `sdk/typescript/src/core/Plugin.ts:150` - logger.debug(message, data);
- **BUG** `sdk/typescript/src/core/PluginRuntime.ts:438` - debug: (message, ...args) => this.logger.debug(`[${pluginId}] ${message}`, ...args),
- **BUG** `sdk/typescript/src/types/index.ts:156` - debug(message: string, ...args: any[]): void;
- **BUG** `production/configs/tracing/correlation-middleware.py:354` - logger.debug("Span started", extra={
- **BUG** `production/configs/tracing/correlation-middleware.py:381` - logger.debug("Span completed", extra={
- **BUG** `production/configs/tracing/correlation-middleware.py:437` - logger.debug("Async span started", extra={
- **BUG** `production/configs/tracing/correlation-middleware.py:464` - logger.debug("Async span completed", extra={
- **BUG** `frontend/src/components/settings/SettingsManager.js:286` - debugMode: false,
- **BUG** `frontend/src/components/settings/SettingsManager.js:750` - <div class="toggle-description">Send crash reports to help fix bugs</div>
- **BUG** `frontend/src/components/settings/SettingsManager.js:1105` - data-key="advanced.debugMode"
- **BUG** `frontend/src/components/settings/SettingsManager.js:1106` - ${settings.debugMode ? 'checked' : ''}>
- **BUG** `frontend/src/components/settings/SettingsManager.js:1109` - <div class="toggle-title">Debug Mode</div>
- **BUG** `frontend/src/components/settings/SettingsManager.js:1110` - <div class="toggle-description">Enable debugging features</div>
- **BUG** `app-factory/base/src/components/modules/SettingsModule.js:367` - <option value="debug">Debug</option>
- **BUG** `app-factory/base/src/components/modules/SettingsModule.js:374` - <p class="setting-description">Download application logs for debugging</p>
- **BUG** `docs/inline-docs/auth-service-docs.py:163` - docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
- **BUG** `docs/inline-docs/auth-service-docs.py:164` - redoc_url="/redoc" if settings.DEBUG else None,
- **BUG** `docs/inline-docs/auth-service-docs.py:165` - openapi_url="/openapi.json" if settings.DEBUG else None,
- **BUG** `docs/inline-docs/auth-service-docs.py:190` - if not settings.DEBUG:
- **TODO** `docs/inline-docs/auth-service-docs.py:274` - "uptime": 0,  # TODO: Implement actual uptime tracking
- **BUG** `docs/inline-docs/auth-service-docs.py:281` - "documentation": "/docs" if settings.DEBUG else None
- **TODO** `docs/inline-docs/auth-service-docs.py:406` - "uptime_seconds": 0,  # TODO: Implement uptime tracking
- **TODO** `docs/inline-docs/auth-service-docs.py:428` - # TODO: Add more health checks (Redis, external APIs, disk space, etc.)
- **TODO** `docs/inline-docs/auth-service-docs.py:509` - "request_id": None  # TODO: Add request tracking
- **BUG** `docs/inline-docs/auth-service-docs.py:639` - - Logs detailed errors for debugging
- **BUG** `docs/inline-docs/auth-service-docs.py:651` - "message": "Internal server error" if not settings.DEBUG else str(exc),
- **BUG** `docs/inline-docs/auth-service-docs.py:676` - debug=settings.DEBUG,
- **BUG** `docs/inline-docs/auth-service-docs.py:677` - reload=settings.DEBUG,
- **BUG** `docs/inline-docs/auth-service-docs.py:679` - log_level="info" if settings.DEBUG else "warning"
- **BUG** `tests/conftest.py:472` - 'LOG_LEVEL': 'DEBUG'
- **BUG** `tests/docker/mock_server.py:86` - elif "error" in content or "debug" in content:
- **BUG** `tests/fixtures/data_generators.py:504` - - DEBUG: Boolean flag for debug mode
- **BUG** `tests/e2e/test_user_workflows.py:29` - headless=True,  # Set to False for debugging
- **BUG** `tests/e2e/test_user_workflows.py:56` - # Enable request/response logging for debugging
- **BUG** `tests/e2e/test_user_workflows.py:117` - """Take screenshot for debugging"""

## Raw Audit Output

```
[0;34m==================================
ActiveLog System Audit Report
Generated: 2025-08-22 22:17:17
==================================[0m

[0;32m=== 1. SERVICES ANALYSIS ===[0m
SERVICE_ANALYSIS_START
RUNNING_PROCESSES:
root         677  0.0  0.0   7660  4800 pts/0    S    01:05   0:00 su - activeloguser
activel+    3745  0.1  0.3 264444 62484 pts/0    Sl   01:22   1:53 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
activel+    3746  0.1  0.3 240364 58796 pts/0    Sl   01:22   1:52 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8001
activel+    3747  0.1  0.3 358956 56032 pts/0    Sl   01:22   1:53 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8088
root       14901  0.0  0.0   7660  4800 pts/2    S    06:17   0:00 su - activeloguser
root       16748  0.0  0.0   7660  4800 pts/4    S    07:16   0:00 su - activeloguser
activel+   18413  0.0  0.0   4916  3264 ?        Ss   07:37   0:00 /bin/bash -c -l source /home/activeloguser/.claude/shell-snapshots/snapshot-bash-1755824307642-vixhde.sh && eval 'python3 main_simple.py' \< /dev/null && pwd -P >| /tmp/claude-3953-cwd
root       41302  0.0  0.0   7660  4608 pts/8    S    15:35   0:00 su - activeloguser
root       44775  0.0  0.0   7660  4800 pts/5    S    16:53   0:00 su - activeloguser
activel+   63823  0.0  0.0   4916  3264 ?        Ss   22:17   0:00 /bin/bash -c -l source /home/activeloguser/.claude/shell-snapshots/snapshot-bash-1755905409738-f0zzkq.sh && eval 'python3 generate_audit_report.py' \< /dev/null && pwd -P >| /tmp/claude-7f86-cwd
activel+   63848  0.0  0.0   4784  3264 ?        S    22:17   0:00 /bin/bash /home/activeloguser/activelog/audit_system.sh

LISTENING_PORTS:
tcp        0      0 0.0.0.0:3000            0.0.0.0:*               LISTEN      3825/python3        
tcp        0      0 0.0.0.0:9000            0.0.0.0:*               LISTEN      -                   
tcp        0      0 0.0.0.0:8000            0.0.0.0:*               LISTEN      3745/python3        
tcp6       0      0 :::9000                 :::*                    LISTEN      -                   

SERVICE_DIRECTORIES:
services
services/__pycache__
services/activeledger
services/ads
services/ai-orchestrator
services/ai-tools
services/ai_orchestrator
services/ambient
services/analytics
services/api-gateway
services/api_gateway
services/ar-layer
services/auth
services/backup
services/batch-import
services/biological
services/blockchain
services/cache
services/cognitive
services/collaboration
services/creative-suite
services/data-export
services/data-manager
services/dmlog-ai-dm
services/dmlog-battle
services/dmlog-characters
services/dmlog-converter
services/dmlog-core
services/dmlog-marketplace
services/dmlog-player
services/dmlog-session
services/dmlog-templates
services/dmlog-world
services/document-ai
services/education-ai
services/emotional-ai
services/file-sync
services/file-watcher
services/file_processor
services/gaming-platform
services/graphql
services/health-integration
services/manufacturing
services/marine-advanced
services/memory-preservation
services/metadata
services/ml-pipeline
services/mobile-api
services/multiverse
services/notification
services/notifications
services/p2p-sync
services/predictive
services/predictive-ai
services/quantum-ready
services/quantum-reality
services/security-advanced
services/simulation
services/smart-folders
services/social-ai
services/sync-engine
services/sync-v2
services/time-machine
services/universal-translator
services/video-pipeline
services/video-processor
services/workflows

SERVICE_CONFIGS:
./app-factory/base/package.json
./dev-tools/templates/service_templates/celery_worker/requirements.txt
./dev-tools/templates/service_templates/fastapi/Dockerfile
./dev-tools/templates/service_templates/fastapi/requirements.txt
./dev-tools/templates/service_templates/flask/requirements.txt
./dev-tools/templates/service_templates/grpc/requirements.txt
./docker-compose.yml
./docker/backend/Dockerfile
./docker/frontend/Dockerfile
./docker/ml-pipeline/Dockerfile
./docker/nginx/Dockerfile
./docker/postgres/Dockerfile
./frontend/Dockerfile
./frontend/package.json
./infrastructure/mesh/docker-compose.yml
./infrastructure/terraform/modules/lambda/lambda_code/requirements.txt
./modules/BusinessLog/package.json
./modules/DMLog/package.json
./modules/FishingLog/package.json
./modules/MakerLog/package.json
./modules/Marine/package.json
./modules/PlayerLog/package.json
./modules/RealLog/package.json
./modules/StudyLog/package.json
./modules/healthcare/requirements.txt
./monitoring/docker-compose.yml
./monitoring/performance-regression/Dockerfile
./monitoring/performance-regression/requirements.txt
./sdk/docs/requirements.txt
./sdk/marketplace/requirements.txt
./sdk/typescript/package.json
./security/audit/Dockerfile
./security/audit/docker-compose.yml
./security/audit/requirements.txt
./security/auth/docker-compose.yml
./security/scanning/docker-compose.yml
./security/secrets/Dockerfile
./security/secrets/docker-compose.yml
./security/secrets/requirements.txt
./services/activeledger/package.json
./services/activeledger/requirements.txt
./services/ai-orchestrator/requirements.txt
./services/ai_orchestrator/Dockerfile
./services/analytics/requirements.txt
./services/api-gateway/requirements.txt
./services/api_gateway/Dockerfile
./services/auth/Dockerfile
./services/auth/requirements.txt
./services/backup/requirements.txt
./services/batch-import/requirements.txt
./services/cache/requirements.txt
./services/collaboration/requirements.txt
./services/data-export/package.json
./services/data-export/requirements.txt
./services/dmlog-ai-dm/requirements.txt
./services/dmlog-battle/requirements.txt
./services/dmlog-characters/requirements.txt
./services/dmlog-converter/requirements.txt
./services/dmlog-core/Dockerfile
./services/dmlog-core/requirements.txt
./services/dmlog-marketplace/requirements.txt
./services/dmlog-player/requirements.txt
./services/dmlog-session/requirements.txt
./services/dmlog-templates/requirements.txt
./services/dmlog-world/requirements.txt
./services/document-ai/package.json
./services/document-ai/requirements.txt
./services/file-sync/requirements.txt
./services/file-watcher/Dockerfile
./services/file-watcher/docker-compose.yml
./services/file-watcher/requirements.txt
./services/file_processor/Dockerfile
./services/graphql/package.json
./services/metadata/Dockerfile
./services/metadata/requirements.txt
./services/ml-pipeline/Dockerfile
./services/ml-pipeline/docker-compose.yml
./services/ml-pipeline/requirements.txt
./services/mobile-api/package.json
./services/mobile-api/requirements.txt
./services/notification/Dockerfile
./services/notifications/requirements.txt
./services/predictive-ai/package.json
./services/smart-folders/requirements.txt
./services/sync-engine/requirements.txt
./services/sync-v2/requirements.txt
./services/video-pipeline/Dockerfile
./services/video-pipeline/docker-compose.yml
./services/video-pipeline/requirements.txt
./services/video-processor/Dockerfile
./services/video-processor/package.json
./services/video-processor/requirements.txt
./services/workflows/requirements.txt
./tests/requirements.txt
SERVICE_ANALYSIS_END

[0;32m=== 2. DEPENDENCIES ANALYSIS ===[0m
DEPENDENCIES_ANALYSIS_START
NODE_DEPENDENCIES:
=== ./services/graphql/package.json ===
{
  "name": "activelog-graphql-service",
  "version": "1.0.0",
  "description": "ActiveLog GraphQL Gateway Service",
  "main": "dist/server.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/server.js",
    "dev": "ts-node-dev --respawn --transpile-only src/server.ts",
    "test": "jest",
    "test:watch": "jest --watch",
    "lint": "eslint src/**/*.ts",
    "lint:fix": "eslint src/**/*.ts --fix",
    "typecheck": "tsc --noEmit",
    "generate-schema": "ts-node src/utils/generateSchema.ts",
    "introspect": "graphql-codegen --config codegen.yml"
  },
  "dependencies": {
    "@apollo/server": "^4.10.0",
    "@apollo/subgraph": "^2.6.0",
    "@apollo/federation": "^0.38.1",
    "@apollo/gateway": "^2.6.0",
    "apollo-server-express": "^3.12.1",
    "graphql": "^16.8.1",
    "graphql-subscriptions": "^2.0.0",
    "graphql-redis-subscriptions": "^2.6.0",
    "graphql-depth-limit": "^1.1.0",
    "graphql-query-complexity": "^0.12.0",
    "graphql-rate-limit": "^2.0.1",
    "dataloader": "^2.2.2",
    "express": "^4.18.2",
    "express-graphql": "^0.12.0",
    "graphql-playground-middleware-express": "^1.7.23",
    "ioredis": "^5.3.2",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "compression": "^1.7.4",
    "morgan": "^1.10.0",
    "winston": "^3.11.0",
    "dotenv": "^16.3.1",
    "pg": "^8.11.3",
    "pg-pool": "^3.6.1",
    "@types/pg": "^8.10.9",
    "axios": "^1.6.2",
    "jsonwebtoken": "^9.0.2",
    "bcryptjs": "^2.4.3",
    "uuid": "^9.0.1"
  },
  "devDependencies": {
    "@types/node": "^20.10.4",
    "@types/express": "^4.17.21",
    "@types/cors": "^2.8.17",
    "@types/compression": "^1.7.5",
    "@types/morgan": "^1.9.9",
    "@types/uuid": "^9.0.7",
    "@types/jsonwebtoken": "^9.0.5",
    "@types/bcryptjs": "^2.4.6",
    "@types/jest": "^29.5.8",
    "@typescript-eslint/eslint-plugin": "^6.13.1",
    "@typescript-eslint/parser": "^6.13.1",
    "eslint": "^8.54.0",
    "jest": "^29.7.0",
    "ts-jest": "^29.1.1",
    "ts-node": "^10.9.1",
    "ts-node-dev": "^2.0.0",
    "typescript": "^5.3.2",
    "@graphql-codegen/cli": "^5.0.0",
    "@graphql-codegen/typescript": "^4.0.1",
    "@graphql-codegen/typescript-resolvers": "^4.0.1",
    "graphql-tag": "^2.12.6"
  },
  "engines": {
    "node": ">=18.0.0"
  },
  "keywords": [
    "graphql",
    "apollo",
    "activelog",
    "api",
    "gateway"
  ],
  "author": "ActiveLog Team",
  "license": "MIT"
}=== ./services/activeledger/package.json ===
{
  "name": "@activelog/activeledger",
  "version": "1.0.0",
  "description": "Complete financial platform for ActiveLog - CC credits, payments, marketplace, compute rental, and enterprise billing",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "dev": "ts-node-dev src/index.ts",
    "start": "node dist/index.js",
    "test": "jest",
    "lint": "eslint src/**/*.ts"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "uuid": "^9.0.0",
    "date-fns": "^2.30.0",
    "lodash": "^4.17.21",
    "mongoose": "^7.5.0",
    "redis": "^4.6.7",
    "stripe": "^12.18.0",
    "paypal-rest-sdk": "^1.8.1",
    "google-pay-api": "^1.0.0",
    "node-cron": "^3.0.2",
    "decimal.js": "^10.4.3",
    "currency-converter-js": "^1.0.3",
    "jsonwebtoken": "^9.0.2",
    "bcryptjs": "^2.4.3",
    "joi": "^17.9.2",
    "winston": "^3.10.0",
    "aws-sdk": "^2.1424.0",
    "mailgun-js": "^0.22.0"
  },
  "devDependencies": {
    "@types/node": "^20.5.0",
    "@types/express": "^4.17.17",
    "@types/cors": "^2.8.13",
    "@types/uuid": "^9.0.2",
    "@types/lodash": "^4.14.195",
    "@types/paypal-rest-sdk": "^1.7.6",
    "@types/node-cron": "^3.0.8",
    "@types/jsonwebtoken": "^9.0.2",
    "@types/bcryptjs": "^2.4.2",
    "@types/joi": "^17.2.3",
    "typescript": "^5.1.6",
    "ts-node-dev": "^2.0.0",
    "jest": "^29.6.2",
    "@types/jest": "^29.5.3",
    "eslint": "^8.46.0",
    "@typescript-eslint/eslint-plugin": "^6.2.1",
    "@typescript-eslint/parser": "^6.2.1"
  },
  "keywords": ["financial", "payments", "credits", "marketplace", "compute", "billing"]
}=== ./services/data-export/package.json ===
{
  "name": "data-export-service",
  "version": "1.0.0",
  "description": "Comprehensive data export service with multiple format support and cloud integration",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "dev": "nodemon src/server.js",
    "test": "jest",
    "lint": "eslint src/",
    "clean": "rimraf temp/* output/*"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "morgan": "^1.10.0",
    "multer": "^1.4.5-lts.1",
    "winston": "^3.11.0",
    "dotenv": "^16.3.1",
    "joi": "^17.11.0",
    "uuid": "^9.0.1",
    "fs-extra": "^11.1.1",
    "archiver": "^6.0.1",
    "tar": "^6.2.0",
    "pdfkit": "^0.13.0",
    "puppeteer": "^21.5.2",
    "handlebars": "^4.7.8",
    "sharp": "^0.32.6",
    "exif-reader": "^2.0.1",
    "piexifjs": "^1.0.6",
    "html-pdf": "^3.0.1",
    "moment": "^2.29.4",
    "mime-types": "^2.1.35",
    "progress": "^2.0.3",
    "socket.io": "^4.7.4",
    "googleapis": "^128.0.0",
    "dropbox": "^10.34.0",
    "aws-sdk": "^2.1496.0",
    "crypto": "^1.0.1",
    "xml2js": "^0.6.2",
    "csv-writer": "^1.6.0",
    "xlsx": "^0.18.5",
    "sanitize-filename": "^1.6.3",
    "node-cron": "^3.0.3",
    "compression": "^1.7.4",
    "rate-limiter-flexible": "^4.0.1"
  },
  "devDependencies": {
    "nodemon": "^3.0.1",
    "jest": "^29.7.0",
    "supertest": "^6.3.3",
    "eslint": "^8.52.0",
    "rimraf": "^5.0.5"
  },
  "keywords": [
    "export",
    "pdf",
    "zip",
    "archive",
    "website-generator",
    "photo-book",
    "gdpr",
    "cloud-storage",
    "bulk-export"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./services/predictive-ai/package.json ===
{
  "name": "@activelog/predictive-ai",
  "version": "1.0.0",
  "description": "Predictive AI service for ActiveLog - learns user patterns and predicts future needs",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "dev": "ts-node-dev src/index.ts",
    "start": "node dist/index.js",
    "test": "jest",
    "lint": "eslint src/**/*.ts"
  },
  "dependencies": {
    "@tensorflow/tfjs-node": "^4.10.0",
    "brain.js": "^2.0.0-beta.2",
    "ml-matrix": "^6.10.4",
    "ml-kmeans": "^6.0.0",
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "uuid": "^9.0.0",
    "date-fns": "^2.30.0",
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "@types/node": "^20.5.0",
    "@types/express": "^4.17.17",
    "@types/cors": "^2.8.13",
    "@types/uuid": "^9.0.2",
    "@types/lodash": "^4.14.195",
    "typescript": "^5.1.6",
    "ts-node-dev": "^2.0.0",
    "jest": "^29.6.2",
    "@types/jest": "^29.5.3",
    "eslint": "^8.46.0",
    "@typescript-eslint/eslint-plugin": "^6.2.1",
    "@typescript-eslint/parser": "^6.2.1"
  },
  "keywords": ["ai", "prediction", "machine-learning", "activelog"]
}=== ./services/document-ai/package.json ===
{
  "name": "document-ai",
  "version": "1.0.0",
  "description": "AI-powered document processing service with classification, NER, summarization, and semantic search",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "dev": "nodemon src/server.js",
    "test": "jest",
    "test:watch": "jest --watch",
    "python:install": "pip install -r requirements.txt",
    "setup": "npm install && npm run python:install"
  },
  "dependencies": {
    "express": "^4.18.2",
    "multer": "^1.4.5-lts.1",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "compression": "^1.7.4",
    "dotenv": "^16.3.1",
    "winston": "^3.11.0",
    "uuid": "^9.0.1",
    "axios": "^1.6.0",
    "form-data": "^4.0.0",
    "pdf-parse": "^1.1.1",
    "pdf2pic": "^2.1.4",
    "sharp": "^0.32.6",
    "mammoth": "^1.6.0",
    "xlsx": "^0.18.5",
    "cheerio": "^1.0.0-rc.12",
    "node-schedule": "^2.1.1",
    "ioredis": "^5.3.2",
    "pg": "^8.11.3",
    "sqlite3": "^5.1.6",
    "sequelize": "^6.35.1",
    "chroma-js": "^2.4.2",
    "compromise": "^14.10.0",
    "natural": "^6.10.0",
    "franc": "^6.0.0",
    "langdetect": "^0.2.1",
    "node-tesseract-ocr": "^2.2.1",
    "jimp": "^0.22.10",
    "puppeteer": "^21.6.0"
  },
  "devDependencies": {
    "nodemon": "^3.0.1",
    "jest": "^29.7.0",
    "supertest": "^6.3.3",
    "@types/jest": "^29.5.8"
  },
  "engines": {
    "node": ">=16.0.0"
  },
  "keywords": [
    "document",
    "ai",
    "ocr",
    "pdf",
    "classification",
    "ner",
    "summarization",
    "semantic-search",
    "nlp"
  ]
}=== ./services/mobile-api/package.json ===
{
  "name": "activelog-mobile-api",
  "version": "1.0.0",
  "description": "ActiveLog Mobile-Optimized API Service",
  "main": "dist/server.js",
  "scripts": {
    "build": "npm run build:proto && tsc",
    "build:proto": "node scripts/build-proto.js",
    "start": "node dist/server.js",
    "dev": "npm run build:proto && ts-node-dev --respawn --transpile-only src/server.ts",
    "test": "jest",
    "test:watch": "jest --watch",
    "lint": "eslint src/**/*.ts",
    "lint:fix": "eslint src/**/*.ts --fix",
    "typecheck": "tsc --noEmit",
    "proto:compile": "pbjs -t static-module -w es6 -o src/protobuf/compiled.js proto/*.proto && pbts -o src/protobuf/compiled.d.ts src/protobuf/compiled.js",
    "proto:watch": "nodemon --watch proto --ext proto --exec \"npm run proto:compile\"",
    "docker:build": "docker build -t activelog-mobile-api .",
    "docker:run": "docker run -p 8011:8011 activelog-mobile-api"
  },
  "dependencies": {
    "express": "^4.18.2",
    "express-rate-limit": "^7.1.5",
    "helmet": "^7.1.0",
    "cors": "^2.8.5",
    "compression": "^1.7.4",
    "morgan": "^1.10.0",
    "dotenv": "^16.3.1",
    "protobufjs": "^7.2.5",
    "ioredis": "^5.3.2",
    "jsonwebtoken": "^9.0.2",
    "bcryptjs": "^2.4.3",
    "uuid": "^9.0.1",
    "multer": "^1.4.5-lts.1",
    "sharp": "^0.33.1",
    "node-firebase-admin": "^1.0.3",
    "node-apn": "^2.2.0",
    "ws": "^8.14.2",
    "zlib": "^1.0.5",
    "lru-cache": "^10.1.0",
    "ioredis-lock": "^4.2.0",
    "cron": "^3.1.6",
    "axios": "^1.6.2",
    "form-data": "^4.0.0",
    "mime-types": "^2.1.35",
    "file-type": "^18.7.0",
    "image-size": "^1.0.2",
    "express-slow-down": "^2.0.1",
    "express-brute": "^1.0.1",
    "express-validator": "^7.0.1"
  },
  "devDependencies": {
    "@types/node": "^20.10.4",
    "@types/express": "^4.17.21",
    "@types/cors": "^2.8.17",
    "@types/compression": "^1.7.5",
    "@types/morgan": "^1.9.9",
    "@types/uuid": "^9.0.7",
    "@types/jsonwebtoken": "^9.0.5",
    "@types/bcryptjs": "^2.4.6",
    "@types/multer": "^1.4.11",
    "@types/ws": "^8.5.10",
    "@types/mime-types": "^2.1.4",
    "@types/jest": "^29.5.8",
    "@typescript-eslint/eslint-plugin": "^6.13.1",
    "@typescript-eslint/parser": "^6.13.1",
    "eslint": "^8.54.0",
    "jest": "^29.7.0",
    "ts-jest": "^29.1.1",
    "ts-node": "^10.9.1",
    "ts-node-dev": "^2.0.0",
    "typescript": "^5.3.2",
    "nodemon": "^3.0.2",
    "supertest": "^6.3.3",
    "@types/supertest": "^6.0.2"
  },
  "engines": {
    "node": ">=18.0.0"
  },
  "keywords": [
    "mobile-api",
    "protobuf",
    "push-notifications",
    "offline-sync",
    "activelog",
    "optimization"
  ],
  "author": "ActiveLog Team",
  "license": "MIT"
}=== ./services/video-processor/package.json ===
{
  "name": "video-processor",
  "version": "1.0.0",
  "description": "Video analysis service with keyframe extraction, scene detection, OCR, and AI summaries",
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "dev": "nodemon src/server.js",
    "test": "jest",
    "test:watch": "jest --watch"
  },
  "dependencies": {
    "express": "^4.18.2",
    "multer": "^1.4.5-lts.1",
    "opencv4nodejs": "^5.6.0",
    "node-tesseract-ocr": "^2.2.1",
    "fluent-ffmpeg": "^2.1.2",
    "ws": "^8.14.2",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "compression": "^1.7.4",
    "dotenv": "^16.3.1",
    "winston": "^3.11.0",
    "uuid": "^9.0.1",
    "sharp": "^0.32.6",
    "node-schedule": "^2.1.1",
    "axios": "^1.6.0",
    "form-data": "^4.0.0",
    "stream-buffers": "^3.0.2"
  },
  "devDependencies": {
    "nodemon": "^3.0.1",
    "jest": "^29.7.0",
    "supertest": "^6.3.3"
  },
  "engines": {
    "node": ">=16.0.0"
  },
  "keywords": [
    "video",
    "analysis",
    "opencv",
    "ocr",
    "ai",
    "keyframes",
    "thumbnails",
    "scene-detection"
  ]
}=== ./modules/BusinessLog/package.json ===
{
  "name": "business-log",
  "version": "1.0.0",
  "description": "Receipt OCR, automatic tax categorization, and payroll automation for business operations",
  "main": "index.js",
  "dependencies": {
    "tesseract.js": "^4.1.1",
    "sharp": "^0.32.0",
    "moment": "^2.29.4",
    "node-nlp": "^4.26.1"
  },
  "keywords": [
    "business",
    "ocr",
    "receipts",
    "tax",
    "payroll",
    "automation"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./modules/FishingLog/package.json ===
{
  "name": "fishing-log",
  "version": "1.0.0",
  "description": "NMEA data integration, fish counting CV, and Coast Guard compliance for fishing activities",
  "main": "index.js",
  "dependencies": {
    "nmea-simple": "^1.1.0",
    "opencv4nodejs": "^5.6.0",
    "node-fetch": "^3.3.0"
  },
  "keywords": [
    "fishing",
    "nmea",
    "computer-vision",
    "coast-guard",
    "compliance"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./modules/RealLog/package.json ===
{
  "name": "real-log",
  "version": "1.0.0",
  "description": "Multi-camera sync, collaborative editing, and broadcast tools for video production",
  "main": "index.js",
  "dependencies": {
    "ffmpeg": "^0.0.4",
    "node-rtmp-stream": "^0.0.4",
    "socket.io": "^4.7.2",
    "obs-websocket-js": "^5.0.3",
    "node-media-server": "^2.6.1"
  },
  "keywords": [
    "video",
    "broadcast",
    "streaming",
    "editing",
    "collaboration"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./modules/DMLog/package.json ===
{
  "name": "dm-log",
  "version": "1.0.0",
  "description": "Character sheets, dice rolling, and campaign management for tabletop RPG games",
  "main": "index.js",
  "dependencies": {
    "express": "^4.18.2",
    "socket.io": "^4.7.2",
    "mongoose": "^7.5.0",
    "bcrypt": "^5.1.1",
    "jsonwebtoken": "^9.0.2"
  },
  "keywords": [
    "rpg",
    "dnd",
    "tabletop",
    "dice",
    "character-sheet",
    "campaign"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./modules/Marine/package.json ===
{
  "name": "marine",
  "version": "1.0.0",
  "description": "OpenCPN integration, AIS tracking, and weather routing for marine navigation",
  "main": "index.js",
  "dependencies": {
    "serialport": "^10.5.0",
    "net": "^1.0.2",
    "node-fetch": "^3.3.0",
    "grib2-simple": "^1.0.2",
    "ais-stream": "^2.1.0"
  },
  "keywords": [
    "marine",
    "navigation",
    "opencpn",
    "ais",
    "weather",
    "routing"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./modules/MakerLog/package.json ===
{
  "name": "maker-log",
  "version": "1.0.0",
  "description": "CAD file preview, component sourcing, and assembly instructions for maker projects",
  "main": "index.js",
  "dependencies": {
    "three": "^0.155.0",
    "opencascade.js": "^2.0.0-beta.2",
    "puppeteer": "^20.7.2",
    "cheerio": "^1.0.0-rc.12",
    "pdf2pic": "^2.1.4"
  },
  "keywords": [
    "maker",
    "cad",
    "3d",
    "assembly",
    "electronics",
    "sourcing"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./modules/PlayerLog/package.json ===
{
  "name": "player-log",
  "version": "1.0.0",
  "description": "Game-specific overlays, opponent analysis, and replay system for gaming activities",
  "main": "index.js",
  "dependencies": {
    "electron": "^25.3.1",
    "obs-websocket-js": "^5.0.3",
    "ffmpeg": "^0.0.4",
    "canvas": "^2.11.2",
    "node-window-manager": "^2.2.4"
  },
  "keywords": [
    "gaming",
    "overlay",
    "analysis",
    "replay",
    "esports"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./modules/StudyLog/package.json ===
{
  "name": "study-log",
  "version": "1.0.0",
  "description": "Progress tracking, assignment management, and parent portal for educational activities",
  "main": "index.js",
  "dependencies": {
    "chart.js": "^4.2.1",
    "express": "^4.18.2",
    "socket.io": "^4.7.2",
    "mongoose": "^7.5.0"
  },
  "keywords": [
    "education",
    "study",
    "progress",
    "assignments",
    "parent-portal"
  ],
  "author": "ActiveLog",
  "license": "MIT"
}=== ./sdk/typescript/package.json ===
{
  "name": "@activelog/plugin-sdk",
  "version": "1.0.0",
  "description": "ActiveLog Plugin SDK for TypeScript",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "test": "jest",
    "lint": "eslint src/**/*.ts",
    "docs": "typedoc src/index.ts"
  },
  "keywords": [
    "activelog",
    "plugin",
    "sdk",
    "typescript"
  ],
  "author": "ActiveLog Team",
  "license": "MIT",
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/jest": "^29.5.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "eslint": "^8.45.0",
    "jest": "^29.6.0",
    "ts-jest": "^29.1.0",
    "typedoc": "^0.24.0",
    "typescript": "^5.1.0"
  },
  "dependencies": {
    "axios": "^1.4.0",
    "eventemitter3": "^5.0.1",
    "zod": "^3.21.4"
  },
  "files": [
    "dist/**/*",
    "README.md"
  ],
  "repository": {
    "type": "git",
    "url": "https://github.com/activelog/plugin-sdk"
  },
  "engines": {
    "node": ">=18.0.0"
  }
}=== ./frontend/package.json ===
{
  "name": "activelog-frontend",
  "version": "1.0.0",
  "description": "ActiveLog.ai Frontend Application",
  "main": "index.html",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "serve": "http-server dist -p 3000"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "http-server": "^14.1.1"
  },
  "dependencies": {
    "lucide": "^0.263.1",
    "@tanstack/virtual-core": "^3.0.0",
    "recharts": "^2.10.0",
    "sortablejs": "^1.15.0",
    "fuse.js": "^7.0.0",
    "pdf-lib": "^1.17.1",
    "file-saver": "^2.0.5",
    "canvas-confetti": "^1.9.2"
  }
}=== ./app-factory/base/package.json ===
{
  "name": "activelog-base-template",
  "version": "1.0.0",
  "description": "Base template for all ActiveLog.ai applications",
  "main": "index.html",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "serve": "http-server dist -p 3000",
    "build:app": "node ../build/app-builder.js"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "http-server": "^14.1.1"
  },
  "dependencies": {
    "lucide": "^0.263.1",
    "@tanstack/virtual-core": "^3.0.0",
    "recharts": "^2.10.0",
    "sortablejs": "^1.15.0",
    "fuse.js": "^7.0.0",
    "pdf-lib": "^1.17.1",
    "file-saver": "^2.0.5",
    "canvas-confetti": "^1.9.2"
  }
}
PYTHON_DEPENDENCIES:
=== ./monitoring/performance-regression/requirements.txt ===
requests==2.31.0
pandas==2.1.4
numpy==1.25.2
scipy==1.11.4
PyYAML==6.0.1
prometheus-client==0.19.0=== ./services/sync-v2/requirements.txt ===
# Core dependencies
asyncio
websockets>=11.0.0
aiohttp>=3.8.0
dataclasses
typing-extensions
hashlib
json
logging
time
uuid
pathlib
enum
datetime

# Optional dependencies for enhanced features
pybluez>=0.23  # Bluetooth support
wifi>=0.3.8    # WiFi scanning
redis>=4.5.0   # Distributed collaboration
prometheus-client>=0.16.0  # Monitoring and metrics

# Development dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0=== ./services/activeledger/requirements.txt ===
# ActiveLedger Financial Platform Requirements

# Core Framework
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
alembic==1.12.1

# Database
psycopg2-binary==2.9.9
redis==5.0.1

# Payment Gateways
paypal-api==1.0.0
google-pay-token-decryption==1.0.2
stripe==7.8.0

# Financial & Currency
forex-python==1.8
currencyapicom==1.0.0
babel==2.13.1

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# API & HTTP
httpx==0.25.2
aiohttp==3.9.1
requests==2.31.0

# Data Processing
pandas==2.1.4
numpy==1.24.4
python-decimal==0.1.0

# Background Tasks
celery==5.3.4
kombu==5.3.4

# Monitoring & Logging
prometheus-client==0.19.0
structlog==23.2.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Development
black==23.11.0
isort==5.12.0
mypy==1.7.1=== ./services/api-gateway/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.2
PyJWT==2.8.0
redis==5.0.1
python-multipart==0.0.6=== ./services/dmlog-ai-dm/requirements.txt ===
# AI DM Assistant Requirements

# Core framework
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.4.0

# AI and ML
openai>=1.3.0
langchain>=0.0.350
tiktoken>=0.5.0
numpy>=1.24.0
scikit-learn>=1.3.0

# Data processing
pandas>=2.1.0
python-multipart>=0.0.6

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0
sqlite3

# Utilities
python-dateutil>=2.8.0
asyncio
logging
json
yaml
enum34
typing-extensions>=4.8.0

# Session and state management
redis>=5.0.0
websockets>=11.0.0

# Natural language processing
spacy>=3.7.0
nltk>=3.8.0

# Scheduling and timing
apscheduler>=3.10.0

# Configuration management
python-dotenv>=1.0.0
pyyaml>=6.0

# Development
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.9.0
flake8>=6.1.0=== ./services/dmlog-session/requirements.txt ===
# Core web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
jinja2==3.1.2

# Database and ORM
sqlalchemy==2.0.23
alembic==1.13.1
psycopg2-binary==2.9.9

# Data validation and serialization
pydantic==2.5.0
pydantic-settings==2.1.0

# Audio processing and recording
pyaudio==0.2.11
librosa==0.10.1
soundfile==0.12.1
webrtcvad==2.0.10
numpy==1.24.3

# Speech recognition and transcription
speechrecognition==3.10.0
openai-whisper==20231117
torch==2.1.1
torchaudio==2.1.1

# Audio analysis for speaker identification
pyannote.audio==3.1.1
speechbrain==0.5.16

# Text processing and NLP
spacy==3.7.2
transformers==4.36.2
nltk==3.8.1

# File handling and multimedia
pillow==10.1.0
opencv-python==4.8.1.78
mutagen==1.47.0

# WebSocket for real-time features
websockets==11.0.3
python-socketio==5.10.0

# Scheduling and calendar
python-dateutil==2.8.2
icalendar==5.0.11
croniter==2.0.1

# PDF generation and document handling
reportlab==4.0.7
pypdf2==3.0.1
markdown==3.5.1

# Real-time collaboration
redis==5.0.1
celery==5.3.4

# Authentication and security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-oauth2==1.1.1

# HTTP requests and external APIs
httpx==0.25.2
requests==2.31.0

# Data analysis and visualization
pandas==2.1.4
matplotlib==3.8.2
seaborn==0.13.0

# WebRTC for real-time audio
aiortc==1.6.0

# Background tasks
apscheduler==3.10.4

# Configuration management
python-dotenv==1.0.0
pyyaml==6.0.1

# Logging and monitoring
structlog==23.2.0
sentry-sdk==1.38.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2=== ./services/dmlog-templates/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
jinja2==3.1.2
aiofiles==23.2.1
pyyaml==6.0.1
numpy==1.24.3
random-word==1.0.11
names==0.3.0
wonderwords==2.2.0
markovify==0.9.4
textblob==0.17.1=== ./services/workflows/requirements.txt ===
# ActiveLog Workflows Service Dependencies

# FastAPI and async support
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
databases[postgresql]==0.8.0
sqlalchemy==2.0.23
alembic==1.12.1
asyncpg==0.29.0

# Redis for caching and job queues
redis==5.0.1
aioredis==2.0.1

# Task scheduling
celery==5.3.4
croniter==2.0.1
apscheduler==3.10.4

# HTTP clients and webhooks
httpx==0.25.2
requests==2.31.0

# Data validation and serialization
pydantic==2.5.0
pydantic-settings==2.1.0

# Authentication and security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# Workflow execution engine
jinja2==3.1.2
jsonpath-ng==1.6.0
jsonschema==4.20.0

# External service integrations
stripe==7.8.0
slack-sdk==3.26.1
boto3==1.34.0
google-api-python-client==2.110.0
twilio==8.12.0

# Monitoring and logging
prometheus-client==0.19.0
structlog==23.2.0

# Development and testing
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
ruff==0.1.6=== ./services/dmlog-core/requirements.txt ===
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
alembic==1.12.1
python-multipart==0.0.6
jinja2==3.1.2
python-jose==3.3.0
passlib==1.7.4
bcrypt==4.1.1
aiofiles==23.2.1
httpx==0.25.2
redis==5.0.1
celery==5.3.4
numpy==1.25.2
fuzzywuzzy==0.18.0
python-levenshtein==0.23.0
networkx==3.2.1
matplotlib==3.8.2
pillow==10.1.0
scipy==1.11.4
dateutils==0.6.12
pyyaml==6.0.1
python-dotenv==1.0.0
psycopg2-binary==2.9.9=== ./services/data-export/requirements.txt ===
# FastAPI and server dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
alembic==1.12.1
asyncpg==0.29.0
databases[postgresql]==0.8.0

# Export formats
reportlab==4.0.7          # PDF generation
PyPDF2==3.0.1             # PDF manipulation
Pillow==10.1.0             # Image processing
jinja2==3.1.2              # Template rendering
markdown==3.5.1           # Markdown processing

# Archive creation
zipfile-ng==0.1.0

# Cloud providers
google-api-python-client==2.108.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0
dropbox==11.36.2
boto3==1.34.0              # AWS S3

# Progress tracking and async
celery[redis]==5.3.4
redis==5.0.1
aiofiles==23.2.1
aiohttp==3.9.1

# Data processing
pandas==2.1.4
openpyxl==3.1.2           # Excel export
xlsxwriter==3.1.9

# Metadata and EXIF
exifread==3.0.0
piexif==1.1.3

# Authentication and security
pyjwt==2.8.0
cryptography==41.0.8
bcrypt==4.1.2

# Utilities
python-magic==0.4.27      # File type detection
python-dateutil==2.8.2
pydantic==2.5.0
pydantic-settings==2.1.0
structlog==23.2.0
rich==13.7.0              # Rich console output

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Development
black==23.11.0
isort==5.12.0
flake8==6.1.0=== ./services/file-sync/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
redis==5.0.1
minio==7.2.0
python-multipart==0.0.6
=== ./services/dmlog-characters/requirements.txt ===
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-multipart==0.0.6

# AI and ML libraries
transformers==4.36.0
torch==2.1.0
torchaudio==2.1.0
numpy==1.24.3
scipy==1.11.4

# Voice synthesis and processing
TTS==0.18.0
pydub==0.25.1
librosa==0.10.1
soundfile==0.12.1
espeak-ng==1.0.2

# Image generation and processing
Pillow==10.1.0
diffusers==0.21.4
accelerate==0.24.1

# Text processing and NLP
spacy==3.7.2
nltk==3.8.1
textblob==0.17.1

# Database and storage
psycopg2-binary==2.9.9
redis==5.0.1

# Utilities
python-dotenv==1.0.0
requests==2.31.0
aiofiles==23.2.0
jinja2==3.1.2=== ./services/backup/requirements.txt ===
# ActiveLog Backup Service Dependencies

# FastAPI and ASGI server
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database
asyncpg==0.29.0

# Redis for job queues
redis==5.0.1
aioredis==2.0.1

# S3 and cloud storage
boto3==1.34.0
botocore==1.34.0

# File operations and async I/O
aiofiles==23.2.1

# Cryptography for encryption
cryptography==41.0.7

# System utilities
psutil==5.9.6

# Scheduling
croniter==2.0.1

# HTTP client for webhooks
aiohttp==3.9.1
httpx==0.25.2

# Configuration and validation
pydantic==2.5.0
pydantic-settings==2.1.0

# Environment variables
python-dotenv==1.0.0

# Date/time handling
python-dateutil==2.8.2

# JSON handling
orjson==3.9.10

# Development and testing
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
flake8==6.1.0
mypy==1.7.1

# Optional: Additional cloud providers
# google-cloud-storage==2.10.0  # Google Cloud Storage
# azure-storage-blob==12.19.0   # Azure Blob Storage=== ./services/document-ai/requirements.txt ===
# FastAPI and web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Async and HTTP
aiofiles==23.2.1
aiohttp==3.9.1
asyncpg==0.29.0

# PDF and document processing
PyPDF2==3.0.1
pdfplumber==0.10.3
PyMuPDF==1.23.9
python-docx==1.1.0

# OCR
pytesseract==0.3.10
Pillow==10.1.0

# Table extraction
camelot-py[cv]==0.11.0
tabula-py==2.8.2
pandas==2.1.3

# Computer vision
opencv-python==4.8.1.78
numpy==1.24.4

# NLP and AI
spacy==3.7.2
transformers==4.35.2
torch==2.1.1
sentence-transformers==2.2.2
scikit-learn==1.3.2

# Language and text processing
langdetect==1.0.9
dateutil==2.8.2
phonenumbers==8.13.24
email-validator==2.1.0

# Vector databases
chromadb==0.4.17
pinecone-client==2.2.4
weaviate-client==3.25.3

# AI APIs
openai==1.3.7
anthropic==0.7.8

# Data validation and configuration
pydantic==2.5.0
pydantic-settings==2.1.0

# Development
pytest==7.4.3
pytest-asyncio==0.21.1=== ./services/video-pipeline/requirements.txt ===
# Video Processing Pipeline Requirements

# Core FastAPI and web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database and storage
asyncpg==0.29.0
SQLAlchemy==2.0.23
alembic==1.12.1
redis==5.0.1
minio==7.2.0
elasticsearch==8.11.0

# Message queues
nats-py==2.6.0
celery==5.3.4

# Video processing
opencv-python==4.8.1.78
ffmpeg-python==0.2.0
pillow==10.1.0
imageio[ffmpeg]==2.33.0

# AI and ML
torch==2.1.1
torchvision==0.16.1
transformers==4.36.2
sentence-transformers==2.2.2
openai==1.3.7
whisper==1.1.10

# Audio processing
librosa==0.10.1
soundfile==0.12.1
pydub==0.25.1

# OCR and text processing
pytesseract==0.3.10
easyocr==1.7.0
spacy==3.7.2

# Computer Vision
scikit-image==0.22.0
moviepy==1.0.3

# Utilities
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
python-dotenv==1.0.0
structlog==23.2.0
prometheus-client==0.19.0

# Development and testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
black==23.11.0
flake8==6.1.0
mypy==1.7.1

# Monitoring and observability
sentry-sdk[fastapi]==1.38.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0=== ./services/batch-import/requirements.txt ===
# ActiveLog Batch Import Service Dependencies

# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Async support
asyncio-mqtt==0.16.1
aiofiles==23.2.1

# Configuration and validation
pydantic[email]==2.5.0
python-dotenv==1.0.0

# File monitoring
watchdog==3.0.0

# Object Storage
minio==7.2.0

# Database connectivity
psycopg2-binary==2.9.7

# Image processing
Pillow==10.1.0

# Video processing (for thumbnails)
ffmpeg-python==0.2.0

# Audio metadata
mutagen==1.47.0

# Document processing
PyPDF2==3.0.1
python-docx==1.1.0
openpyxl==3.1.2

# File type detection
python-magic==0.4.27
filetype==1.2.0

# HTTP requests
requests==2.31.0

# Logging
structlog==23.2.0

# Date handling
python-dateutil==2.8.2

# Security
cryptography==41.0.7

# Development tools
pytest==7.4.3
pytest-asyncio==0.21.1

# Optional OCR support
# pytesseract==0.3.10  # Uncomment if OCR is needed

# Optional language detection
# langdetect==1.0.9   # Uncomment if language detection is needed=== ./services/dmlog-battle/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
requests==2.31.0
httpx==0.25.2

# Mathematical and scientific computing
numpy==1.24.3
scipy==1.11.4

# Graph algorithms for pathfinding and LOS
networkx==3.2.1

# Image processing for battlefield visualization
Pillow==10.1.0
opencv-python==4.8.1.78
matplotlib==3.8.2

# Data serialization
pyyaml==6.0.1
toml==0.10.2

# Performance optimization
numba==0.58.1

# Random number generation
python-random==1.0.1=== ./services/metadata/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic[email]==2.5.0
psycopg2-binary==2.9.9
elasticsearch==8.11.0
httpx==0.25.2
python-multipart==0.0.6
pgvector==0.2.4=== ./services/dmlog-player/requirements.txt ===
# Player Interface Requirements

# Core framework
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.4.0

# Database and data handling
sqlalchemy>=2.0.0
sqlite3
alembic>=1.12.0

# Date and time handling
python-dateutil>=2.8.0

# Text processing
python-multipart>=0.0.6
jinja2>=3.1.0

# Configuration
pyyaml>=6.0
python-dotenv>=1.0.0

# Mathematical calculations
numpy>=1.24.0

# Security
passlib>=1.7.0
python-jose>=3.3.0
bcrypt>=4.0.0

# Development and testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.9.0
flake8>=6.1.0

# Frontend (if needed)
jinja2>=3.1.0
starlette>=0.27.0=== ./services/mobile-api/requirements.txt ===
# Mobile API Service Dependencies

# Core FastAPI and async support
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
httpx==0.25.2

# Database
asyncpg==0.29.0
databases[postgresql]==0.8.0
sqlalchemy[asyncio]==2.0.23
alembic==1.12.1

# Protocol Buffers
protobuf==4.25.1
grpcio==1.60.0
grpcio-tools==1.60.0

# Redis for caching and pub/sub
redis[hiredis]==5.0.1
aioredis==2.0.1

# Push notifications
aioapns==3.0
pyfcm==1.5.4
py-vapid==1.9.0

# Image optimization
Pillow==10.1.0
pillow-simd==10.0.1.post1
opencv-python-headless==4.8.1.78
imageio==2.31.6

# Compression and serialization
lz4==4.3.2
brotli==1.1.0
msgpack==1.0.7
orjson==3.9.10

# Cryptography and security
cryptography==41.0.7
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
python-multipart==0.0.6

# Mobile optimization
user-agents==2.2.0
mobile-detect==0.1.2

# Monitoring and logging
structlog==23.2.0
prometheus-client==0.19.0
sentry-sdk[fastapi]==1.38.0

# Utils
python-dotenv==1.0.0
pydantic[email]==2.5.0
pydantic-settings==2.1.0
tenacity==8.2.3
schedule==1.2.0

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1=== ./services/dmlog-marketplace/requirements.txt ===
# Marketplace Requirements

# Core framework
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.4.0

# Database and data handling
sqlalchemy>=2.0.0
alembic>=1.12.0
redis>=5.0.0

# File handling and storage
boto3>=1.26.0  # AWS S3 for file storage
pillow>=10.0.0  # Image processing
python-multipart>=0.0.6

# Payment processing
stripe>=6.0.0
paypal-rest-sdk>=1.13.0

# Security and authentication
passlib>=1.7.0
python-jose>=3.3.0
bcrypt>=4.0.0
cryptography>=41.0.0

# API and networking
httpx>=0.24.0
websockets>=11.0.0

# Data processing
pandas>=2.1.0
numpy>=1.24.0

# Configuration and utilities
pyyaml>=6.0.0
python-dotenv>=1.0.0
python-dateutil>=2.8.0

# Email and notifications
celery>=5.3.0
flower>=2.0.0
sendgrid>=6.10.0

# Search and indexing
elasticsearch>=8.9.0
whoosh>=2.7.0

# Content processing
markdown>=3.5.0
bleach>=6.0.0

# Development and testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.9.0
flake8>=6.1.0

# Monitoring and logging
prometheus-client>=0.17.0
structlog>=23.1.0=== ./services/collaboration/requirements.txt ===
# ActiveLog Collaboration Service Dependencies

# FastAPI and async support
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
websockets==12.0

# Database
databases[postgresql]==0.8.0
sqlalchemy==2.0.23
alembic==1.12.1
asyncpg==0.29.0

# Redis for real-time features
redis==5.0.1
aioredis==2.0.1

# Real-time communication
python-socketio==5.10.0
python-engineio==4.7.1

# File handling and storage
aiofiles==23.2.1
python-magic==0.4.27
pillow==10.1.0

# Data validation and serialization
pydantic==2.5.0
pydantic-settings==2.1.0

# Authentication and security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# Date and time handling
python-dateutil==2.8.2
pytz==2023.3

# Document processing
python-docx==1.1.0
PyPDF2==3.0.1
openpyxl==3.1.2

# Version control
GitPython==3.1.40
diff-match-patch==20230430

# Text processing and search
whoosh==2.7.4
nltk==3.8.1
textdistance==4.6.2

# Monitoring and logging
prometheus-client==0.19.0
structlog==23.2.0

# Development and testing
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
ruff==0.1.6=== ./services/dmlog-converter/requirements.txt ===
# System Converter Requirements

# Core framework
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.4.0

# Data processing and validation
pandas>=2.1.0
numpy>=1.24.0
scikit-learn>=1.3.0

# Math and statistics
scipy>=1.11.0
sympy>=1.12.0

# Text processing and parsing
python-multipart>=0.0.6
regex>=2023.10.0
pyparsing>=3.1.0

# Configuration and serialization
pyyaml>=6.0
toml>=0.10.0
json5>=0.9.0

# Database and caching
sqlalchemy>=2.0.0
redis>=5.0.0

# Utilities
python-dateutil>=2.8.0
typing-extensions>=4.8.0
enum34
dataclasses-json>=0.6.0

# Mathematical expression parsing
ast
operator

# Validation and testing
marshmallow>=3.20.0
jsonschema>=4.19.0

# Development tools
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.9.0
flake8>=6.1.0

# Documentation
markdown>=3.5.0=== ./services/ml-pipeline/requirements.txt ===
# Core ML Libraries
torch>=2.0.0
transformers>=4.30.0
sentence-transformers>=2.2.0
scikit-learn>=1.3.0
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0

# Deep Learning & Neural Networks
pytorch-lightning>=2.0.0
torchvision>=0.15.0
accelerate>=0.20.0
datasets>=2.12.0

# MLflow & Experiment Tracking
mlflow>=2.4.0
mlflow[extras]>=2.4.0

# Celery & Task Queue
celery>=5.3.0
redis>=4.5.0
flower>=2.0.0

# FastAPI & Web Framework
fastapi>=0.100.0
uvicorn>=0.22.0
pydantic>=2.0.0
sqlalchemy>=2.0.0
alembic>=1.11.0

# Data Processing & Feature Engineering
feature-engine>=1.6.0
optuna>=3.2.0
hyperopt>=0.2.7
bayesian-optimization>=1.4.0

# Model Serving & Deployment
bentoml>=1.1.0
onnx>=1.14.0
onnxruntime>=1.15.0

# Utilities & Monitoring
wandb>=0.15.0
tensorboard>=2.13.0
psutil>=5.9.0
tqdm>=4.65.0
rich>=13.4.0
typer>=0.9.0

# Database & Storage
psycopg2-binary>=2.9.0
pymongo>=4.4.0
boto3>=1.26.0
minio>=7.1.0

# Configuration & Serialization
pyyaml>=6.0
python-dotenv>=1.0.0
joblib>=1.3.0
pickle5>=0.0.12
cloudpickle>=2.2.0

# Testing & Quality
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.7.0
flake8>=6.0.0
mypy>=1.4.0

# Visualization & Analysis
matplotlib>=3.7.0
seaborn>=0.12.0
plotly>=5.15.0
shap>=0.42.0

# Active Learning & Uncertainty
modAL>=0.4.1
alipy>=1.2.5

# Model Interpretation
lime>=0.2.0
captum>=0.6.0

# Text Processing
nltk>=3.8.0
spacy>=3.6.0
textblob>=0.17.0

# Audio/Image Processing (optional)
librosa>=0.10.0
opencv-python>=4.8.0
pillow>=10.0.0

# Distributed Computing
dask>=2023.7.0
ray>=2.5.0

# Security & Authentication
cryptography>=41.0.0
python-jose>=3.3.0
passlib>=1.7.0
bcrypt>=4.0.0

# Logging & Monitoring
structlog>=23.1.0
prometheus-client>=0.17.0
sentry-sdk>=1.28.0

# Development Tools
ipython>=8.14.0
jupyter>=1.0.0
pre-commit>=3.3.0=== ./services/dmlog-world/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
requests==2.31.0
httpx==0.25.2

# Map generation and image processing
Pillow==10.1.0
opencv-python==4.8.1.78
numpy==1.24.3
matplotlib==3.8.2
scipy==1.11.4

# Random generation
noise==1.2.2
opensimplex==0.3

# Text processing and generation
nltk==3.8.1
textstat==0.7.3
markovify==0.9.4

# Time and calendar
python-dateutil==2.8.2
pytz==2023.3

# Economy simulation
networkx==3.2.1

# Data serialization
pyyaml==6.0.1
toml==0.10.2=== ./services/ai-orchestrator/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
redis==5.0.1
minio==7.2.0
openai==1.6.1
pillow==10.1.0
aiohttp==3.9.1
elasticsearch[async]==8.11.0
mutagen==1.47.0
aiofiles==23.2.0
=== ./services/smart-folders/requirements.txt ===
# FastAPI and server dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
alembic==1.12.1
asyncpg==0.29.0
databases[postgresql]==0.8.0

# AI and ML dependencies
scikit-learn==1.3.2
pandas==2.1.4
numpy==1.24.4
nltk==3.8.1
transformers==4.36.0
torch==2.1.0
sentence-transformers==2.2.2

# Rule engine and processing
python-rule-engine==1.0.5
croniter==2.0.1
watchdog==3.0.0

# File processing
python-magic==0.4.27
pillow==10.1.0
pypdf==3.17.1

# Authentication and security
pyjwt==2.8.0
cryptography==41.0.8
bcrypt==4.1.2

# Utilities
pydantic==2.5.0
pydantic-settings==2.1.0
structlog==23.2.0
redis==5.0.1
aiofiles==23.2.1
aiohttp==3.9.1

# Background tasks
celery[redis]==5.3.4
APScheduler==3.10.4

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Development
black==23.11.0
isort==5.12.0
flake8==6.1.0=== ./services/notifications/requirements.txt ===
# ActiveLog Notification Service Dependencies

# FastAPI and ASGI server
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database
asyncpg==0.29.0
psycopg2-binary==2.9.9

# Redis for caching and queues
redis==5.0.1
aioredis==2.0.1

# Email providers
aiosmtplib==3.0.1
sendgrid==6.11.0
boto3==1.34.0  # AWS SES

# SMS provider
twilio==8.10.0

# Template engine
Jinja2==3.1.2

# HTTP client
aiohttp==3.9.1
httpx==0.25.2

# Structured logging
structlog==23.2.0

# Configuration and validation
pydantic==2.5.0
pydantic-settings==2.1.0

# Environment variables
python-dotenv==1.0.0

# Date/time handling
python-dateutil==2.8.2

# JSON handling
orjson==3.9.10

# WebSocket support
websockets==12.0

# File handling
aiofiles==23.2.1

# Security
cryptography==41.0.7
PyJWT==2.8.0

# Development dependencies
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
flake8==6.1.0
mypy==1.7.1

# Optional: Advanced template features
markdown==3.5.1
bleach==6.1.0=== ./services/video-processor/requirements.txt ===
# FastAPI and web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0

# Async and HTTP
aiofiles==23.2.1
aiohttp==3.9.1
asyncpg==0.29.0

# Video processing
opencv-python==4.8.1.78
ffmpeg-python==0.2.0
Pillow==10.1.0
numpy==1.24.4
scipy==1.11.4

# OCR
pytesseract==0.3.10

# AI and NLP
openai==1.3.7
anthropic==0.7.8

# Data validation and configuration
pydantic==2.5.0
pydantic-settings==2.1.0

# Utilities
python-multipart==0.0.6
chardet==5.2.0
python-magic==0.4.27

# Development
pytest==7.4.3
pytest-asyncio==0.21.1=== ./services/cache/requirements.txt ===
# Redis Caching System Requirements

# Core Redis dependencies
redis>=4.5.0
aioredis>=2.0.1

# FastAPI for middleware
fastapi>=0.68.0

# Async support
asyncio-throttle>=1.0.2

# Utilities
python-dateutil>=2.8.2
pydantic>=1.10.0

# Compression
zstandard>=0.19.0

# Monitoring and logging
structlog>=22.1.0

# Optional: Redis Cluster support
redis-py-cluster>=2.1.3

# Optional: Prometheus metrics
prometheus-client>=0.14.1=== ./services/file-watcher/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
watchdog==3.0.0
aiofiles==23.2.0
redis==5.0.1
nats-py==2.6.0
pathspec==0.11.2
psutil==5.9.6
tenacity==8.2.3
pydantic==2.5.0
asyncpg==0.29.0
sqlalchemy==2.0.23
aiohttp==3.9.1=== ./services/auth/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
pydantic[email]==2.5.0
psycopg2-binary==2.9.9
bcrypt==4.1.2
PyJWT==2.8.0
python-jose[cryptography]==3.3.0=== ./services/analytics/requirements.txt ===
# ActiveLog Analytics Service Dependencies

# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database and TimescaleDB
asyncpg==0.29.0
psycopg2-binary==2.9.7

# Redis for caching
redis==5.0.1
aioredis==2.0.1

# Configuration and validation
pydantic[email]==2.5.0
python-dotenv==1.0.0

# Async support
asyncio==3.4.3
aiofiles==23.2.1

# Data processing and analysis
pandas==2.1.3
numpy==1.26.2

# Export formats
openpyxl==3.1.2

# Date handling
python-dateutil==2.8.2

# HTTP requests
requests==2.31.0

# Logging
structlog==23.2.0

# WebSocket support
websockets==12.0

# Security
cryptography==41.0.7

# Development and testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0

# Optional: Advanced analytics
# scipy==1.11.4
# scikit-learn==1.3.2

# Optional: Plotting for reports
# matplotlib==3.8.2
# plotly==5.17.0=== ./services/sync-engine/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.13.1
asyncpg==0.29.0
redis==5.0.1
minio==7.2.0
nats-py==2.6.0
aiofiles==23.2.0
watchdog==3.0.0
xxhash==3.4.1
aiodns==3.1.1
cryptography==41.0.8
pydantic==2.5.0
psutil==5.9.6
tenacity==8.2.3=== ./dev-tools/templates/service_templates/fastapi/requirements.txt ===
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
sqlalchemy[asyncio]>=2.0.23
aiosqlite>=0.19.0
redis>=5.0.1
python-multipart>=0.0.6
python-dotenv>=1.0.0
=== ./dev-tools/templates/service_templates/grpc/requirements.txt ===
grpcio>=1.59.0
grpcio-tools>=1.59.0
protobuf>=4.24.0
=== ./dev-tools/templates/service_templates/flask/requirements.txt ===
Flask>=3.0.0
Flask-CORS>=4.0.0
python-dotenv>=1.0.0
gunicorn>=21.2.0
=== ./dev-tools/templates/service_templates/celery_worker/requirements.txt ===
celery[redis]>=5.3.0
redis>=5.0.1
=== ./modules/healthcare/requirements.txt ===
# ActiveLog Healthcare Module Dependencies

# Core healthcare data standards
pydicom==2.4.3                    # DICOM medical imaging
fhirpy==2.0.12                     # FHIR client
python-hl7==0.3.4                 # HL7 message processing
dicom2nifti==2.4.8                # DICOM conversion utilities

# Medical imaging processing
SimpleITK==2.3.1                  # Medical image processing
nibabel==5.2.0                    # Neuroimaging data I/O
pylibjpeg==1.4.0                  # JPEG compression for DICOM
pylibjpeg-libjpeg==1.3.4         # JPEG library
gdcm==3.0.21                      # DICOM toolkit

# NLP for clinical notes
spacy==3.7.2                      # NLP framework
scispacy==0.5.3                   # Scientific/medical NLP
transformers==4.36.2              # Hugging Face transformers
torch==2.1.2                      # PyTorch for ML models
scikit-learn==1.3.2               # ML utilities

# Medical terminology and coding
pymedtermino==0.3.3               # Medical terminologies
icd10-cm==0.0.4                   # ICD-10 codes

# Cryptography and security
cryptography==41.0.8              # Encryption
pycryptodome==3.19.0              # Additional crypto functions
jwcrypto==1.5.0                   # JSON Web Encryption

# Database and storage
sqlalchemy==2.0.23                # ORM
alembic==1.12.1                   # Database migrations
redis==5.0.1                      # Caching
boto3==1.34.0                     # AWS SDK for secure storage

# API and web framework
fastapi==0.104.1                  # REST API framework
uvicorn[standard]==0.24.0         # ASGI server
websockets==12.0                  # WebSocket support
python-multipart==0.0.6          # File upload support

# Data validation and serialization
pydantic==2.5.0                   # Data validation
marshmallow==3.20.2               # Serialization
jsonschema==4.20.0                # JSON validation

# Monitoring and logging
structlog==23.2.0                 # Structured logging
prometheus-client==0.19.0         # Metrics

# Utilities
python-dateutil==2.8.2           # Date utilities
pytz==2023.3                      # Timezone handling
python-dotenv==1.0.0              # Environment variables

# Testing (for development)
pytest==7.4.3                     # Testing framework
pytest-asyncio==0.21.1            # Async testing
pytest-mock==3.12.0               # Mocking

# Development tools
black==23.11.0                    # Code formatting
ruff==0.1.6                       # Linting=== ./security/audit/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
redis==5.0.1
elasticsearch==8.11.0
pydantic==2.5.0
structlog==23.2.0
geoip2==4.7.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-exporter-jaeger==1.21.0
opentelemetry-exporter-jaeger-thrift==1.21.0
requests==2.31.0
aiofiles==23.2.1
python-multipart==0.0.6
asyncpg==0.29.0
sqlalchemy==2.0.23
alembic==1.13.1
pyyaml==6.0.1
croniter==2.0.1
pytz==2023.3=== ./security/secrets/requirements.txt ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
redis==5.0.1
boto3==1.34.0
hvac==2.0.0
cryptography==41.0.7
pydantic==2.5.0
apscheduler==3.10.4
requests==2.31.0
aiofiles==23.2.1
python-multipart==0.0.6
asyncpg==0.29.0
sqlalchemy==2.0.23
alembic==1.13.1=== ./infrastructure/terraform/modules/lambda/lambda_code/requirements.txt ===
# Lambda Layer Dependencies for ActiveLog

# Core dependencies
boto3==1.29.0
botocore==1.32.0

# Database connectivity
psycopg2-binary==2.9.7

# OpenAI API
openai==1.3.0

# Email processing
email-validator==2.1.0

# File processing
pillow==10.1.0
python-magic==0.4.27

# Text processing
beautifulsoup4==4.12.2
lxml==4.9.3

# PDF processing
PyPDF2==3.0.1

# Office document processing
python-docx==1.1.0
openpyxl==3.1.2

# Compression/Archive handling
rarfile==4.1
py7zr==0.20.6

# Image processing
opencv-python-headless==4.8.1.78

# Audio/Video metadata
mutagen==1.47.0

# Cryptography
cryptography==41.0.7

# HTTP requests
requests==2.31.0
httpx==0.25.2

# JSON/Data processing
pydantic==2.5.0
jsonschema==4.20.0

# Async support
aiofiles==23.2.1
asyncio-mqtt==0.16.1

# Logging and monitoring
structlog==23.2.0

# Utilities
python-dateutil==2.8.2
pytz==2023.3
uuid==1.30

# Security
bcrypt==4.1.2

# File type detection
filetype==1.2.0

# OCR (Optical Character Recognition)
pytesseract==0.3.10

# Language detection
langdetect==1.0.9

# Environment variables
python-dotenv==1.0.0=== ./sdk/marketplace/requirements.txt ===
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.0
pydantic==2.5.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pyjwt==2.8.0
bcrypt==4.1.2
aiofiles==23.2.0=== ./sdk/docs/requirements.txt ===
jinja2==3.1.2
markdown==3.5.1
pygments==2.16.1
markupsafe==2.1.3=== ./tests/requirements.txt ===
# Core testing framework
pytest==7.4.3
pytest-cov==4.1.0
pytest-xdist==3.5.0
pytest-mock==3.12.0
pytest-asyncio==0.23.2
pytest-timeout==2.2.0
pytest-html==4.1.1
pytest-benchmark==4.0.0

# HTTP testing
httpx==0.25.2
requests==2.31.0
responses==0.24.1

# Database testing
pytest-postgresql==5.0.0
pytest-redis==3.0.2
factory-boy==3.3.0
faker==20.1.0

# API testing
fastapi[all]==0.104.1
starlette-testclient==0.37.2

# Async testing
asyncio==3.4.3
aioresponses==0.7.6

# Load testing
locust==2.17.0

# Mock and fixtures
responses==0.24.1
freezegun==1.2.2
time-machine==2.13.0
vcrpy==5.1.0

# Docker testing
testcontainers==3.7.1
docker==6.1.3

# Security testing
bandit==1.7.5
safety==2.3.5

# Performance monitoring
memory-profiler==0.61.0
psutil==5.9.6

# Test utilities
pydantic==2.5.0
sqlalchemy==2.0.23
alembic==1.13.1
redis==5.0.1
psycopg2-binary==2.9.9
bcrypt==4.1.2
jwt==1.3.1
cryptography==41.0.7

# AI/ML testing
torch==2.1.1
transformers==4.36.2
numpy==1.24.4
pandas==2.1.4
scikit-learn==1.3.2

# Email testing
aiosmtpd==1.4.4.post2

# File system testing
tempfile==3.11
shutil==3.11

# Monitoring
prometheus-client==0.19.0
PYTHON_IMPORTS_BY_SERVICE:
=== __pycache__ ===
=== activeledger ===
from ...config.settings import settings
from ...config.settings import settings, PRICING_COMPONENTS, COST_PLUS_MARKUP
from ...config.settings import settings, SUBSCRIPTION_TIERS
from ...models.database import (
from ...models.database import CurrencyExchangeRate
from ...models.database import Transaction, User, TransactionType, TransactionStatus, PaymentMethod
from ...models.database import User, PricingCalculation
from ...models.database import User, Transaction, CurrencyExchangeRate, TransactionType, TransactionStatus
from ..analytics.usage_tracker import UsageTracker
from ..config.settings import settings
from ..credits.cc_system import ComputeCreditSystem
from ..exchange.currency_converter import CurrencyConverter
from .ad_revenue import AdRevenueManager
from .affiliate_program import AffiliateManager
from .cost_calculator import CostPlusCalculator
from .currency_converter import CurrencyConverter
from .rental_manager import ComputeRentalManager
from abc import ABC, abstractmethod
from datetime import datetime
from datetime import datetime, timedelta
=== ads ===
from ad_service import AdService, AdServiceConfig
from affiliate.affiliate_manager import AffiliateManager, AffiliateNetwork
from core.ad_manager import AdManager, UserTier, UserAdPreferences
from core.ad_manager import UserTier
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from integrations.adsense_integration import AdSenseIntegration, AdSenseAccount
from typing import Dict, List, Any, Optional
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import asyncio
import base64
import hashlib
import hmac
import json
import random
import re
import urllib.parse
import uuid
=== ai-orchestrator ===
from PIL import Image
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from datetime import datetime, timedelta
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from functools import wraps
from minio import Minio
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from openai import AsyncOpenAI
from pathlib import Path
from plugin_manager import plugin_manager
from plugins.openai_plugin import OpenAIPlugin
from typing import Dict, Any
from typing import Dict, List, Any, Optional
=== ai-tools ===
from ...config.settings import settings
from ...config.settings import settings, AI_OPERATION_COSTS
from ...config.settings import settings, AI_OPERATION_COSTS, COMPUTE_OPTIMIZATION_RULES
from ...config.settings import settings, COMPUTE_OPTIMIZATION_RULES
from ...database import get_session
from ...database.models import (
from ...database.models import BatchJob, BatchJobStatus, QueuePriority
from ...database.models import LORATraining, LORATrainingStatus, TrainingDataset, ModelType
from ...database.models import VideoGeneration, VideoGenerationStatus, AIProvider
from ...exceptions import BatchProcessingError
from ...exceptions import LORATrainingError
from ...exceptions import MarketplaceError
from ...exceptions import VideoGenerationError
from ...models.ai_operations import (
from ...models.ai_operations import AIOperation, AIOperationType, AIProvider, OperationStatus
from ...models.ai_operations import CacheEntry, AIOperationType, AIOperation
from ...settings import settings
from ..cache.result_cache import ResultCache
from ..cache.result_cache import result_cache
from ..compute.optimizer import ComputeOptimizer
=== ai_orchestrator ===
=== ambient ===
from .context_switcher import (
from .environmental_adapter import (
from .predictive_actions import (
from .privacy_assistant import (
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import datetime, timedelta, time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
import asyncio
import hashlib
import json
import logging
import numpy as np
import pickle
import statistics
=== analytics ===
from ..core.config import settings
from ..core.database import DatabaseManager
from ..core.database import db_manager
from ..core.logging import logger
from .config import settings
from asyncpg.pool import Pool
from collections import defaultdict
from contextlib import asynccontextmanager
from core.config import settings
from core.database import DatabaseManager
from core.logging import logger
from dataclasses import dataclass, asdict
from datetime import datetime
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Response
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi import WebSocket
from fastapi.middleware.cors import CORSMiddleware
=== api-gateway ===
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, Set
import asyncio
import httpx
import json
import jwt
import logging
import redis.asyncio as redis
import time
import uuid
=== api_gateway ===
=== ar-layer ===
from .contextual_overlay import (
from .facial_recognition import (
from .gesture_recognition import (
from .real_time_translator import (
from PIL import Image
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from googletrans import Translator
from typing import Dict, List, Any, Optional, Callable, Tuple
from typing import Dict, List, Any, Optional, Tuple
from typing import Dict, List, Any, Optional, Tuple, Set
from typing import Dict, List, Any, Optional, Tuple, Union
import asyncio
import base64
import cv2
=== auth ===
from auth_models import UserModel
from auth_models import UserModel, RefreshTokenModel
from auth_models import init_db
from auth_routes import router as auth_router
from auth_utils import (
from auth_utils import verify_access_token
from contextlib import asynccontextmanager
from datetime import datetime
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi import Depends, HTTPException, status
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps
from middleware import get_current_user, require_admin, require_user_or_admin
from middleware import get_current_user, require_role
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, EmailStr, validator
from schemas import (
=== backup ===
from ..core.config import settings
from ..core.database import DatabaseManager
from ..crypto.encryption import BackupEncryption
from .backup_manager import BackupManager
from .config import settings
from .local_destination import LocalDestination
from .recovery_service import RecoveryService
from botocore.exceptions import ClientError, NoCredentialsError
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from core.config import settings
from core.database import DatabaseManager
from core.logging import logger, backup_logger
from croniter import croniter
from crypto.encryption import BackupEncryption
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
=== batch-import ===
from ..core.config import settings
from ..core.logging import logger
from .config import settings
from .logging import logger
from .minio_service import MinIOService
from api.routes import router
from api.websocket import websocket_router
from core.config import settings
from core.logging_config import setup_logging
from dataclasses import dataclass, asdict
from dataclasses import dataclass, field
from datetime import datetime
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from main import get_batch_processor, get_report_service, get_import_monitor
=== biological ===
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from cryptography.fernet import Fernet
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable, Union, Set
import asyncio
import base64
import hashlib
import json
import logging
import math
import numpy as np
import random
import time
import uuid
=== blockchain ===
from ..config.blockchain_config import (
from ..config.blockchain_config import blockchain_config
from ..config.blockchain_config import blockchain_config, BlockchainNetwork
from ..config.blockchain_config import blockchain_config, BlockchainNetwork, ContractType
from ..models.blockchain_models import ComputeMarketplace
from ..models.blockchain_models import ComputeToken, ComputeMarketplace
from ..models.blockchain_models import ConsensusNode, SharedTruth
from ..models.blockchain_models import ReputationToken
from ..models.blockchain_models import ZKProof
from ..privacy.zk_proof_system import ZKProofSystem
from ..storage.ipfs_manager import IPFSManager
from ..tokens.compute_token_manager import ComputeTokenManager, ResourceType, PricingModel
from ..tokens.reputation_token_manager import ReputationTokenManager, ReputationAction
from ..tokens.reputation_token_manager import ReputationTokenManager, ReputationAction, ReputationCategory
from ..utils.crypto_utils import (
from ..utils.crypto_utils import create_data_hash, generate_merkle_tree
from ..utils.crypto_utils import create_data_hash, generate_merkle_tree, create_accumulator_proof
from ..utils.crypto_utils import generate_merkle_tree, create_data_hash
from ..utils.crypto_utils import generate_merkle_tree, create_event_hash
from .audit.immutable_audit_trail import ImmutableAuditTrail, EventType, Severity  
=== cache ===
from .api_cache import (
from .distributed_locks import (
from .invalidation import (
from .metadata_cache import (
from .redis_client import (
from .redis_client import get_redis_client, RedisClient
from .redis_client import get_redis_client, RedisClient, cache_result
from .session_cache import (
from contextlib import asynccontextmanager
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from functools import wraps
from typing import Any, Optional, Dict, List, Union
from typing import Dict, List, Optional, Any, Tuple
from typing import Dict, List, Optional, Any, Tuple, Union
from typing import Dict, List, Optional, Set, Any
=== cognitive ===
=== collaboration ===
from .activity_manager import ActivityManager
from .annotation_manager import AnnotationManager
from .comment_manager import CommentManager
from .config import settings
from .diff_engine import DiffEngine
from .discussion_handler import DiscussionHandler
from .guest_manager import GuestManager
from .membership_manager import MembershipManager
from .permission_manager import PermissionManager
from .realtime_handler import RealtimeAnnotationHandler
from .role_manager import RoleManager
from .session_manager import GuestSessionManager
from .timeline_builder import TimelineBuilder
from .version_manager import VersionManager
from .workspace_manager import WorkspaceManager
from collections import defaultdict
from contextlib import asynccontextmanager
from core.config import settings
from core.config import settings, LOGGING_CONFIG
from core.database import ActivityType
=== creative-suite ===
from PIL import Image, ImageFilter, ImageEnhance
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize, sent_tokenize
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4
import asyncio
import base64
import io
import json
import logging
import nltk
import numpy as np
import random
=== data-export ===
from ..cloud.cloud_providers import CloudProviderManager
from ..core.config import settings
from ..core.database import db_manager, ExportStatus, ExportType
from ..exporters.archive_exporter import ArchiveExporter
from ..exporters.gdpr_exporter import GDPRExporter
from ..exporters.pdf_exporter import PDFExporter
from ..generators.photobook_generator import PhotoBookGenerator
from ..generators.website_generator import WebsiteGenerator
from ..utils.file_utils import get_file_metadata, get_files_by_filters
from ..utils.metadata_extractor import MetadataExtractor
from ..utils.progress_tracker import ProgressTracker
from .config import settings
from .database import db_manager, ExportStatus, ExportType
from .progress_tracker import ProgressTracker, ProgressStatus, create_progress_tracker
from PIL import Image
from PIL import Image as PILImage
from PIL import Image as PILImage, ImageEnhance, ImageFilter
from abc import ABC, abstractmethod
from api.routes import router as api_router
from concurrent.futures import ThreadPoolExecutor
=== data-manager ===
from abc import ABC, abstractmethod
from ai.intelligent_classifier import IntelligentClassifier
from ai.recommendation_engine import RecommendationEngine
from analytics.insights_engine import InsightsEngine
from api.integration import integration_service, personalization_layer
from collections import defaultdict, Counter
from core.data_manager import DataManager
from dataclasses import asdict
from dataclasses import dataclass, asdict
from datetime import datetime
from datetime import datetime, timedelta
from datetime import datetime, timezone
from datetime import datetime, timezone, timedelta
from enum import Enum
from monitoring.quality_monitor import QualityMonitor
from pathlib import Path
from processing.processors import *
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
=== dmlog-ai-dm ===
from ..config import AI_DM_CONFIG
from ..config import DIFFICULTY_CONFIG
from ..config import ENGAGEMENT_CONFIG
from ..config import IMPROVISATION_CONFIG
from ..config import LORE_CONFIG
from ..config import NARRATIVE_CONFIG
from ..config import TIMING_CONFIG, FORESHADOWING_CONFIG
from ..models.base import (
from ..models.base import LoreEntry, Campaign, NarrativeEvent
from ..models.base import Player, GameMetrics, SessionState, DifficultyLevel
from ..models.base import Player, SessionState, EngagementLevel
from ..utils.ai_client import AIClient
from ..utils.coherence_analyzer import CoherenceAnalyzer
from ..utils.random_tables import RandomTables
from .assistants.improvisation_assistant import ImprovisationAssistant
from .config import AI_DM_CONFIG, DATABASE_CONFIG, LOGGING_CONFIG
from .managers.difficulty_manager import DifficultyManager
from .managers.dramatic_timing_manager import DramaticTimingManager
from .managers.engagement_monitor import PlayerEngagementMonitor
from .managers.narrative_manager import NarrativeFlowManager
=== dmlog-battle ===
from ..config import Config
from ..models.base import (
from ..models.base import Position, CreatureSize, ActionType, DamageType
from ..models.base import Position, DamageType, ActionType
from ..models.base import Position, GridCell, CoverType
from ..models.base import Position, GridCell, TerrainType, CoverType, LineOfSight
from ..models.base import Position, TerrainType, DamageType
from ..models.battlefield import (
from ..models.battlefield import BattlefieldSchema, AreaOfEffect
from ..models.battlefield import BattlefieldSchema, AreaOfEffect, AOEShape
from ..models.battlefield import BattlefieldSchema, AreaOfEffect, LightSource, AOEShape
from ..models.battlefield import BattlefieldSchema, EnvironmentalHazard, LightSource, AreaOfEffect, GridArea
from ..models.combat import (
from ..models.combat import CombatEncounter
from ..models.combat import CombatEncounter, CombatAction
from ..models.combat import CombatEncounter, CombatAction, SpellResult
from ..models.combatant import CombatantSchema
from ..models.combatant import CombatantSchema, DeathSavingThrows
from ..models.combatant import CombatantSchema, Mount
from ..services.grid_service import GridService
=== dmlog-characters ===
from ..config import Config
from ..config import settings
from ..models.base import CharacterType, CharacterRace, ArtStyle
from ..models.base import EmotionType
from ..models.base import EmotionType, CharacterType
from ..models.base import EmotionType, CharacterType, AccentType, SpeechPattern
from ..models.base import EmotionType, CharacterType, CharacterRace
from ..models.base import EmotionType, VoiceGender, AccentType, SpeechPattern
from ..models.character_arc import (
from ..models.dialogue import (
from ..models.emotion import (
from ..models.faction import (
from ..models.faction import FactionReputationSchema
from ..models.mannerism import (
from ..models.memory import (
from ..models.memory import MemorySchema
from ..models.personality import (
from ..models.personality import PersonalityProfileSchema
from ..models.personality import PersonalityProfileSchema, MoralAlignment
from ..models.portrait import (
=== dmlog-converter ===
from ..config.systems import (
from ..config.systems import GameSystem
from ..config.systems import GameSystem, MECHANIC_MAPPINGS
from ..config.systems import GameSystem, POWER_LEVEL_MAPPINGS
from ..config.systems import GameSystem, SPELL_MAPPINGS, ITEM_MAPPINGS
from ..models.base import Adventure, ConversionResult, Monster, Item
from ..models.base import Character, ConversionResult, ConversionRule
from ..models.base import ConversionResult
from ..models.base import HouseRule, ValidationResult, ConversionResult
from ..models.base import Item, Spell, ConversionResult
from ..models.base import Mechanic, ConversionResult
from ..models.base import Monster, ConversionResult
from ..models.base import ValidationResult, Character, Monster, Spell, Item, BalanceCheck
from .character_converter import CharacterConverter
from .config.systems import GameSystem
from .converters.adventure_converter import AdventureConverter
from .converters.character_converter import CharacterConverter
from .converters.difficulty_converter import DifficultyConverter, DifficultyTier
from .converters.mechanic_converter import MechanicConverter
from .difficulty_converter import DifficultyConverter
=== dmlog-core ===
from ..database import get_db
from ..models.base import (
from ..models.base import DamageType, ConditionType, ActionType
from ..models.base import DiceType
from ..models.base import DifficultyLevel
from ..models.base import Rarity, DamageType
from ..models.campaign import (
from ..models.character import (
from ..models.character import Character
from ..models.combat import (
from ..models.combat import CombatEncounterSchema, CombatParticipantSchema, CombatActionRequest
from ..models.encounter import (
from ..models.encounter import EncounterSchema, EncounterRequest, EncounterBalance
from ..models.experience import (
from ..models.inventory import (
from ..models.loot import (
from ..models.npc import NPCSchema, NPCGenerationRequest, PersonalityProfile
from ..models.relationship import (
from ..models.rules import (
from ..models.spells import (
=== dmlog-marketplace ===
from ..models.base import AdventureModule, Product, ContentType, ProductStatus, Order
from ..models.base import ArtCommission, Product, ContentType, CommissionStatus
from ..models.base import AudioTrack, Product, ContentType, ProductStatus
from ..models.base import CampaignSetting, Product, ContentType, ProductStatus
from ..models.base import CustomMiniature, Product, ContentType, ProductStatus, Order
from ..models.base import DMScreen, Product, ContentType, ProductStatus
from ..models.base import DiceSkin, Product, ContentType, ProductStatus
from ..models.base import MapAsset, Product, ContentType, ProductStatus
from ..models.base import Review, Product, ProductStatus
from ..models.base import RoyaltyRule, Order, Product
from ..models.base import RulesSupplement, Product, ContentType, ProductStatus
from ..models.base import VoicePack, Product, ContentType, ProductStatus
from .models.base import (
from .services.review_system import ReviewSystem
from .services.royalty_system import RoyaltySystem
from .stores.adventure_store import AdventureStore
from .stores.art_commission_store import ArtCommissionStore
from .stores.audio_library import AudioLibrary
from .stores.campaign_setting_store import CampaignSettingStore
from .stores.dice_skin_store import DiceSkinStore
=== dmlog-player ===
from ..models.base import Character, SpellSlotUsage
from ..models.base import InventoryItem, Character
from ..models.base import JournalEntry, Character
from ..models.base import Party, Character, PartyFund
from ..models.base import Quest, QuestStatus, Priority, Character
from ..models.base import Relationship, RelationshipType
from ..models.base import RestRecord, RestType, Character
from .managers.inventory_manager import InventoryManager
from .managers.journal_manager import JournalManager
from .managers.party_manager import PartyManager
from .managers.quest_tracker import QuestTracker
from .managers.relationship_manager import RelationshipManager
from .managers.spell_reference_manager import SpellReferenceManager
from .models.base import (
from datetime import datetime
from datetime import datetime, date
from enum import Enum
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
=== dmlog-session ===
from ..config import AI_CONFIG, RECAP_CONFIG
from ..config import ANALYTICS_CONFIG
from ..config import AUDIO_CONFIG
from ..config import CONTENT_CONFIG
from ..config import Config
from ..config import FEEDBACK_CONFIG
from ..config import TABLETOP_CONFIG
from ..models.base import (
from ..models.base import AudioSegment, SpeakerProfile, TranscriptionStatus
from ..models.base import BaseSessionModel
from ..models.base import BaseSessionModel, SessionHighlight, HighlightType
from ..models.base import SessionHighlight, HighlightType
from ..models.base import SessionHighlight, HighlightType, AudioSegment
from ..models.content import (
from ..models.content import AudioTrack, Playlist, AmbianceScene, AudioCue
from ..models.content import Survey, SurveyQuestion, SurveyResponse, FeedbackReport
from ..models.scheduling import (
from ..models.session import (
from ..models.session import SessionSchema
from ..models.session import SessionSchema, SessionNote, SessionParticipant, TranscriptionSegment
=== dmlog-templates ===
from ..config import BACKSTORY_CONFIG
from ..config import CHASE_CONFIG
from ..config import HEIST_CONFIG
from ..config import HORROR_CONFIG
from ..config import LEVEL_TIERS, TEMPLATE_CONFIG, ENCOUNTER_CONFIG
from ..config import MYSTERY_CONFIG
from ..config import PLOT_CONFIG
from ..config import POLITICAL_CONFIG
from ..config import PUZZLE_CONFIG
from ..config import SOCIAL_CONFIG
from ..config import TRAP_CONFIG
from ..models.adventure import Adventure, Chapter
from ..models.adventure import Adventure, Chapter, Scene, OneShot, AdventureHook, AdventureSite
from ..models.base import (
from ..models.base import BaseTemplate, ComplexityLevel, DifficultyLevel
from ..models.base import DiceRoll, DamageType, SkillType, SkillCheck
from ..models.base import SkillCheck, SkillType, DifficultyLevel
from ..models.base import SkillCheck, SkillType, StatBlock
from ..models.base import SkillType
from ..models.base import Twist, ComplexityLevel, ThemeType
=== dmlog-world ===
from ..config import Config
from ..models.base import BiomeType, ClimateType, Coordinate
from ..models.base import BiomeType, WeatherType, TileType
from ..models.calendar import (
from ..models.location import (
from ..models.maps import (
from ..models.religion import (
from ..models.weather import (
from .base import Base, BaseWorldModel
from .base import Base, BaseWorldModel, DeityDomain
from .base import Base, BaseWorldModel, MapType, BiomeType, SettlementType, Coordinate, Color
from .base import Base, BaseWorldModel, MapType, BiomeType, WeatherType, TileType, Coordinate
from .base import Base, BaseWorldModel, WeatherType, ClimateType, BiomeType, Coordinate
from .config import Config
from .models.calendar import (
from .models.location import (
from .models.maps import (
from .models.religion import (
from .models.weather import (
from .services.calendar_service import CalendarService
=== document-ai ===
from ..core.config import settings
from ..core.config import settings, DOCUMENT_TYPES, LANGUAGE_CONFIGS
from ..core.config import settings, LANGUAGE_CONFIGS
from ..core.database import DatabaseManager
from ..models.document_models import DocumentEmbedding, SemanticSearchResult
from ..models.document_models import DocumentSummary, SummaryType
from ..models.document_models import DocumentType, DocumentClassification
from ..models.document_models import ExtractedTable, TableCell, BoundingBox
from ..models.document_models import ExtractedText, ExtractionMethod, BoundingBox
from ..models.document_models import NamedEntity, EntityType
from .config import settings
from .config import settings, DOCUMENT_TYPES, LANGUAGE_CONFIGS
from .database import DatabaseManager
from .document_classifier import DocumentClassifier
from .document_models import (
from .logging import setup_logging, logger, doc_logger, ocr_logger, nlp_logger, vector_logger
from .ner_processor import NERProcessor
from .summarization_processor import SummarizationProcessor
from .table_extractor import TableExtractor
from .text_extractor import TextExtractor
=== education-ai ===
from collections import deque
from dataclasses import dataclass, asdict, field
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from enum import Enum
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional, Tuple, Any
from typing import Dict, List, Optional, Tuple, Any, Union
from typing import Dict, List, Optional, Tuple, Set, Any
from typing import Dict, List, Optional, Tuple, Set, Any, Union
import asyncio
import difflib
import hashlib
=== emotional-ai ===
from .emotional_journey_mapper import (
from .mood_detector import (
from .stress_detector import (
from collections import defaultdict
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from nltk.sentiment import SentimentIntensityAnalyzer
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from textblob import TextBlob
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import hashlib
=== file-sync ===
from fastapi import FastAPI, UploadFile, File
from minio import Minio
import psycopg2
import redis
=== file-watcher ===
from batch_importer import BatchImporter, ThrottledBatchProcessor
from config import WatcherConfig
from contextlib import asynccontextmanager
from dataclasses import dataclass
from dataclasses import dataclass, field
from datetime import datetime
from datetime import datetime, timedelta
from enum import Enum
from event_queue import EventQueue, SyncEngineClient
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from ignore_patterns import SmartIgnoreManager
from models import FileEventType
from models import FileEventType, EventStatus
from nats.aio.client import Client as NATS
from nats.js.api import StreamConfig, ConsumerConfig, RetentionPolicy, DiscardPolicy
from pathlib import Path
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, Float, JSON
from sqlalchemy import Index
=== file_processor ===
=== gaming-platform ===
from .coordination_analytics import (
from .replay_analyzer import (
from collections import defaultdict, Counter
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from scipy.spatial.distance import pdist, squareform
from scipy.stats import pearsonr
from sklearn.cluster import DBSCAN
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Any, Optional, Tuple
from typing import Dict, List, Any, Optional, Tuple, Set
import asyncio
import cv2
import hashlib
import json
import logging
=== graphql ===
=== health-integration ===
from ..devices.wearable_ingestion import DataType, wearable_ingestion
from ..devices.wearable_ingestion import HealthDataPoint, DataType, wearable_ingestion
from PIL import Image
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import datetime, timedelta, date
from datetime import datetime, timedelta, time
from enum import Enum
from scipy import signal
from scipy import stats
from scipy.signal import find_peaks
from scipy.stats import pearsonr
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from typing import Any, Dict, List, Optional, Set, Tuple, Union
=== manufacturing ===
from PIL import Image, ImageDraw
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from datetime import datetime, timedelta
from docx import Document
from docx.shared import Inches
from enum import Enum
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from scipy import stats
from scipy import stats, signal
from scipy.optimize import minimize
=== marine-advanced ===
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from geopy.distance import geodesic
from io import BytesIO
from jinja2 import Template
from pathlib import Path
from scipy import interpolate, optimize
from scipy import optimize
from scipy import optimize, interpolate
from scipy import optimize, stats
from scipy import stats
from scipy.spatial.distance import euclidean
from scipy.spatial.distance import haversine
from shapely.geometry import Point, Polygon, Circle
from shapely.ops import transform
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
=== memory-preservation ===
from collections import defaultdict
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from typing import Dict, List, Optional, Any, Tuple, Union, Set
import asyncio
import json
import numpy as np
import re
import uuid
=== metadata ===
from contextlib import asynccontextmanager
from database import FileMetadataModel, TagModel, get_db
from database import get_db
from database import get_db, FileMetadataModel
from database import init_db
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from elasticsearch_client import ElasticsearchService
from elasticsearch_client import init_elasticsearch
from embeddings import EmbeddingService
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, validator
from relationships import RelationshipService
from routes import metadata_router, tags_router, search_router, embeddings_router, relationships_router, batch_router
from schemas import (
from typing import Dict, Any, List, Optional
from typing import List, Dict, Any, Optional
=== ml-pipeline ===
from ab_testing.ab_tester import ABTestConfig, ABTestVariant
from ab_testing.ab_tester import ABTester, ABTestConfig, ABTestManager
from abc import ABC, abstractmethod
from active_learning.active_learner import ActiveLearner, ActiveLearningConfig, ActiveLearningManager
from active_learning.active_learner import ActiveLearningConfig
from celery import Celery, Task
from celery.exceptions import Retry, WorkerLostError
from celery.result import AsyncResult
from celery.signals import worker_ready, worker_shutdown
from collections import Counter
from collections import defaultdict, Counter
from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import dataclass, field
from dataclasses import dataclass, field, asdict
from datetime import datetime
from datetime import datetime, timedelta
from embeddings.fine_tuner import EmbeddingFineTuner, FineTuningConfig, MultiUserEmbeddingManager
from embeddings.fine_tuner import FineTuningConfig
=== mobile-api ===
from ..api.auth import get_current_user
from ..config import settings
from ..core.config import settings
from ..core.config import settings, mobile_settings
from ..core.database import get_database
from ..middleware.compression import compress_response
from ..middleware.mobile_optimization import get_device_info, get_connection_info
from ..middleware.rate_limiting import rate_limit
from ..protobuf.generated.mobile_pb import (
from ..services.auth_service import AuthService, TokenService, DeviceService
from ..services.battery_manager import BatteryManager
from ..services.security_service import SecurityService
from ..services.sync_manager import SyncManager, SyncConflictResolver
from PIL import Image, ImageOps, ExifTags
from PIL.Image import Resampling
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
=== multiverse ===
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from cryptography.fernet import Fernet
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Callable, Union, Set
import asyncio
import base64
import hashlib
import json
import logging
import math
import numpy as np
import random
import time
import uuid
=== notification ===
=== notifications ===
from ..core.config import settings
from ..core.database import DatabaseManager
from ..core.logging import logger
from .config import settings
from .logging import logger
from api.routes import router
from api.websocket import websocket_router
from asyncpg.pool import Pool
from contextlib import asynccontextmanager
from core.config import settings
from core.database import DatabaseManager
from core.logging import logger
from datetime import datetime
from datetime import datetime, time
from datetime import datetime, timedelta
from datetime import datetime, timedelta, time as dt_time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
=== p2p-sync ===
from .config import settings
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from typing import List, Dict, Any, Optional
import asyncio
import asyncpg
import hashlib
import json
import logging
import os
=== predictive-ai ===
from collections import defaultdict, Counter
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from typing import Dict, List, Any, Optional, Tuple, Set
import asyncio
import calendar
import hashlib
import json
import math
import numpy as np
import os
import random
import re
=== predictive ===
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional, Tuple, Any, Callable, Union, Set
import asyncio
import hashlib
import json
import logging
import math
import numpy as np
import random
import time
import uuid
import warnings
=== quantum-ready ===
from ..algorithms.quantum_interfaces import UnifiedQuantumInterface
from ..encryption.quantum_resistant_encryption import QuantumResistantCrypto
from ..optimization.quantum_optimization import QuantumOptimizer
from ..security.quantum_key_distribution import QuantumKeyDistribution
from .algorithms.quantum_interfaces import QuantumAlgorithmInterface
from .annealing.quantum_annealing import QuantumAnnealingInterface
from .communication.quantum_protocols import QuantumCommunication
from .crypto.post_quantum_crypto import PostQuantumCryptography
from .encryption.quantum_resistant_encryption import QuantumResistantCrypto
from .ml.quantum_ml_prep import QuantumMLPreparation
from .optimization.quantum_optimization import QuantumOptimizer
from .pipelines.hybrid_pipelines import HybridQuantumPipeline
from .random.quantum_rng import QuantumRandomGenerator
from .security.quantum_key_distribution import QuantumKeyDistribution
from .sensing.quantum_sensing import QuantumSensingIngestion
from .simulation.quantum_simulation import QuantumSimulator
from abc import ABC, abstractmethod
from cirq import Circuit as CirqCircuit, GridQubit
from cirq import Simulator, Circuit as CirqCircuit
from collections import deque
=== quantum-reality ===
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
import asyncio
import base64
import hashlib
import hmac
import json
import math
import numpy as np
import pickle
import secrets
import sqlite3
import statistics
import uuid
=== security-advanced ===
from .anonymous_credentials import (
from .behavioral_authentication import (
from .data_sovereignty import (
from .decoy_data import (
from .differential_privacy import (
from .federated_learning import (
from .homomorphic_encryption import (
from .privacy_budget_management import (
from .quantum_safe_encryption import (
from .record_linkage import (
from .secure_enclaves import (
from .secure_multiparty_computation import (
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import dataclass, field
from datetime import datetime
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
=== simulation ===
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from scipy import stats
from scipy.spatial.distance import euclidean
from sklearn.cluster import DBSCAN
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from typing import Dict, List, Optional, Tuple, Any, Callable, Union, Set
from uuid import uuid4
import asyncio
import json
import logging
import math
import networkx as nx
import numpy as np
=== smart-folders ===
from ..ai.folder_suggester import FolderSuggester
from ..core.config import settings
from ..core.database import db_manager
from ..core.database import db_manager, FolderType
from ..core.rule_engine import RuleEngine
from ..permissions.permission_manager import PermissionManager
from ..templates.template_manager import TemplateManager
from ..utils.cache_manager import CacheManager
from ..virtual.virtual_folder_manager import VirtualFolderManager
from .config import settings
from .database import RuleOperator
from .database import db_manager
from .database import db_manager, FolderType
from .inheritance_manager import InheritanceManager
from .permission_manager import PermissionManager
from .rule_engine import RuleEngine
from .template_manager import TemplateManager, FolderTemplate
from PIL import Image
from api.routes import router as api_router
from collections import defaultdict, Counter
=== social-ai ===
from collections import Counter
from collections import defaultdict
from collections import defaultdict, Counter
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional, Tuple, Set, Any
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from typing import List, Dict, Optional, Tuple, Any
from typing import List, Dict, Optional, Tuple, Any, Set
import asyncio
import itertools
import json
import logging
import math
import networkx as nx
=== sync-engine ===
from contextlib import asynccontextmanager
from copy import deepcopy
from crdt import CRDTFileSystem, ConflictResolver
from dataclasses import dataclass
from dataclasses import dataclass, asdict
from datetime import datetime
from datetime import datetime, timedelta
from delta_sync import FileChunk, CompressionHandler
from delta_sync import ResumableUploader, BinaryDelta
from delta_sync import ResumableUploader, BinaryDelta, CompressionHandler
from enum import Enum
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.responses import JSONResponse
from minio import Minio
from minio.commonconfig import Tags, REPLACE
from minio.error import S3Error, NoSuchKey, NoSuchBucket
from models import Base, SyncRule, FileInfo, SyncJob, SyncStatus
from models import FileInfo
from models import SyncJob, SyncStatus, FileInfo
from models import SyncRule, FileInfo
=== sync-v2 ===
from ..core.sync_engine import DeviceInfo, DeviceCapabilities, SyncItem, ContentType, DeviceType
from ..core.sync_engine import SyncItem, DeviceInfo, DeviceType, DeviceCapabilities
from ..realtime.collaboration_hub import CollaborationHub
from ..resolution.conflict_resolver import ConflictManager
from ..strategies.bandwidth_aware import NetworkMonitor, AdaptiveSyncScheduler
from ..strategies.selective_sync import SelectiveSyncEngine
from .core.sync_engine import SyncEngine, DeviceInfo, SyncItem, DeviceType, DeviceCapabilities
from .protocols.sync_protocol import SyncProtocolFactory, SyncRequest, SyncDirection
from .realtime.collaboration_hub import CollaborationHub
from .resolution.conflict_resolver import ConflictManager
from .strategies.bandwidth_aware import NetworkMonitor, AdaptiveSyncScheduler
from .strategies.selective_sync import SelectiveSyncEngine, SyncOptimizer
from contextlib import asynccontextmanager
from core.sync_engine import SyncEngine, SyncItem, DeviceInfo, DeviceType, DeviceCapabilities, ContentType
from dataclasses import asdict
from dataclasses import dataclass, asdict
from datetime import datetime
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
=== time-machine ===
from .day_reconstructor import (
from .day_reconstructor import DayReconstruction, ReconstructedEvent, ActivityType, ConfidenceLevel
from .temporal_query_engine import (
from .temporal_query_engine import TemporalQuery, QueryResult
from .timeline_comparisons import (
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from datetime import datetime, timedelta, date, time
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import asyncio
import calendar
import hashlib
import itertools
import json
=== universal-translator ===
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dataclasses import dataclass, field
from datetime import datetime
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from scipy import stats
from typing import Dict, List, Optional, Any, Tuple, Union
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
import ast
import asyncio
import base64
import cv2
import hashlib
import io
import json
import librosa
import mediapipe as mp
=== video-pipeline ===
from .analytics import (
from .processing import (
from .video import (
from PIL import Image
from collections import deque, defaultdict
from config.settings import settings
from contextlib import asynccontextmanager
from core.database import Base
from core.database import init_db, close_db, get_db
from datetime import datetime
from datetime import datetime, timedelta
from enum import Enum
from fastapi import (
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from functools import lru_cache
from minio import Minio
from minio.error import S3Error
from models import Video, VideoStatus, ProcessingJob, JobType, JobStatus
=== video-processor ===
from ..core.config import settings
from ..core.database import DatabaseManager
from ..models.video_models import VideoFile, ProcessingJob
from ..processors.keyframe_extractor import KeyframeExtractor
from ..processors.ocr_processor import OCRProcessor
from ..processors.scene_detector import SceneDetector
from .config import settings
from .stream_processor import StreamingVideoProcessor, StreamFrame, StreamAnalysisResult
from PIL import Image, ImageEnhance, ImageFilter
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from core.config import settings
from core.database import DatabaseManager
from core.logging import setup_logging
from dataclasses import dataclass, asdict
from datetime import datetime
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
=== workflows ===
from .actions import ActionRegistry
from .conditions import ConditionEvaluator
from .config import settings
from .context import ExecutionContext
from .database import db_manager, init_db, close_db
from .integration_manager import IntegrationManager, BaseIntegration, AuthType, ServiceConfig
from .routes import router
from .scheduler import WorkflowScheduler, ScheduledWorkflow
from .template_manager import TemplateManager, WorkflowTemplate, TemplateCategory, TemplateStatus
from .triggers import TriggerRegistry
from .webhook_manager import WebhookManager, WebhookEndpointConfig, WebhookRequest, WebhookResponse
from .workflow_engine import WorkflowEngine, WorkflowExecution
from abc import ABC, abstractmethod
from api.routes import router as api_router
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from core.config import settings
from core.config import settings, LOGGING_CONFIG
from core.database import ActionType
from core.database import TriggerType
DEPENDENCIES_ANALYSIS_END

[0;32m=== 3. CODE METRICS ===[0m
CODE_METRICS_START
LINES_OF_CODE_BY_SERVICE:
=== __pycache__ ===
Python:  lines
JavaScript/TypeScript:  lines
JSON:  lines
Total:  lines

=== activeledger ===
Python: 7865 lines
JavaScript/TypeScript:  lines
JSON: 74 lines
Total: 11177 lines

=== ads ===
Python: 3179 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 3179 lines

=== ai-orchestrator ===
Python: 4196 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 4196 lines

=== ai-tools ===
Python: 7532 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 7532 lines

=== ai_orchestrator ===
Python:  lines
JavaScript/TypeScript:  lines
JSON:  lines
Total:  lines

=== ambient ===
Python: 3002 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 3002 lines

=== analytics ===
Python: 5205 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 5205 lines

=== api-gateway ===
Python: 652 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 652 lines

=== api_gateway ===
Python:  lines
JavaScript/TypeScript:  lines
JSON:  lines
Total:  lines

=== ar-layer ===
Python: 4693 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 4693 lines

=== auth ===
Python: 746 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 746 lines

=== backup ===
Python: 6043 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 6043 lines

=== batch-import ===
Python: 4081 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 4081 lines

=== biological ===
Python: 1872 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 1872 lines

=== blockchain ===
Python: 10322 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 10322 lines

=== cache ===
Python: 3117 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 3117 lines

=== cognitive ===
Python:  lines
JavaScript/TypeScript:  lines
JSON:  lines
Total:  lines

=== collaboration ===
Python: 7869 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 7869 lines

=== creative-suite ===
Python: 3477 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 3477 lines

=== data-export ===
Python: 7237 lines
JavaScript/TypeScript:  lines
JSON: 68 lines
Total: 12214 lines

=== data-manager ===
Python: 7177 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 7177 lines

=== dmlog-ai-dm ===
Python: 6660 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 6660 lines

=== dmlog-battle ===
Python: 6909 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 6909 lines

=== dmlog-characters ===
Python: 11885 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 11885 lines

=== dmlog-converter ===
Python: 7847 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 7847 lines

=== dmlog-core ===
Python: 13736 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 13736 lines

=== dmlog-marketplace ===
Python: 9126 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 9126 lines

=== dmlog-player ===
Python: 4321 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 4321 lines

=== dmlog-session ===
Python: 11020 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 11020 lines

=== dmlog-templates ===
Python: 9686 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 9686 lines

=== dmlog-world ===
Python: 8553 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 8553 lines

=== document-ai ===
Python: 13941 lines
JavaScript/TypeScript:  lines
JSON: 64 lines
Total: 15189 lines

=== education-ai ===
Python: 10178 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 10178 lines

=== emotional-ai ===
Python: 3818 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 3818 lines

=== file-sync ===
Python: 42 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 42 lines

=== file-watcher ===
Python: 2844 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 2844 lines

=== file_processor ===
Python:  lines
JavaScript/TypeScript:  lines
JSON:  lines
Total:  lines

=== gaming-platform ===
Python: 3253 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 3253 lines

=== graphql ===
Python:  lines
JavaScript/TypeScript:  lines
JSON: 125 lines
Total: 7785 lines

=== health-integration ===
Python: 8502 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 8502 lines

=== manufacturing ===
Python: 15723 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 15723 lines

=== marine-advanced ===
Python: 6756 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 6756 lines

=== memory-preservation ===
Python: 6642 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 6642 lines

=== metadata ===
Python: 2347 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 2347 lines

=== ml-pipeline ===
Python: 7901 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 7901 lines

=== mobile-api ===
Python: 4990 lines
JavaScript/TypeScript:  lines
JSON: 137 lines
Total: 10330 lines

=== multiverse ===
Python: 1736 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 1736 lines

=== notification ===
Python:  lines
JavaScript/TypeScript:  lines
JSON:  lines
Total:  lines

=== notifications ===
Python: 6717 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 6717 lines

=== p2p-sync ===
Python: 1032 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 1032 lines

=== predictive-ai ===
Python: 4370 lines
JavaScript/TypeScript:  lines
JSON: 59 lines
Total: 10097 lines

=== predictive ===
Python: 1805 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 1805 lines

=== quantum-ready ===
Python: 10046 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 10046 lines

=== quantum-reality ===
Python: 5662 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 5662 lines

=== security-advanced ===
Python: 8994 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 8994 lines

=== simulation ===
Python: 7209 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 7209 lines

=== smart-folders ===
Python: 6067 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 6067 lines

=== social-ai ===
Python: 11119 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 11119 lines

=== sync-engine ===
Python: 4632 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 4632 lines

=== sync-v2 ===
Python: 5992 lines
JavaScript/TypeScript:  lines
JSON: 131 lines
Total: 6123 lines

=== time-machine ===
Python: 3029 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 3029 lines

=== universal-translator ===
Python: 11599 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 11599 lines

=== video-pipeline ===
Python: 5965 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 5965 lines

=== video-processor ===
Python: 5985 lines
JavaScript/TypeScript:  lines
JSON: 48 lines
Total: 10123 lines

=== workflows ===
Python: 6948 lines
JavaScript/TypeScript:  lines
JSON:  lines
Total: 6948 lines

OVERALL_PROJECT_STATS:
Total Python lines: 471970
Total JavaScript/TypeScript lines: 
Total code files: 1007
CODE_METRICS_END

[0;32m=== 4. API ENDPOINTS ===[0m
API_ENDPOINTS_START
DETECTED_API_ROUTES:
=== ./services/graphql/src/schema/analytics.ts ===
=== ./services/graphql/src/schema/notification.ts ===
=== ./services/graphql/src/schema/plugin.ts ===
=== ./services/graphql/src/schema/video.ts ===
=== ./services/graphql/src/schema/user.ts ===
=== ./services/graphql/src/schema/subscription.ts ===
=== ./services/graphql/src/schema/file.ts ===
=== ./services/graphql/src/schema/index.ts ===
=== ./services/graphql/src/schema/organization.ts ===
=== ./services/graphql/src/server.ts ===
192:app.get('/health', (req, res) => {
200:app.get('/ready', async (req, res) => {
=== ./services/graphql/src/types/context.ts ===
=== ./services/activeledger/src/index.ts ===
45:app.get('/health', (req, res) => {
=== ./services/predictive-ai/src/api/PredictiveAIService.ts ===
33:    this.router.post('/users/:userId/actions/learn', this.learnFromAction.bind(this));
34:    this.router.get('/users/:userId/predictions', this.getPredictions.bind(this));
35:    this.router.get('/users/:userId/predictions/next-actions', this.getNextActionPredictions.bind(this));
38:    this.router.get('/users/:userId/suggestions/folders', this.getFolderSuggestions.bind(this));
39:    this.router.get('/users/:userId/suggestions/folder-names', this.getFolderNameSuggestions.bind(this));
42:    this.router.get('/users/:userId/predictions/future-needs', this.getFutureNeeds.bind(this));
43:    this.router.get('/users/:userId/predictions/tax-season', this.getTaxSeasonPredictions.bind(this));
44:    this.router.get('/users/:userId/predictions/holidays', this.getHolidayPredictions.bind(this));
47:    this.router.get('/users/:userId/cache/recommendations', this.getCacheRecommendations.bind(this));
48:    this.router.get('/users/:userId/cache/should-cache', this.shouldPreCache.bind(this));
=== ./services/predictive-ai/src/index.ts ===
43:app.get('/health', (req, res) => {
=== ./services/mobile-api/src/services/PushNotificationService.ts ===
=== ./services/mobile-api/src/server.ts ===
167:app.get('/health', (req, res) => {
181:app.get('/ready', async (req, res) => {
193:app.get('/api/v1/config', configController.getAppConfig);
194:app.post('/api/v1/config/feature-flag', authMiddleware, configController.updateFeatureFlag);
195:app.get('/api/v1/config/analytics', authMiddleware, configController.getAnalytics);
198:app.post('/api/v1/sync', authMiddleware, syncController.performSync);
199:app.post('/api/v1/sync/batch', authMiddleware, syncController.processBatchOperations);
200:app.post('/api/v1/sync/queue', authMiddleware, syncController.processOfflineQueue);
201:app.post('/api/v1/sync/conflict', authMiddleware, syncController.resolveConflict);
202:app.get('/api/v1/sync/stats/:deviceId', authMiddleware, syncController.getSyncStats);
=== ./services/mobile-api/src/controllers/imageController.ts ===
=== ./services/mobile-api/src/controllers/configController.ts ===
=== ./services/mobile-api/src/controllers/pushController.ts ===
=== ./services/mobile-api/src/controllers/syncController.ts ===
=== ./services/mobile-api/src/controllers/optimizedController.ts ===
=== ./services/mobile-api/src/middleware/compression.ts ===
=== ./services/mobile-api/src/middleware/protocol.ts ===
=== ./services/mobile-api/src/middleware/auth.ts ===
=== ./src/middleware/auth.ts ===

PYTHON_API_ROUTES:
=== ./services/api-gateway/gateway.py ===
14:@app.get("/")
22:@app.get("/health")
35:@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
=== ./services/api-gateway/main.py ===
311:@app.middleware("http")
437:@app.get("/")
454:@app.get("/health")
491:@app.get("/metrics")
501:@app.post("/auth/validate")
516:@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
=== ./services/dmlog-ai-dm/main_service.py ===
553:@app.post("/campaigns")
558:@app.post("/campaigns/{campaign_id}/sessions")
563:@app.post("/sessions/{session_id}/actions")
568:@app.post("/sessions/{session_id}/assistance")
575:@app.delete("/sessions/{session_id}")
580:@app.get("/campaigns/{campaign_id}")
585:@app.get("/health")
595:@app.get("/stats")
=== ./services/dmlog-session/main_service.py ===
307:@app.post("/sessions", response_model=Dict[str, Any])
314:@app.post("/sessions/{session_id}/start")
321:@app.post("/sessions/{session_id}/end")
328:@app.get("/sessions/{session_id}/status")
334:@app.get("/sessions/{session_id}/recap")
343:@app.get("/sessions/{session_id}/analytics")
352:@app.get("/sessions/{session_id}/feedback")
361:@app.websocket("/sessions/{session_id}/realtime")
402:@app.get("/health")
=== ./services/dmlog-templates/main_service.py ===
596:@app.post("/adventures")
603:@app.post("/oneshots")
610:@app.post("/characters/backstories")
617:@app.post("/characters/npcs")
624:@app.post("/encounters/puzzles")
631:@app.post("/encounters/traps")
638:@app.post("/encounters/social")
645:@app.post("/plots/twists")
652:@app.post("/campaigns")
659:@app.post("/encounters/sequences")
=== ./services/workflows/main.py ===
144:@app.get("/")
164:@app.get("/health")
208:@app.get("/metrics")
242:@app.exception_handler(Exception)
263:@app.post("/webhook/{endpoint_id}")
295:@app.get("/marketplace/featured")
311:    @app.post("/dev/reset-db")
323:    @app.get("/dev/test-workflow")
=== ./services/workflows/src/api/routes.py ===
100:@router.post("/workflows", response_model=Dict[str, Any])
150:@router.get("/workflows", response_model=List[Dict[str, Any]])
187:@router.get("/workflows/{workflow_id}", response_model=Dict[str, Any])
228:@router.put("/workflows/{workflow_id}", response_model=Dict[str, Any])
301:@router.delete("/workflows/{workflow_id}", response_model=Dict[str, Any])
336:@router.post("/workflows/{workflow_id}/execute", response_model=Dict[str, Any])
358:@router.get("/workflows/{workflow_id}/executions", response_model=List[Dict[str, Any]])
403:@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
421:@router.post("/executions/{execution_id}/cancel", response_model=Dict[str, Any])
444:@router.post("/workflows/{workflow_id}/webhooks", response_model=Dict[str, Any])
=== ./services/dmlog-core/api/character.py ===
17:@router.post("/", response_model=CharacterSchema)
30:@router.get("/", response_model=List[CharacterSchema])
49:@router.get("/{character_id}", response_model=CharacterSchema)
57:@router.put("/{character_id}", response_model=CharacterSchema)
80:@router.delete("/{character_id}")
95:@router.post("/{character_id}/level-up")
149:@router.get("/{character_id}/summary")
202:@router.post("/{character_id}/damage")
253:@router.post("/{character_id}/heal")
301:@router.get("/templates/", response_model=List[CharacterTemplateSchema])
=== ./services/dmlog-core/api/spell.py ===
19:@router.post("/", response_model=SpellSchema)
32:@router.get("/", response_model=List[SpellSchema])
56:@router.get("/{spell_id}", response_model=SpellSchema)
68:@router.post("/instances/", response_model=SpellInstanceSchema)
81:@router.post("/instances/{instance_id}/cast")
102:@router.get("/characters/{character_id}/spells")
119:@router.post("/characters/{character_id}/resources/", response_model=ResourcePoolSchema)
134:@router.get("/characters/{character_id}/resources/")
150:@router.put("/resources/{pool_id}/consume")
168:@router.put("/resources/{pool_id}/restore")
=== ./services/dmlog-core/api/relationship.py ===
22:@router.post("/characters/", response_model=CharacterSchema)
35:@router.get("/characters/{character_id}", response_model=CharacterSchema)
47:@router.get("/characters/search")
67:@router.post("/", response_model=RelationshipSchema)
80:@router.get("/{relationship_id}", response_model=RelationshipSchema)
92:@router.post("/{relationship_id}/events/", response_model=RelationshipEventSchema)
107:@router.get("/{relationship_id}/history")
124:@router.get("/campaigns/{campaign_id}/graph")
150:@router.get("/characters/{character_id}/analysis")
168:@router.get("/characters/{character_id}/suggestions")
=== ./services/dmlog-core/api/experience.py ===
22:@router.post("/award")
40:@router.post("/calculate")
56:@router.post("/levelup")
72:@router.get("/characters/{character_id}/progression")
85:@router.post("/milestones/", response_model=MilestoneSchema)
98:@router.post("/milestones/{milestone_id}/complete")
117:@router.get("/combat/calculate")
146:@router.get("/tables/xp-by-level")
159:@router.get("/tables/proficiency-bonus")
171:@router.post("/quest/calculate")
=== ./services/dmlog-core/api/campaign.py ===
22:@router.post("/", response_model=CampaignSchema)
35:@router.get("/{campaign_id}", response_model=CampaignSchema)
47:@router.get("/{campaign_id}/summary")
60:@router.post("/{campaign_id}/sessions/", response_model=GameSessionSchema)
75:@router.post("/{campaign_id}/events/", response_model=CampaignEventSchema)
90:@router.post("/{campaign_id}/timeline")
111:@router.post("/{campaign_id}/calendar/", response_model=WorldCalendarSchema)
126:@router.post("/{campaign_id}/calendar/advance")
145:@router.get("/{campaign_id}/statistics")
161:@router.get("/{campaign_id}/events/search")
=== ./services/dmlog-core/api/encounter.py ===
19:@router.post("/", response_model=EncounterSchema)
32:@router.get("/{encounter_id}", response_model=EncounterSchema)
44:@router.get("/")
76:@router.post("/balance/analyze")
105:@router.post("/generate")
121:@router.post("/balance/quick")
161:@router.get("/difficulty/thresholds")
178:@router.get("/cr/{challenge_rating}/xp")
191:@router.get("/multipliers")
203:@router.post("/templates/")
=== ./services/dmlog-core/api/inventory.py ===
22:@router.post("/items/", response_model=ItemSchema)
35:@router.get("/items/{item_id}", response_model=ItemSchema)
47:@router.get("/characters/{character_id}/inventory", response_model=InventorySchema)
69:@router.post("/characters/{character_id}/inventory/", response_model=InventorySchema)
84:@router.post("/inventories/{inventory_id}/items/add")
106:@router.post("/inventories/{inventory_id}/items/remove")
125:@router.post("/transfer")
148:@router.post("/inventories/{inventory_id}/containers/", response_model=ContainerSchema)
163:@router.get("/inventories/{inventory_id}/encumbrance", response_model=EncumbranceCalculation)
177:@router.get("/inventories/{inventory_id}/value")
=== ./services/dmlog-core/api/combat.py ===
19:@router.post("/encounters/", response_model=CombatEncounterSchema)
32:@router.get("/encounters/{encounter_id}", response_model=CombatEncounterSchema)
44:@router.post("/encounters/{encounter_id}/start")
62:@router.post("/encounters/{encounter_id}/next-turn")
80:@router.post("/encounters/{encounter_id}/participants/", response_model=CombatParticipantSchema)
95:@router.post("/encounters/{encounter_id}/actions/")
109:@router.put("/participants/{participant_id}/damage")
129:@router.put("/participants/{participant_id}/heal")
147:@router.post("/participants/{participant_id}/conditions/")
163:@router.delete("/participants/{participant_id}/conditions/{condition_name}")
=== ./services/dmlog-core/api/rules.py ===
22:@router.post("/", response_model=RuleSchema)
35:@router.get("/{rule_id}", response_model=RuleSchema)
57:@router.post("/search")
75:@router.get("/search/suggestions")
96:@router.get("/{rule_id}/related")
114:@router.post("/{rule_id}/interpretations/", response_model=RuleInterpretationSchema)
129:@router.post("/{rule_id}/clarifications/", response_model=RuleClarificationSchema)
144:@router.get("/quick-reference/{game_system}/{category}")
161:@router.get("/conflicts/{game_system}")
180:@router.get("/categories")
=== ./services/dmlog-core/api/dice.py ===
19:@router.post("/roll", response_model=DiceRollResponse)
35:@router.post("/roll/multiple")
53:@router.get("/statistics")
58:@router.get("/history")
70:@router.delete("/history")
76:@router.post("/probability/single")
88:@router.post("/probability/sum")
105:@router.post("/probability/target")
129:@router.post("/probability/advantage")
146:@router.get("/presets")
=== ./services/dmlog-core/api/npc.py ===
19:@router.post("/generate")
35:@router.post("/", response_model=NPCSchema)
48:@router.get("/", response_model=List[NPCSchema])
72:@router.get("/{npc_id}", response_model=NPCSchema)
84:@router.put("/{npc_id}", response_model=NPCSchema)
100:@router.delete("/{npc_id}")
115:@router.post("/{npc_id}/personality/analyze")
131:@router.post("/generate/quick")
159:@router.get("/campaign/{campaign_id}/by-location")
175:@router.get("/campaign/{campaign_id}/by-faction")
=== ./services/dmlog-core/api/loot.py ===
22:@router.post("/generate")
37:@router.post("/generate/quick")
71:@router.post("/tables/", response_model=LootTableSchema)
84:@router.post("/tables/{table_id}/entries/", response_model=LootTableEntrySchema)
99:@router.get("/tables/")
122:@router.post("/tables/{table_id}/generate")
141:@router.get("/treasure/individual/{challenge_rating}")
157:@router.get("/treasure/hoard/{challenge_rating}")
173:@router.post("/currency/generate")
193:@router.post("/items/generate")
=== ./services/dmlog-core/main.py ===
51:@app.middleware("http")
60:@app.exception_handler(ValueError)
67:@app.exception_handler(404)
74:@app.exception_handler(500)
83:@app.get("/health")
94:@app.get("/")
121:@app.on_event("startup")
129:@app.on_event("shutdown")
=== ./services/data-export/main.py ===
105:@app.get("/")
123:@app.get("/health")
152:@app.get("/metrics")
160:@app.get("/exports/progress/{export_id}")
172:@app.delete("/exports/{export_id}")
184:@app.get("/exports/{export_id}/download")
203:@app.exception_handler(HTTPException)
216:@app.exception_handler(Exception)
=== ./services/file-sync/main.py ===
15:@app.get("/")
19:@app.post("/upload")
36:@app.get("/health")
=== ./services/dmlog-characters/main.py ===
85:@app.get("/")
108:@app.get("/health")
114:@app.post("/personality/generate")
127:@app.get("/personality/{character_id}")
144:@app.post("/personality/{character_id}/predict-behavior")
166:@app.post("/voice/synthesize")
197:@app.post("/voice/clone")
213:@app.post("/dialogue/generate")
238:@app.post("/dialogue/banter")
271:@app.post("/memory/create")
=== ./services/backup/main.py ===
130:@app.get("/")
149:@app.get("/health")
200:@app.post("/api/v1/backups/full")
229:@app.post("/api/v1/backups/incremental")
258:@app.get("/api/v1/backups/{job_id}/status")
277:@app.get("/api/v1/backups")
311:@app.post("/api/v1/verification/integrity/{job_id}")
338:@app.post("/api/v1/verification/restore-test/{snapshot_id}")
362:@app.get("/api/v1/verification/history")
377:@app.post("/api/v1/recovery/full")
=== ./services/document-ai/main.py ===
112:@app.get("/health")
145:@app.post("/documents/upload", response_model=DocumentUploadResponse)
236:@app.post("/documents/{job_id}/process")
398:@app.get("/documents/{job_id}/status", response_model=JobStatusResponse)
433:@app.get("/documents/{job_id}/results", response_model=DocumentProcessingResults)
554:@app.post("/search/semantic", response_model=SemanticSearchResponse)
591:@app.post("/search/text", response_model=TextSearchResponse)
618:@app.post("/search/entities", response_model=EntitySearchResponse)
655:@app.get("/analytics", response_model=DocumentAnalytics)
727:@app.get("/config/document-types")
=== ./services/video-pipeline/src/api/main.py ===
98:@app.on_event("startup")
128:@app.on_event("shutdown") 
151:@app.get("/health", response_model=HealthResponse)
164:@app.get("/health/detailed")
170:@app.get("/metrics")
177:@app.get("/api/status")
192:@app.post("/api/videos/upload")
327:@app.get("/api/videos/{video_id}")
357:@app.get("/api/videos/{video_id}/status")
393:@app.get("/api/videos")
=== ./services/video-pipeline/src/core/database.py ===
=== ./services/data-manager/api/endpoints.py ===
66:@router.post("/data/ingest")
85:@router.post("/data/batch-ingest")
114:@router.post("/classify")
130:@router.get("/recommendations/{user_id}")
154:@router.get("/user-profile/{user_id}")
166:@router.post("/user-behavior/{user_id}")
185:@router.get("/insights/{user_id}")
209:@router.get("/analytics/{user_id}")
222:@router.get("/quality/{user_id}")
234:@router.get("/quality/alerts/{user_id}")
=== ./services/batch-import/api/routes.py ===
51:@router.get("/status", response_model=ServiceStatus)
70:@router.get("/stats", response_model=ProcessingStats)
94:@router.get("/pending-files")
107:@router.get("/active-batches")
120:@router.post("/trigger-scan")
141:@router.post("/process-batch")
171:@router.get("/reports")
188:@router.post("/reports/daily")
216:@router.post("/reports/weekly")
244:@router.get("/health-report")
=== ./services/batch-import/main.py ===
53:@app.on_event("startup")
82:@app.on_event("shutdown")
92:@app.get("/")
103:@app.get("/health")
131:@app.get("/stats")
=== ./services/dmlog-battle/main.py ===
53:@app.get("/")
76:@app.get("/health")
83:@app.post("/encounters", response_model=CombatResponse)
110:@app.get("/encounters/{encounter_id}", response_model=CombatResponse)
122:@app.post("/encounters/{encounter_id}/start", response_model=CombatResponse)
143:@app.post("/encounters/{encounter_id}/actions", response_model=CombatResponse)
182:@app.post("/encounters/{encounter_id}/auto-resolve", response_model=CombatResponse)
213:@app.get("/encounters/{encounter_id}/line-of-sight")
258:@app.get("/encounters/{encounter_id}/movement-path")
302:@app.get("/encounters/{encounter_id}/visualization")
=== ./services/metadata/main.py ===
38:@app.get("/")
42:@app.get("/health")
=== ./services/dmlog-player/main_service.py ===
381:@app.get("/health")
388:@app.post("/characters")
398:@app.get("/characters/{character_id}")
407:@app.get("/characters/{character_id}/dashboard")
416:@app.get("/characters/{character_id}/session-prep")
426:@app.post("/characters/{character_id}/journal")
441:@app.get("/characters/{character_id}/journal")
448:@app.post("/characters/{character_id}/inventory")
461:@app.get("/characters/{character_id}/inventory")
467:@app.get("/characters/{character_id}/encumbrance")
=== ./services/mobile-api/api/sync.py ===
74:@router.post("/sync", response_model=Dict[str, Any])
175:@router.get("/sync/status")
201:@router.post("/sync/resolve-conflicts")
237:@router.get("/sync/conflicts")
270:@router.post("/sync/batch")
365:@router.get("/sync/delta/{file_id}")
409:@router.post("/sync/upload-delta/{file_id}")
442:@router.get("/sync/offline-queue")
472:@router.post("/sync/offline-queue")
502:@router.delete("/sync/offline-queue/{operation_id}")
=== ./services/mobile-api/api/auth.py ===
120:@router.post("/login", response_model=Dict[str, Any])
263:@router.post("/refresh", response_model=Dict[str, Any])
347:@router.post("/biometric/setup")
385:@router.post("/biometric/authenticate")
452:@router.post("/logout")
488:@router.get("/me")
515:@router.post("/change-password")
559:@router.get("/devices")
585:@router.delete("/devices/{device_id}")
=== ./services/mobile-api/main.py ===
137:@app.exception_handler(Exception)
153:@app.get("/health")
175:@app.get("/")
205:@app.get("/metrics/mobile")
239:@app.on_event("startup")
=== ./services/dmlog-marketplace/main_service.py ===
224:@app.get("/")
262:@app.get("/adventures/")
277:@app.get("/adventures/{adventure_id}")
285:@app.get("/adventures/featured")
292:@app.get("/art/artists")
312:@app.post("/art/commissions")
346:@app.get("/maps/")
364:@app.get("/maps/featured")
371:@app.get("/audio/")
392:@app.get("/audio/recommendations/{scenario}")
=== ./services/collaboration/main.py ===
88:@app.get("/")
108:@app.get("/health")
149:@app.get("/metrics")
213:@app.exception_handler(Exception)
235:    @app.post("/dev/reset-db")
=== ./services/dmlog-converter/main_service.py ===
346:@app.get("/health")
352:@app.post("/convert")
381:@app.post("/convert/challenge-rating")
397:@app.post("/convert/dc")
413:@app.post("/projects")
428:@app.post("/projects/{project_id}/content")
446:@app.post("/projects/{project_id}/execute")
457:@app.get("/projects/{project_id}")
467:@app.get("/preview")
481:@app.get("/compatibility")
=== ./services/ml-pipeline/src/api/main.py ===
121:@app.get("/health")
160:@app.post("/api/training/classifier", response_model=JobResponse)
199:@app.post("/api/training/embeddings", response_model=JobResponse)
231:@app.post("/api/training/hyperparameter-optimization", response_model=JobResponse)
270:@app.post("/api/training/batch", response_model=JobResponse)
298:@app.post("/api/active-learning/iteration", response_model=JobResponse)
324:@app.post("/api/ab-testing/start", response_model=JobResponse)
349:@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
372:@app.delete("/api/jobs/{job_id}")
395:@app.get("/api/jobs")
=== ./services/dmlog-world/main.py ===
95:@app.get("/health")
105:@app.post("/maps/dungeon", response_model=MapGenerationResponse)
114:@app.post("/maps/settlement", response_model=MapGenerationResponse)
123:@app.post("/maps/region", response_model=MapGenerationResponse)
132:@app.post("/maps/world", response_model=MapGenerationResponse)
142:@app.post("/locations/describe", response_model=LocationDescriptionResponse)
152:@app.post("/weather/generate", response_model=WeatherResponse)
161:@app.post("/weather/query", response_model=WeatherResponse)
175:@app.post("/weather/events/create", response_model=WeatherResponse)
185:@app.post("/calendar/create", response_model=CalendarResponse)
=== ./services/ai-orchestrator/main.py ===
69:@app.get("/")
81:@app.get("/health")
117:@app.get("/plugins")
129:@app.get("/plugins/stats")
136:@app.post("/ai/embeddings")
153:@app.post("/ai/analyze")
171:@app.post("/ai/tags")
188:@app.post("/ai/analyze/image")
206:@app.post("/ai/generate/image")
225:@app.post("/analyze/file")
=== ./services/smart-folders/main.py ===
99:@app.get("/")
116:@app.get("/health")
145:@app.get("/metrics")
153:@app.get("/folders/suggestions/{user_id}")
162:@app.post("/folders/apply-template")
177:@app.post("/folders/refresh/{folder_id}")
188:@app.exception_handler(HTTPException)
201:@app.exception_handler(Exception)
=== ./services/smart-folders/src/api/routes.py ===
59:@router.post("/folders", response_model=Dict[str, Any])
88:@router.get("/folders", response_model=List[Dict[str, Any]])
111:@router.get("/folders/{folder_id}", response_model=Dict[str, Any])
129:@router.get("/folders/{folder_id}/content", response_model=List[Dict[str, Any]])
146:@router.post("/folders/{folder_id}/refresh", response_model=Dict[str, Any])
160:@router.get("/templates", response_model=List[Dict[str, Any]])
177:@router.get("/templates/{template_id}", response_model=Dict[str, Any])
195:@router.get("/templates/{template_id}/preview", response_model=Dict[str, Any])
213:@router.post("/templates/{template_id}/create", response_model=Dict[str, Any])
228:@router.get("/templates/categories", response_model=List[str])
=== ./services/notifications/api/routes.py ===
91:@router.post("/notifications/send")
162:@router.post("/notifications/email")
187:@router.post("/notifications/sms")
209:@router.post("/notifications/webhook")
233:@router.post("/templates")
262:@router.get("/templates")
283:@router.get("/templates/{template_id}")
302:@router.put("/templates/{template_id}")
326:@router.delete("/templates/{template_id}")
345:@router.post("/templates/{template_id}/render")
=== ./services/notifications/main_simple.py ===
94:@app.get("/health")
121:@app.post("/api/v1/notifications")
152:@app.get("/api/v1/users/{user_id}/notifications")
196:@app.post("/api/v1/notifications/{notification_id}/read")
219:@app.get("/api/v1/users/{user_id}/preferences")
246:@app.post("/api/v1/system/broadcast")
273:@app.get("/api/v1/stats")
302:@app.websocket("/api/v1/ws/{user_id}")
=== ./services/notifications/main.py ===
58:@app.on_event("startup")
89:@app.on_event("shutdown")
105:@app.get("/")
124:@app.get("/health")
153:@app.get("/stats")
=== ./services/video-processor/main.py ===
128:@app.get("/health")
150:@app.post("/videos/upload", response_model=VideoUploadResponse)
200:@app.post("/videos/{job_id}/process")
299:@app.get("/jobs/{job_id}/status")
324:@app.get("/jobs/{job_id}/results")
358:@app.post("/search")
398:@app.post("/streaming/sessions")
419:@app.delete("/streaming/sessions/{session_id}")
431:@app.get("/streaming/sessions")
443:@app.get("/streaming/sessions/{session_id}")
=== ./services/cache/api_cache.py ===
467:def get_api_cache() -> APIResponseCache:
481:def cache_api_response(path: str, response_data: Any, ttl: int = None, user_id: str = None):
512:def invalidate_api_cache(paths: List[str] = None, user_id: str = None):
=== ./services/file-watcher/main.py ===
168:@app.get("/health", response_model=HealthResponse)
184:@app.get("/stats", response_model=StatsResponse)
199:@app.get("/config")
218:@app.post("/watch/add")
232:@app.delete("/watch/remove")
246:@app.get("/watch/directories")
256:@app.post("/ignore/add")
276:@app.delete("/ignore/remove")
297:@app.get("/ignore/patterns")
312:@app.post("/rescan")
=== ./services/auth/auth_routes.py ===
18:@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
52:@router.post("/login", response_model=TokenResponse)
86:@router.post("/refresh", response_model=TokenResponse)
133:@router.post("/logout")
142:@router.post("/logout-all")
147:@router.get("/me", response_model=UserResponse)
151:@router.put("/me", response_model=UserResponse)
196:@router.post("/change-password")
228:@router.get("/users", response_model=List[UserResponse])
233:@router.get("/users/{user_id}", response_model=UserResponse)
=== ./services/auth/main.py ===
35:@app.get("/")
39:@app.get("/health")
43:@app.get("/protected")
47:@app.get("/admin-only")
=== ./services/main.py ===
28:@app.post("/metadata")
55:@app.get("/metadata/{file_id}")
70:@app.get("/search")
93:@app.get("/")
=== ./services/analytics/api/routes.py ===
50:@router.get("/metrics/dashboard", response_model=MetricsResponse)
64:@router.get("/metrics/top")
79:@router.get("/metrics/file-types")
93:@router.post("/usage/track/file-upload")
135:@router.post("/usage/track/api-call")
136:async def track_api_call(
177:@router.get("/usage/user/{user_id}", response_model=UsageStatsResponse)
198:@router.get("/usage/tenant/{tenant_id}")
212:@router.get("/usage/global")
226:@router.post("/costs/track/ai-operation")
=== ./services/analytics/main_simple.py ===
106:@app.get("/health")
113:@app.post("/api/v1/metrics/file-upload")
130:@app.post("/api/v1/metrics/api-call")
131:async def track_api_call(metric: APICallMetric):
148:@app.post("/api/v1/metrics/ai-operation")
176:@app.get("/api/v1/reports/usage")
199:@app.get("/api/v1/reports/cost")
223:@app.get("/api/v1/dashboard/overview")
237:@app.get("/api/v1/dashboard/charts")
251:@app.get("/api/v1/dashboard/top-users")
=== ./services/analytics/main.py ===
122:@app.get("/health")
129:@app.post("/api/v1/metrics/file-upload")
146:@app.post("/api/v1/metrics/api-call")
147:async def track_api_call(metric: APICallMetric):
164:@app.post("/api/v1/metrics/ai-operation")
192:@app.get("/api/v1/reports/usage")
215:@app.get("/api/v1/reports/cost")
239:@app.get("/api/v1/dashboard/overview")
253:@app.get("/api/v1/dashboard/charts")
267:@app.get("/api/v1/dashboard/top-users")
=== ./services/sync-engine/main.py ===
270:@app.get("/")
287:@app.get("/health")
333:@app.post("/sync/upload")
388:@app.get("/sync/status/{job_id}")
433:@app.get("/sync/queue/stats")
457:@app.get("/sync/workers/stats")
471:@app.post("/sync/rules")
478:@app.get("/sync/rules")
485:@app.put("/sync/rules/{rule_id}")
492:@app.delete("/sync/rules/{rule_id}")
=== ./optimizations/caching/cache_headers.py ===
438:    def get_api_data_cache_config() -> CacheConfig:
531:    @app.middleware("http")
=== ./optimizations/cdn/static_serving.py ===
=== ./optimizations/compression/request_compression.py ===
=== ./dev-tools/visualization/dependency_visualizer.py ===
297:    def _find_api_calls(self, content: str, service_info: ServiceInfo):
386:            r'@app\.route\s*\(\s*["\']([^"\']+)["\']',  # Flask
387:            r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',  # FastAPI
=== ./dev-tools/templates/service_templates/fastapi/main.py ===
43:@app.on_event("startup")
51:@app.on_event("shutdown")
57:@app.get("/health", response_model=HealthResponse)
68:@app.get("/info", response_model=ServiceInfoResponse)
81:@app.get("/")
88:@app.get("/api/v1/{{SERVICE_NAME_KEBAB}}")
95:@app.post("/api/v1/{{SERVICE_NAME_KEBAB}}")
=== ./dev-tools/templates/service_templates/flask/app.py ===
26:@app.route('/health', methods=['GET'])
37:@app.route('/info', methods=['GET'])
49:@app.route('/', methods=['GET'])
58:@app.route('/api/v1/{{SERVICE_NAME_KEBAB}}', methods=['GET'])
67:@app.route('/api/v1/{{SERVICE_NAME_KEBAB}}', methods=['POST'])
=== ./dev-tools/templates/generate_service.py ===
351:    def _generate_test_api(self, template_vars: Dict[str, Any]) -> str:
375:def test_api_endpoints(client, auth_headers):
597:def create_fastapi_template(template_dir: Path):
644:@app.on_event("startup")
652:@app.on_event("shutdown")
658:@app.get("/health", response_model=HealthResponse)
669:@app.get("/info", response_model=ServiceInfoResponse)
682:@app.get("/")
689:@app.get("/api/v1/{{SERVICE_NAME_KEBAB}}")
696:@app.post("/api/v1/{{SERVICE_NAME_KEBAB}}")
=== ./security-audit/tools/input_sanitization.py ===
=== ./security/audit/audit-logger.py ===
=== ./security/secrets/rotation-service.py ===
=== ./security/api-keys/api-key-service.py ===
178:    def _generate_api_key(self) -> tuple[str, str, str]:
195:    def _verify_api_key(self, provided_key: str, stored_hash: str) -> bool:
199:    async def create_api_key(self, request: CreateAPIKeyRequest, user_id: str, organization_id: str) -> tuple[str, APIKey]:
255:    async def validate_api_key(self, provided_key: str, ip_address: str = None) -> Optional[APIKey]:
327:    async def _check_rate_limit(self, api_key_id: str, rate_limit: int, rate_window: int) -> bool:
358:    async def _update_last_used(self, api_key_id: str):
366:    async def _update_key_status(self, api_key_id: str, status: APIKeyStatus):
372:    async def get_user_api_keys(self, user_id: str) -> List[APIKey]:
403:    async def update_api_key(self, api_key_id: str, user_id: str, request: UpdateAPIKeyRequest) -> Optional[APIKey]:
489:    async def get_api_key(self, api_key_id: str, user_id: str) -> Optional[APIKey]:
=== ./security/scanning/vulnerability-scanner.py ===
=== ./security/headers/security-headers.py ===
=== ./security/auth/two-factor-auth.py ===
=== ./generate_audit_report.py ===
110:                endpoints = re.findall(r'@app\.route\(["\']([^"\']+)["\']', content)
=== ./edge/management-dashboard/dashboard.py ===
544:        @self.app.route('/')
548:        @self.app.route('/api/devices')
549:        def api_devices():
553:        @self.app.route('/api/devices/<device_id>')
554:        def api_device_detail(device_id):
569:        @self.app.route('/api/devices/<device_id>/metrics')
570:        def api_device_metrics(device_id):
575:        @self.app.route('/api/devices/<device_id>/command', methods=['POST'])
576:        def api_device_command(device_id):
590:        @self.app.route('/api/events')
=== ./sdk/marketplace/api.py ===
284:@app.post("/plugins", response_model=PluginResponse)
371:@app.get("/plugins", response_model=PluginSearchResponse)
452:@app.get("/plugins/{plugin_id}", response_model=PluginResponse)
464:@app.put("/plugins/{plugin_id}", response_model=PluginResponse)
494:@app.delete("/plugins/{plugin_id}")
524:@app.post("/plugins/{plugin_id}/install")
562:@app.delete("/plugins/{plugin_id}/install")
584:@app.get("/plugins/{plugin_id}/download")
620:@app.post("/plugins/{plugin_id}/reviews", response_model=ReviewResponse)
678:@app.get("/plugins/{plugin_id}/reviews")
=== ./production/configs/rate-limiting/rate_limiter.py ===
365:    @app.before_request
409:    @app.after_request
=== ./production/configs/tracing/correlation-middleware.py ===
=== ./production/health/health_checker.py ===
601:    @app.route('/health')
615:    @app.route('/health/<check_name>')
632:    @app.route('/health/status')
=== ./docs/api/openapi-generator.py ===
20:    def __init__(self, base_output_dir: str = "./openapi"):
55:    async def fetch_openapi_spec(self, service_name: str, port: int) -> Dict:
75:    def enhance_openapi_spec(self, spec: Dict, service_name: str, description: str) -> Dict:
262:    def generate_api_index(self, results: Dict[str, bool]):
=== ./docs/inline-docs/auth-service-docs.py ===
234:@app.get(
285:@app.get(
443:@app.get(
513:@app.get(
607:@app.exception_handler(HTTPException)
633:@app.exception_handler(Exception)
=== ./tests/docker/mock_server.py ===
API_ENDPOINTS_END

[0;32m=== 5. DATABASE ANALYSIS ===[0m
DATABASE_ANALYSIS_START
DATABASE_FILES:
./docker/postgres/init/01-init-database.sql
./migrations
./migrations/001_create_indexes.sql
./migrations/002_partitioning.sql
./migrations/003_materialized_views.sql
./migrations/004_backup_restore.sql
./migrations/005_vector_optimization.sql
./migrations/006_connection_pooling.sql
./migrations/data-transform/schema_migrator.py
./migrations/database-migration
./migrations/database-migration/sample_migrations
./migrations/database-migration/sample_migrations/V20250822_000001__create_users_table.sql
./migrations/database-migration/sample_migrations/V20250822_000002__create_activity_logs_table.sql
./migrations/run_migrations.sh
./migrations/schema-migrations
./production/database/optimization/create_indexes.sql
./production/database/optimization/query_optimization.sql
./scripts/init.sql
./security/audit/scripts/init.sql
./security/secrets/scripts/init.sql
./services/activeledger/migrations
./services/auth/__pycache__/schemas.cpython-310.pyc
./services/auth/schemas.py
./services/graphql/src/schema
./services/metadata/__pycache__/schemas.cpython-310.pyc
./services/metadata/schemas.py
./services/video-pipeline/migrations
./tests/unit/test_database_migrations.py

DATABASE_CONFIGURATIONS:
./monitoring/performance-regression/config.yaml
./services/sync-v2/config/default.json
./services/graphql/.env.example
./services/activeledger/package.json
./services/dmlog-ai-dm/config.py
./services/dmlog-session/config.py
./services/workflows/src/core/config.py
./services/dmlog-core/config.py
./services/data-export/src/core/config.py
./services/dmlog-characters/config.py

DATABASE_MODELS:
./services/quantum-ready/simulation/quantum_simulation.py
./services/quantum-ready/ml/quantum_ml_prep.py
./services/dmlog-ai-dm/main_service.py
./services/dmlog-ai-dm/models/base.py
./services/dmlog-session/main_service.py
./services/dmlog-session/models/scheduling.py
./services/dmlog-session/models/session.py
./services/dmlog-session/models/content.py
./services/dmlog-session/models/base.py
./services/dmlog-session/models/tabletop.py
DATABASE_ANALYSIS_END

[0;32m=== 6. DOCKER ANALYSIS ===[0m
DOCKER_ANALYSIS_START
DOCKER_FILES:
./dev-tools/templates/service_templates/fastapi/Dockerfile
./docker-compose.https.yml
./docker-compose.monitoring.yml
./docker-compose.prod.yml
./docker-compose.test.yml
./docker-compose.yml
./docker/backend/Dockerfile
./docker/frontend/Dockerfile
./docker/ml-pipeline/Dockerfile
./docker/nginx/Dockerfile
./docker/postgres/Dockerfile
./docs/deployment/docker-compose.md
./frontend/Dockerfile
./infrastructure/mesh/docker-compose.yml
./logging/Dockerfile.fluentd
./monitoring/docker-compose.yml
./monitoring/performance-regression/Dockerfile
./optimizations/docker/Dockerfile.optimized
./optimizations/docker/docker-compose.optimized.yml
./sdk/runtime/Dockerfile.plugin-base
./security/audit/Dockerfile
./security/audit/docker-compose.yml
./security/auth/docker-compose.yml
./security/scanning/docker-compose.yml
./security/secrets/Dockerfile
./security/secrets/docker-compose.yml
./services/ai_orchestrator/Dockerfile
./services/api_gateway/Dockerfile
./services/auth/Dockerfile
./services/dmlog-core/Dockerfile
./services/file-watcher/Dockerfile
./services/file-watcher/docker-compose.yml
./services/file_processor/Dockerfile
./services/metadata/Dockerfile
./services/ml-pipeline/Dockerfile
./services/ml-pipeline/docker-compose.yml
./services/notification/Dockerfile
./services/video-pipeline/Dockerfile
./services/video-pipeline/docker-compose.yml
./services/video-processor/Dockerfile
./tests/docker/Dockerfile.mock-services
./tests/docker/Dockerfile.test-runner

DOCKER_COMPOSE_SERVICES:
=== docker-compose.yml ===
services:
  postgres:
    image: pgvector/pgvector:pg15
    container_name: activelog-postgres
    environment:
      POSTGRES_DB: activelog

RUNNING_CONTAINERS:
CONTAINER ID   IMAGE                 COMMAND                  CREATED      STATUS                         PORTS                                         NAMES
d51a83ef8f99   guacamole/guacamole   "/opt/guacamole/bin/…"   2 days ago   Up 30 hours                    0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp   guacamole
cedf8d1bc94b   mariadb               "docker-entrypoint.s…"   2 days ago   Up 30 hours                    3306/tcp                                      guac-db
5cd93812a5d8   guacamole/guacd       "/opt/guacamole/entr…"   2 days ago   Up 30 hours (healthy)          4822/tcp                                      guacd
38f6c13320a3   nginx:latest          "/docker-entrypoint.…"   2 days ago   Restarting (1) 8 seconds ago                                                 guac-nginx

DOCKER_IMAGES:
activelog-backend-activelog-api                 latest        cabf6578742e   5 days ago      246MB
activelog-backend-activelog-worker              latest        0a339da19c24   5 days ago      207MB
activelog-backend-api                           latest        2dd3f9c9b6a5   6 days ago      271MB
activelog-backend-worker                        latest        ec2ac4866dc9   6 days ago      222MB
DOCKER_ANALYSIS_END

[0;32m=== 7. CONFIGURATION FILES ===[0m
CONFIG_ANALYSIS_START
CONFIGURATION_FILES:
./.claude/settings.local.json
./.github/workflows/ci.yml
./.github/workflows/performance.yml
./.github/workflows/security-scan.yml
./.github/workflows/security.yml
./.github/workflows/test.yml
./app-factory/base/package.json
./app-factory/configs
./app-factory/configs/businesslog.json
./app-factory/configs/capitaine.json
./app-factory/configs/cocapn.json
./app-factory/configs/dmlog.json
./app-factory/configs/fishinglog.json
./app-factory/configs/makerlog.json
./app-factory/configs/personallog.json
./app-factory/configs/playerlog.json
./app-factory/configs/reallog.json
./app-factory/configs/studylog.json
./app-factory/settings
./config
./deployment/stores/metadata/activeledger-store.yaml
./deployment/stores/metadata/activelog-ai-store.yaml
./deployment/stores/metadata/activelog-app-store.yaml
./dev-tools/cli/config.yml
./dev-tools/templates/service_templates/fastapi/config.py
./docker-compose.https.yml
./docker-compose.monitoring.yml
./docker-compose.prod.yml
./docker-compose.test.yml
./docker-compose.yml
./docs/configuration
./frontend/package.json
./frontend/src/components/settings
./infrastructure/mesh/configs
./infrastructure/mesh/configs/mesh-config.yaml
./infrastructure/mesh/consul/consul-agent.json
./infrastructure/mesh/consul/consul-server.json
./infrastructure/mesh/deployments/blue-green-config.yaml
./infrastructure/mesh/deployments/blue-green-deployments.yaml
./infrastructure/mesh/deployments/canary-config.yaml
./infrastructure/mesh/deployments/canary-deployments.yaml
./infrastructure/mesh/docker-compose.yml
./infrastructure/mesh/envoy/envoy.yaml
./infrastructure/mesh/routing/traffic-routing.yaml
./migrations/config
./modules/BusinessLog/package.json
./modules/DMLog/package.json
./modules/FishingLog/package.json
./modules/MakerLog/package.json
./modules/Marine/package.json
./modules/PlayerLog/package.json
./modules/RealLog/package.json
./modules/StudyLog/package.json
./modules/healthcare/src/core/config.py
./monitoring/alertmanager.yml
./monitoring/alertmanager/alertmanager.yml
./monitoring/blackbox.yml
./monitoring/configs
./monitoring/dashboards/activelog-overview.json
./monitoring/dashboards/distributed-tracing.json
./monitoring/dashboards/file-service.json
./monitoring/dashboards/graphql-service.json
./monitoring/dashboards/infrastructure-overview.json
./monitoring/dashboards/mobile-api.json
./monitoring/dashboards/services-health.json
./monitoring/docker-compose.yml
./monitoring/grafana/dashboards/activelog-overview.json
./monitoring/grafana/dashboards/dashboard.yml
./monitoring/grafana/dashboards/dashboards.yml
./monitoring/grafana/datasources/datasources.yml
./monitoring/grafana/datasources/prometheus.yml
./monitoring/jaeger/jaeger-config.yml
./monitoring/jaeger/sampling_strategies.json
./monitoring/loki/loki-config.yml
./monitoring/loki/promtail-config.yml
./monitoring/otel/otel-collector-config.yml
./monitoring/performance-regression/config.yaml
./monitoring/prometheus.yml
./monitoring/prometheus/blackbox.yml
./monitoring/prometheus/prometheus.yml
./monitoring/prometheus/rules/alerting_rules.yml
./monitoring/rules/activelog-alerts.yml
./monitoring/service-mesh/istio-telemetry.yaml
./monitoring/service-mesh/service-monitor.yaml
./monitoring/tempo/tempo-config.yml
./monitoring/thanos/bucket_config.yaml
./optimizations/docker/docker-compose.optimized.yml
./production/backup/config
./production/backup/config/config_backup.sh
./production/configs
./production/configs/production.yml
./production/monitoring/grafana/dashboards/activelog-production.json
./sdk/examples/data-visualization/manifest.json
./sdk/examples/social-media-import/manifest.json
./sdk/examples/weather-plugin/manifest.json
./sdk/specs/plugin-manifest.json
./sdk/typescript/package.json
./sdk/typescript/tsconfig.json
./security-audit/configs
./security-audit/configs/api_key_rotation_config.yaml
./security-audit/reports/bandit_scan_20250822_094522.json
./security/audit/docker-compose.yml
./security/auth/docker-compose.yml
./security/configs
./security/ddos/ddos-protection.yaml
./security/headers/configs
./security/headers/configs/security-headers.yaml
./security/scanning/docker-compose.yml
./security/secrets/configs
./security/secrets/configs/rotation-config.yaml
./security/secrets/docker-compose.yml
./security/waf/waf-rules.yaml
./services/activeledger/config
./services/activeledger/config/settings.py
./services/activeledger/package.json
./services/activeledger/src/config
./services/activeledger/tsconfig.json
./services/ai-orchestrator/.env.example
./services/ai-orchestrator/plugins/config.py
./services/ai-tools/config
./services/ai-tools/config/settings.py
./services/analytics/core/__pycache__/config.cpython-310.pyc
./services/analytics/core/config.py
./services/backup/config
./services/backup/core/config.py
./services/batch-import/core/config.py
./services/blockchain/config
./services/collaboration/src/core/config.py
./services/data-export/.env.example
./services/data-export/package.json
./services/data-export/src/config
./services/data-export/src/config/config.js
./services/data-export/src/core/config.py
./services/data-manager/config
./services/dmlog-ai-dm/config.py
./services/dmlog-battle/__pycache__/config.cpython-310.pyc
./services/dmlog-battle/config.py
./services/dmlog-characters/config.py
./services/dmlog-converter/config
./services/dmlog-core/config.py
./services/dmlog-marketplace/config
./services/dmlog-player/config
./services/dmlog-session/config.py
./services/dmlog-templates/config.py
./services/dmlog-world/config.py
./services/document-ai/.env.example
./services/document-ai/config
./services/document-ai/core/config.py
./services/document-ai/package.json
./services/document-ai/src/config
./services/document-ai/src/config/config.js
./services/file-watcher/.env.example
./services/file-watcher/config.py
./services/file-watcher/docker-compose.yml
./services/graphql/.env.example
./services/graphql/package.json
./services/graphql/tsconfig.json
./services/ml-pipeline/.env.example
./services/ml-pipeline/docker-compose.yml
./services/ml-pipeline/src/config
./services/ml-pipeline/src/utils/config.py
./services/mobile-api/.env.example
./services/mobile-api/config
./services/mobile-api/core/config.py
./services/mobile-api/package.json
./services/mobile-api/src/controllers/configController.ts
./services/mobile-api/src/types/config.ts
./services/mobile-api/tsconfig.json
./services/notifications/core/__pycache__/config.cpython-310.pyc
./services/notifications/core/config.py
./services/p2p-sync/core/config.py
./services/predictive-ai/package.json
./services/predictive-ai/tsconfig.json
./services/smart-folders/src/core/config.py
./services/sync-engine/.env.example
./services/sync-v2/config
./services/sync-v2/config/default.json
./services/video-pipeline/.env.example
./services/video-pipeline/config
./services/video-pipeline/config/settings.py
./services/video-pipeline/docker-compose.yml
./services/video-processor/.env.example
./services/video-processor/config
./services/video-processor/core/config.py
./services/video-processor/package.json
./services/video-processor/src/config
./services/video-processor/src/config/config.js
./services/workflows/src/core/config.py

ENVIRONMENT_FILES:
./services/ai-orchestrator/.env.example
./services/data-export/.env.example
./services/document-ai/.env.example
./services/file-watcher/.env.example
./services/graphql/.env.example
./services/ml-pipeline/.env.example
./services/mobile-api/.env.example
./services/sync-engine/.env.example
./services/video-pipeline/.env.example
./services/video-processor/.env.example

CONFIG_FILE_SIZES:
-rw-rw-r-- 1 activeloguser activeloguser 627K Aug 22 09:45 ./security-audit/reports/bandit_scan_20250822_094522.json
-rw-rw-r-- 1 activeloguser activeloguser 25K Aug 22 08:47 ./security/ddos/ddos-protection.yaml
-rw-rw-r-- 1 activeloguser activeloguser 18K Aug 22 08:22 ./monitoring/prometheus/rules/alerting_rules.yml
-rw-rw-r-- 1 activeloguser activeloguser 18K Aug 21 20:44 ./.github/workflows/ci.yml
-rw-rw-r-- 1 activeloguser activeloguser 17K Aug 22 09:34 ./.github/workflows/test.yml
-rw-rw-r-- 1 activeloguser activeloguser 16K Aug 22 09:35 ./production/configs/production.yml
-rw-rw-r-- 1 activeloguser activeloguser 16K Aug 21 20:49 ./docker-compose.prod.yml
-rw-rw-r-- 1 activeloguser activeloguser 15K Aug 22 09:35 ./.github/workflows/performance.yml
-rw-rw-r-- 1 activeloguser activeloguser 15K Aug 22 08:30 ./infrastructure/mesh/envoy/envoy.yaml
-rw-rw-r-- 1 activeloguser activeloguser 15K Aug 22 00:43 ./monitoring/dashboards/mobile-api.json
-rw-rw-r-- 1 activeloguser activeloguser 15K Aug 22 00:43 ./monitoring/dashboards/file-service.json
-rw-rw-r-- 1 activeloguser activeloguser 15K Aug 22 00:41 ./monitoring/dashboards/graphql-service.json
-rw-rw-r-- 1 activeloguser activeloguser 14K Aug 22 08:46 ./security/waf/waf-rules.yaml
-rw-rw-r-- 1 activeloguser activeloguser 14K Aug 22 08:35 ./infrastructure/mesh/routing/traffic-routing.yaml
-rw-rw-r-- 1 activeloguser activeloguser 13K Aug 22 08:34 ./infrastructure/mesh/deployments/canary-config.yaml
-rw-rw-r-- 1 activeloguser activeloguser 13K Aug 22 08:25 ./monitoring/docker-compose.yml
-rw-rw-r-- 1 activeloguser activeloguser 13K Aug 21 20:52 ./monitoring/grafana/dashboards/activelog-overview.json
-rw-rw-r-- 1 activeloguser activeloguser 12K Aug 22 08:32 ./infrastructure/mesh/deployments/blue-green-config.yaml
-rw-rw-r-- 1 activeloguser activeloguser 11K Aug 22 08:34 ./infrastructure/mesh/deployments/canary-deployments.yaml
-rw-rw-r-- 1 activeloguser activeloguser 11K Aug 22 00:40 ./monitoring/dashboards/activelog-overview.json
CONFIG_ANALYSIS_END

[0;32m=== 8. ENVIRONMENT VARIABLES ===[0m
ENV_ANALYSIS_START
ENVIRONMENT_VARIABLE_USAGE:
        url: process.env.ANALYTICS_SERVICE_URL
        url: process.env.FILE_SERVICE_URL
        url: process.env.PLUGIN_SERVICE_URL
        url: process.env.USER_SERVICE_URL
        url: process.env.VIDEO_SERVICE_URL
      ...(process.env.ANALYTICS_SERVICE_URL ? [{
      ...(process.env.FILE_SERVICE_URL ? [{
      ...(process.env.PLUGIN_SERVICE_URL ? [{
      ...(process.env.USER_SERVICE_URL ? [{
      ...(process.env.VIDEO_SERVICE_URL ? [{
      ...process.env,
    console.log(`📊 Rate limiting: ${process.env.RATE_LIMIT_MAX || 1000} requests per 15 minutes`);
    console.log(`🔒 Authentication: ${process.env.JWT_SECRET ? 'Enabled' : 'Disabled'}`);
    version: () => process.env.npm_package_version || '1.0.0',
    version: process.env.npm_package_version || '1.0.0'
  const useGateway = process.env.USE_GATEWAY === 'true' && process.env.NODE_ENV === 'production';
  host: process.env.REDIS_HOST || 'localhost',
  max: process.env.RATE_LIMIT_MAX ? parseInt(process.env.RATE_LIMIT_MAX) : 1000,
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  password: process.env.REDIS_PASSWORD,

ENV_FILE_VARIABLES:

MISSING_ENV_REFERENCES:
ENV_ANALYSIS_END

[0;32m=== 9. DISK USAGE ANALYSIS ===[0m
DISK_USAGE_START
SERVICE_DIRECTORY_SIZES:
756K	services/document-ai
680K	services/manufacturing
604K	services/dmlog-core
592K	services/dmlog-templates
592K	services/data-manager
572K	services/activeledger
556K	services/social-ai
548K	services/dmlog-characters
520K	services/data-export
508K	services/education-ai
504K	services/mobile-api
500K	services/universal-translator
496K	services/video-processor
480K	services/dmlog-session
476K	services/blockchain
468K	services/simulation
468K	services/quantum-ready
452K	services/predictive-ai
444K	services/dmlog-converter
444K	services/collaboration
432K	services/notifications
428K	services/analytics
412K	services/dmlog-world
408K	services/ml-pipeline
408K	services/dmlog-battle
400K	services/dmlog-marketplace
384K	services/workflows
384K	services/ai-tools
380K	services/health-integration
368K	services/security-advanced
356K	services/marine-advanced
332K	services/video-pipeline
332K	services/dmlog-ai-dm
316K	services/smart-folders
312K	services/backup
308K	services/sync-v2
308K	services/memory-preservation
296K	services/ai-orchestrator
292K	services/ads
276K	services/graphql
256K	services/dmlog-player
256K	services/ar-layer
236K	services/quantum-reality
232K	services/batch-import
196K	services/creative-suite
192K	services/emotional-ai
184K	services/sync-engine
184K	services/metadata
156K	services/gaming-platform
148K	services/file-watcher
148K	services/cache
144K	services/time-machine
132K	services/ambient
88K	services/p2p-sync
80K	services/predictive
80K	services/biological
80K	services/auth
72K	services/multiverse
44K	services/api-gateway
20K	services/file-sync
8.0K	services/notification
8.0K	services/file_processor
8.0K	services/api_gateway
8.0K	services/ai_orchestrator
8.0K	services/__pycache__
4.0K	services/main.py
4.0K	services/cognitive

LARGEST_FILES:

DISK_USAGE_BY_TYPE:
Python files:
Total: 17.6147 MB
JavaScript files:
Total: 0 MB
JSON files:
Total: 0.838073 MB
DISK_USAGE_END

[0;32m=== 10. PROJECT STRUCTURE ===[0m
PROJECT_TREE_START
PROJECT_TREE:
.
./config
./monitoring
./monitoring/alertmanager
./monitoring/configs
./monitoring/dashboards
./monitoring/grafana
./monitoring/grafana/dashboards
./monitoring/grafana/datasources
./monitoring/jaeger
./monitoring/loki
./monitoring/otel
./monitoring/performance-regression
./monitoring/prometheus
./monitoring/prometheus/rules
./monitoring/rules
./monitoring/scripts
./monitoring/service-mesh
./monitoring/tempo
./monitoring/thanos
./monitoring/vector
./services
./services/graphql
./services/graphql/scripts
./services/graphql/src
./services/graphql/src/dataloaders
./services/graphql/src/schema
./services/notification
./services/quantum-ready
./services/quantum-ready/algorithms
./services/quantum-ready/annealing
./services/quantum-ready/communication
./services/quantum-ready/crypto
./services/quantum-ready/encryption
./services/quantum-ready/ml
./services/quantum-ready/optimization
./services/quantum-ready/pipelines
./services/quantum-ready/random
./services/quantum-ready/security
./services/quantum-ready/sensing
./services/quantum-ready/simulation
./services/sync-v2
./services/sync-v2/config
./services/sync-v2/core
./services/sync-v2/docs
./services/sync-v2/protocols
./services/sync-v2/realtime
./services/sync-v2/resolution
./services/sync-v2/strategies
./services/sync-v2/tests

DIRECTORY_STRUCTURE:
.
./.claude
./.github
./.github/workflows
./app-factory
./app-factory/ai-models
./app-factory/ai-models/models
./app-factory/apps
./app-factory/apps/business
./app-factory/apps/capitaine
./app-factory/apps/cocapn
./app-factory/apps/dm
./app-factory/apps/fishing
./app-factory/apps/maker
./app-factory/apps/personal
./app-factory/apps/player
./app-factory/apps/real
./app-factory/apps/study
./app-factory/auth
./app-factory/auth/providers
./app-factory/base
./app-factory/base/src
./app-factory/build
./app-factory/configs
./app-factory/data
./app-factory/data-sync
./app-factory/docs
./app-factory/settings
./app-factory/shared
./app-factory/sync
./app-factory/templates
./app-factory/tests
./app-factory/themes
./app-factory/themes/layouts
./app-factory/themes/themes
./app-factory/utils
./config
./data
./deploy
./deployment
./deployment/stores
./deployment/stores/android
./deployment/stores/ios
./deployment/stores/legal
./deployment/stores/metadata
./deployment/stores/screenshots
./deployment/stores/scripts
./dev-tools
./dev-tools/cli
./dev-tools/debug
./dev-tools/formatting
./dev-tools/logging
./dev-tools/profiling
./dev-tools/setup
./dev-tools/templates
./dev-tools/templates/service_templates
./dev-tools/visualization
./docker
./docker/backend
./docker/frontend
./docker/ml-pipeline
./docker/nginx
./docker/postgres
./docker/postgres/init
./docs
./docs/api
./docs/architecture
./docs/configuration
./docs/deployment
./docs/developer
./docs/inline-docs
./docs/plugins
./docs/troubleshooting
./docs/user-guides
./edge
./edge/camera-firmware
./edge/dashboard
./edge/device-discovery
./edge/discovery
./edge/integrations
./edge/iot-integration
./edge/jetson-nano
./edge/management-dashboard
./edge/management-dashboard/templates
./edge/monitoring
./edge/offline-sync
./edge/power-management
./edge/power-mgmt
./edge/raspberry-pi
./edge/security
./edge/sync
./frontend
./frontend/src
./frontend/src/components
./frontend/src/styles
./frontend/src/utils
./import-queue
./infrastructure
./infrastructure/mesh
./infrastructure/mesh/configs
./infrastructure/mesh/consul
./infrastructure/mesh/deployments
./infrastructure/mesh/envoy
./infrastructure/mesh/routing
./infrastructure/mesh/scripts
./infrastructure/mesh/templates
./infrastructure/terraform
./infrastructure/terraform/modules
./logging
./logs
./migrations
./migrations/anonymization
./migrations/config
./migrations/data-export
./migrations/data-import
./migrations/data-transform
./migrations/database-migration
./migrations/database-migration/sample_migrations
./migrations/logs
./migrations/rollback
./migrations/schema-migrations
./migrations/temp
./migrations/validation
./modules
./modules/BusinessLog
./modules/DMLog
./modules/DMLog/core
./modules/DMLog/examples
./modules/DMLog/systems
./modules/DMLog/tests
./modules/FishingLog
./modules/MakerLog
./modules/Marine
./modules/PlayerLog
./modules/RealLog
./modules/StudyLog
./modules/healthcare
./modules/healthcare/audit
./modules/healthcare/consent
./modules/healthcare/device-api
./modules/healthcare/dicom
./modules/healthcare/hipaa
./modules/healthcare/hl7-fhir
./modules/healthcare/nlp
./modules/healthcare/src
./modules/legal
./modules/legal/citations
./modules/legal/contracts
./modules/legal/custody
./modules/legal/ediscovery
./modules/legal/holds
./modules/legal/matter
./modules/legal/matters
./modules/legal/redaction
./monitoring
./monitoring/alertmanager
./monitoring/configs
./monitoring/dashboards
./monitoring/grafana
./monitoring/grafana/dashboards
./monitoring/grafana/datasources
./monitoring/jaeger
./monitoring/loki
./monitoring/otel
./monitoring/performance-regression
./monitoring/prometheus
./monitoring/prometheus/rules
./monitoring/rules
./monitoring/scripts
./monitoring/service-mesh
./monitoring/tempo
./monitoring/thanos
./monitoring/vector
./nginx
./optimizations
./optimizations/benchmarks
./optimizations/caching
./optimizations/cdn
./optimizations/compression
./optimizations/database
./optimizations/docker
./optimizations/docker/nginx
./optimizations/pagination
./pids
./production
./production/backup
./production/backup/config
./production/backup/database
./production/backup/disaster-recovery
./production/backup/files
./production/backup/logs
./production/backup/monitoring
./production/backup/redis
./production/backup/scripts
./production/backup/verify
./production/caching
./production/configs
./production/configs/nginx
./production/configs/rate-limiting
./production/configs/resilience
./production/configs/tracing
./production/database
./production/database/optimization
./production/database/scripts
./production/deployment
./production/health
./production/logs
./production/logs/conf.d
./production/monitoring
./production/monitoring/grafana
./production/scripts
./production/secrets
./scripts
./sdk
./sdk/docs
./sdk/examples
./sdk/examples/data-visualization
./sdk/examples/social-media-import
./sdk/examples/weather-plugin
./sdk/marketplace
./sdk/python
./sdk/python/activelog_plugin_sdk
./sdk/python/docs
./sdk/python/tests
./sdk/runtime
./sdk/specs
./sdk/typescript
./sdk/typescript/src
./secrets
./security
./security-audit
./security-audit/configs
./security-audit/configs/certificates
./security-audit/reports
./security-audit/scripts
./security-audit/tests
./security-audit/tools
./security/2fa
./security/api-keys
./security/audit
./security/audit/scripts
./security/auth
./security/configs
./security/ddos
./security/headers
./security/headers/configs
./security/headers/nginx
./security/policies
./security/scanning
./security/scripts
./security/secrets
./security/secrets/configs
./security/secrets/scripts
./security/vulnerability-scanning
./security/waf
./services
./services/__pycache__
./services/activeledger
./services/activeledger/api
./services/activeledger/config
./services/activeledger/controllers
./services/activeledger/middleware
./services/activeledger/migrations
./services/activeledger/models
./services/activeledger/services
./services/activeledger/src
./services/activeledger/tests
./services/activeledger/utils
./services/ads
./services/ads/__pycache__
./services/ads/affiliate
./services/ads/core
./services/ads/integrations
./services/ads/tracking
./services/ai-orchestrator
./services/ai-orchestrator/__pycache__
./services/ai-orchestrator/plugins
./services/ai-tools
./services/ai-tools/config
./services/ai-tools/models
./services/ai-tools/services
./services/ai-tools/utils
./services/ai_orchestrator
./services/ambient
./services/analytics
./services/analytics/__pycache__
./services/analytics/api
./services/analytics/core
./services/analytics/models
./services/analytics/services
./services/analytics/websocket
./services/api-gateway
./services/api-gateway/__pycache__
./services/api_gateway
./services/ar-layer
./services/ar-layer/biometrics
./services/ar-layer/collaboration
./services/ar-layer/core
./services/ar-layer/gestures
./services/ar-layer/haptics
./services/ar-layer/overlay
./services/ar-layer/recognition
./services/ar-layer/spatial
./services/ar-layer/tracking
./services/ar-layer/translation
./services/ar-layer/visualization
./services/ar-layer/voice
./services/auth
./services/auth/__pycache__
./services/backup
./services/backup/api
./services/backup/backup_engines
./services/backup/config
./services/backup/core
./services/backup/crypto
./services/backup/destinations
./services/backup/logs
./services/backup/models
./services/backup/recovery
./services/backup/services
./services/backup/tests
./services/batch-import
./services/batch-import/api
./services/batch-import/core
./services/batch-import/models
./services/batch-import/services
./services/biological
./services/blockchain
./services/blockchain/audit
./services/blockchain/bridges
./services/blockchain/config
./services/blockchain/consensus
./services/blockchain/contracts
./services/blockchain/credentials
./services/blockchain/governance
./services/blockchain/marketplace
./services/blockchain/models
./services/blockchain/nft
./services/blockchain/payments
./services/blockchain/privacy
./services/blockchain/storage
./services/blockchain/tokens
./services/blockchain/utils
./services/cache
./services/cognitive
./services/collaboration
./services/collaboration/src
./services/creative-suite
./services/creative-suite/blocks
./services/creative-suite/collaboration
./services/creative-suite/colors
./services/creative-suite/energy
./services/creative-suite/ideas
./services/creative-suite/inspiration
./services/creative-suite/moodboards
./services/creative-suite/music
./services/creative-suite/portfolio
./services/creative-suite/story
./services/creative-suite/style
./services/creative-suite/versioning
./services/data-export
./services/data-export/output
./services/data-export/src
./services/data-export/temp
./services/data-export/templates
./services/data-manager
./services/data-manager/ai
./services/data-manager/analytics
./services/data-manager/api
./services/data-manager/config
./services/data-manager/core
./services/data-manager/models
./services/data-manager/monitoring
./services/data-manager/processing
./services/data-manager/tests
./services/data-manager/utils
./services/dmlog-ai-dm
./services/dmlog-ai-dm/assistants
./services/dmlog-ai-dm/data
./services/dmlog-ai-dm/managers
./services/dmlog-ai-dm/models
./services/dmlog-ai-dm/utils
./services/dmlog-battle
./services/dmlog-battle/__pycache__
./services/dmlog-battle/data
./services/dmlog-battle/models
./services/dmlog-battle/services
./services/dmlog-battle/utils
./services/dmlog-characters
./services/dmlog-characters/models
./services/dmlog-characters/services
./services/dmlog-converter
./services/dmlog-converter/__pycache__
./services/dmlog-converter/config
./services/dmlog-converter/converters
./services/dmlog-converter/data
./services/dmlog-converter/managers
./services/dmlog-converter/models
./services/dmlog-converter/utils
./services/dmlog-converter/validators
./services/dmlog-core
./services/dmlog-core/api
./services/dmlog-core/models
./services/dmlog-core/services
./services/dmlog-marketplace
./services/dmlog-marketplace/config
./services/dmlog-marketplace/data
./services/dmlog-marketplace/models
./services/dmlog-marketplace/payments
./services/dmlog-marketplace/services
./services/dmlog-marketplace/stores
./services/dmlog-marketplace/utils
./services/dmlog-player
./services/dmlog-player/__pycache__
./services/dmlog-player/config
./services/dmlog-player/data
./services/dmlog-player/interface
./services/dmlog-player/managers
./services/dmlog-player/models
./services/dmlog-player/utils
./services/dmlog-session
./services/dmlog-session/models
./services/dmlog-session/services
./services/dmlog-session/static
./services/dmlog-session/templates
./services/dmlog-templates
./services/dmlog-templates/__pycache__
./services/dmlog-templates/data
./services/dmlog-templates/generators
./services/dmlog-templates/models
./services/dmlog-templates/templates
./services/dmlog-templates/utils
./services/dmlog-world
./services/dmlog-world/models
./services/dmlog-world/services
./services/document-ai
./services/document-ai/classifiers
./services/document-ai/config
./services/document-ai/core
./services/document-ai/extractors
./services/document-ai/models
./services/document-ai/output
./services/document-ai/processors
./services/document-ai/src
./services/document-ai/tests
./services/document-ai/vector_db
./services/education-ai
./services/education-ai/attention
./services/education-ai/communication
./services/education-ai/credentials
./services/education-ai/curriculum
./services/education-ai/docs
./services/education-ai/games
./services/education-ai/grading
./services/education-ai/knowledge-gaps
./services/education-ai/learning-styles
./services/education-ai/plagiarism
./services/education-ai/skills
./services/education-ai/study-groups
./services/education-ai/tests
./services/education-ai/tutoring
./services/emotional-ai
./services/emotional-ai/journey
./services/emotional-ai/mood
./services/emotional-ai/stress
./services/file-sync
./services/file-sync/__pycache__
./services/file-watcher
./services/file_processor
./services/gaming-platform
./services/gaming-platform/replay
./services/gaming-platform/team
./services/graphql
./services/graphql/scripts
./services/graphql/src
./services/health-integration
./services/health-integration/analytics
./services/health-integration/devices
./services/health-integration/fitness
./services/health-integration/medication
./services/health-integration/nutrition
./services/health-integration/sleep
./services/health-integration/stress
./services/manufacturing
./services/manufacturing/assembly
./services/manufacturing/collaboration
./services/manufacturing/compliance
./services/manufacturing/coordination
./services/manufacturing/docs
./services/manufacturing/jit
./services/manufacturing/maintenance
./services/manufacturing/pipeline
./services/manufacturing/quality
./services/manufacturing/sourcing
./services/manufacturing/suppliers
./services/manufacturing/sustainability
./services/manufacturing/tests
./services/manufacturing/version_control
./services/marine-advanced
./services/marine-advanced/ais
./services/marine-advanced/anchor
./services/marine-advanced/docs
./services/marine-advanced/emergency
./services/marine-advanced/fleet
./services/marine-advanced/fuel
./services/marine-advanced/logbook
./services/marine-advanced/mob
./services/marine-advanced/ports
./services/marine-advanced/sail
./services/marine-advanced/tests
./services/marine-advanced/tides
./services/marine-advanced/voyage
./services/marine-advanced/weather
./services/memory-preservation
./services/metadata
./services/metadata/__pycache__
./services/ml-pipeline
./services/ml-pipeline/data
./services/ml-pipeline/docker
./services/ml-pipeline/examples
./services/ml-pipeline/logs
./services/ml-pipeline/scripts
./services/ml-pipeline/src
./services/ml-pipeline/tests
./services/mobile-api
./services/mobile-api/api
./services/mobile-api/config
./services/mobile-api/core
./services/mobile-api/proto
./services/mobile-api/protobuf
./services/mobile-api/scripts
./services/mobile-api/services
./services/mobile-api/src
./services/multiverse
./services/notification
./services/notifications
./services/notifications/__pycache__
./services/notifications/api
./services/notifications/core
./services/notifications/models
./services/notifications/services
./services/notifications/templates
./services/notifications/tests
./services/p2p-sync
./services/p2p-sync/core
./services/p2p-sync/dht
./services/p2p-sync/discovery
./services/p2p-sync/encryption
./services/p2p-sync/groups
./services/p2p-sync/models
./services/p2p-sync/nat
./services/p2p-sync/tests
./services/p2p-sync/webrtc
./services/predictive
./services/predictive-ai
./services/predictive-ai/analytics
./services/predictive-ai/caching
./services/predictive-ai/core
./services/predictive-ai/engines
./services/predictive-ai/learning
./services/predictive-ai/src
./services/quantum-ready
./services/quantum-ready/algorithms
./services/quantum-ready/annealing
./services/quantum-ready/communication
./services/quantum-ready/crypto
./services/quantum-ready/encryption
./services/quantum-ready/ml
./services/quantum-ready/optimization
./services/quantum-ready/pipelines
./services/quantum-ready/random
./services/quantum-ready/security
./services/quantum-ready/sensing
./services/quantum-ready/simulation
./services/quantum-reality
./services/security-advanced
./services/simulation
./services/simulation/behavioral
./services/simulation/business
./services/simulation/crisis
./services/simulation/digital_twin
./services/simulation/economic
./services/simulation/market
./services/simulation/network
./services/simulation/resource
./services/simulation/social
./services/simulation/traffic
./services/simulation/weather
./services/simulation/whatif
./services/smart-folders
./services/smart-folders/src
./services/social-ai
./services/social-ai/communication
./services/social-ai/compatibility
./services/social-ai/conflict
./services/social-ai/energy
./services/social-ai/gifts
./services/social-ai/influence
./services/social-ai/insights
./services/social-ai/introductions
./services/social-ai/networks
./services/social-ai/relationships
./services/social-ai/reminders
./services/social-ai/teams
./services/sync-engine
./services/sync-v2
./services/sync-v2/config
./services/sync-v2/core
./services/sync-v2/docs
./services/sync-v2/protocols
./services/sync-v2/realtime
./services/sync-v2/resolution
./services/sync-v2/strategies
./services/sync-v2/tests
./services/time-machine
./services/universal-translator
./services/video-pipeline
./services/video-pipeline/config
./services/video-pipeline/docker
./services/video-pipeline/docs
./services/video-pipeline/migrations
./services/video-pipeline/models
./services/video-pipeline/src
./services/video-pipeline/tests
./services/video-processor
./services/video-processor/api
./services/video-processor/config
./services/video-processor/core
./services/video-processor/models
./services/video-processor/output
./services/video-processor/processors
./services/video-processor/services
./services/video-processor/src
./services/video-processor/streaming
./services/video-processor/temp
./services/video-processor/tests
./services/video-processor/utils
./services/workflows
./services/workflows/src
./src
./src/middleware
./src/plugins
./tests
./tests/coverage
./tests/docker
./tests/e2e
./tests/fixtures
./tests/integration
./tests/load
./tests/logs
./tests/mocks
./tests/unit
./tests/utils
PROJECT_TREE_END

[0;32m=== 11. LOG FILES ANALYSIS ===[0m
LOG_ANALYSIS_START
LOG_FILES:
-rw-rw-r-- 1 activeloguser activeloguser  11K Aug 22 00:40 ./monitoring/dashboards/activelog-overview.json
-rw-rw-r-- 1 activeloguser activeloguser  13K Aug 21 20:52 ./monitoring/grafana/dashboards/activelog-overview.json
-rw-rw-r-- 1 activeloguser activeloguser 8.1K Aug 21 20:51 ./monitoring/rules/activelog-alerts.yml
-rw-rw-r-- 1 activeloguser activeloguser 2.5K Aug 21 23:19 ./services/backup/core/logging.py
-rw-rw-r-- 1 activeloguser activeloguser 1.3K Aug 21 21:58 ./services/batch-import/core/logging.py
-rw-rw-r-- 1 activeloguser activeloguser 2.0K Aug 21 21:18 ./services/batch-import/core/logging_config.py
-rw-rw-r-- 1 activeloguser activeloguser 1.5K Aug 21 22:17 ./services/data-export/src/utils/logger.js
-rw-rw-r-- 1 activeloguser activeloguser  11K Aug 22 15:15 ./services/dmlog-characters/models/dialogue.py
-rw-rw-r-- 1 activeloguser activeloguser  22K Aug 22 15:17 ./services/dmlog-characters/services/dialogue_service.py
-rw-rw-r-- 1 activeloguser activeloguser 3.2K Aug 21 23:53 ./services/document-ai/core/logging.py
-rw-rw-r-- 1 activeloguser activeloguser  930 Aug 21 22:04 ./services/document-ai/src/utils/logger.js
-rw-rw-r-- 1 activeloguser activeloguser  57K Aug 22 16:22 ./services/marine-advanced/logbook/automatic_logbook.py
-rwxrwxr-x 1 activeloguser activeloguser  688 Aug 21 15:55 ./stop_activelog.sh

./services/backup/logs:
total 0

./services/dmlog-ai-dm:
total 76K
-rw-rw-r-- 1 activeloguser activeloguser 9.3K Aug 22 21:02 README.md
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:56 assistants
-rw-rw-r-- 1 activeloguser activeloguser  12K Aug 22 20:45 config.py
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:44 data
-rw-rw-r-- 1 activeloguser activeloguser  25K Aug 22 21:01 main_service.py
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:54 managers
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:46 models
-rw-rw-r-- 1 activeloguser activeloguser  704 Aug 22 20:44 requirements.txt
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:59 utils

./services/dmlog-characters:
total 56K
-rw-rw-r-- 1 activeloguser activeloguser 7.0K Aug 22 15:38 README.md
-rw-rw-r-- 1 activeloguser activeloguser 4.5K Aug 22 15:08 config.py
-rw-rw-r-- 1 activeloguser activeloguser  22K Aug 22 15:38 main.py
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 15:32 models
-rw-rw-r-- 1 activeloguser activeloguser  603 Aug 22 15:08 requirements.txt
-rwxrwxr-x 1 activeloguser activeloguser 1.1K Aug 22 15:38 run.py
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 15:36 services

./services/dmlog-core:
total 48K
-rw-rw-r-- 1 activeloguser activeloguser  700 Aug 22 14:27 Dockerfile
-rw-rw-r-- 1 activeloguser activeloguser 5.9K Aug 22 15:01 README.md
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 15:00 api
-rw-rw-r-- 1 activeloguser activeloguser 5.1K Aug 22 14:27 config.py
-rw-rw-r-- 1 activeloguser activeloguser 1.6K Aug 22 15:00 database.py
-rw-rw-r-- 1 activeloguser activeloguser 4.9K Aug 22 14:37 main.py
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 15:00 models
-rw-rw-r-- 1 activeloguser activeloguser  426 Aug 22 14:27 requirements.txt
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 15:00 services

./services/dmlog-session:
total 60K
-rw-rw-r-- 1 activeloguser activeloguser 8.9K Aug 22 20:11 README.md
-rw-rw-r-- 1 activeloguser activeloguser 7.8K Aug 22 19:47 config.py
-rw-rw-r-- 1 activeloguser activeloguser  17K Aug 22 20:11 main_service.py
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 19:51 models
-rw-rw-r-- 1 activeloguser activeloguser 1.6K Aug 22 19:47 requirements.txt
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:10 services
drwxrwxr-x 6 activeloguser activeloguser 4.0K Aug 22 19:46 static
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 19:46 templates

./services/dmlog-templates:
total 72K
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:43 __pycache__
-rw-rw-r-- 1 activeloguser activeloguser 8.9K Aug 22 20:14 config.py
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:13 data
drwxrwxr-x 3 activeloguser activeloguser 4.0K Aug 22 20:43 generators
-rw-rw-r-- 1 activeloguser activeloguser  32K Aug 22 20:42 main_service.py
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:32 models
-rw-rw-r-- 1 activeloguser activeloguser  227 Aug 22 20:13 requirements.txt
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:13 templates
drwxrwxr-x 2 activeloguser activeloguser 4.0K Aug 22 20:13 utils

./services/marine-advanced/logbook:
total 60K
-rw-rw-r-- 1 activeloguser activeloguser 57K Aug 22 16:22 automatic_logbook.py

LOG_DIRECTORIES:
./services/backup/logs
./services/ml-pipeline/logs
./migrations/logs
./logs
./production/logs
./production/backup/logs
./tests/logs

RECENT_LOG_ACTIVITY:
-rw-rw-r-- 1 activeloguser activeloguser 479 Aug 22 10:00 ./logs/ai-orchestrator.log
-rw-rw-r-- 1 activeloguser activeloguser 599 Aug 22 10:00 ./logs/file-sync.log
-rw-rw-r-- 1 activeloguser activeloguser 311 Aug 21 16:28 ./logs/api-gateway.log
-rw-rw-r-- 1 activeloguser activeloguser  60 Aug 21 16:16 ./logs/frontend.log
LOG_ANALYSIS_END

[0;32m=== 12. PROCESS ANALYSIS ===[0m
PROCESS_ANALYSIS_START
ACTIVELOG_PROCESSES:
root         677  0.0  0.0   7660  4800 pts/0    S    01:05   0:00 su - activeloguser
activel+    3745  0.1  0.3 264444 62484 pts/0    Sl   01:22   1:53 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
activel+    3746  0.1  0.3 240364 58796 pts/0    Sl   01:22   1:52 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8001
activel+    3747  0.1  0.3 358956 56032 pts/0    Sl   01:22   1:53 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8088
root       14901  0.0  0.0   7660  4800 pts/2    S    06:17   0:00 su - activeloguser
root       16748  0.0  0.0   7660  4800 pts/4    S    07:16   0:00 su - activeloguser
activel+   18413  0.0  0.0   4916  3264 ?        Ss   07:37   0:00 /bin/bash -c -l source /home/activeloguser/.claude/shell-snapshots/snapshot-bash-1755824307642-vixhde.sh && eval 'python3 main_simple.py' \< /dev/null && pwd -P >| /tmp/claude-3953-cwd
root       41302  0.0  0.0   7660  4608 pts/8    S    15:35   0:00 su - activeloguser
root       44775  0.0  0.0   7660  4800 pts/5    S    16:53   0:00 su - activeloguser
activel+   63823  0.0  0.0   4916  3264 ?        Ss   22:17   0:00 /bin/bash -c -l source /home/activeloguser/.claude/shell-snapshots/snapshot-bash-1755905409738-f0zzkq.sh && eval 'python3 generate_audit_report.py' \< /dev/null && pwd -P >| /tmp/claude-7f86-cwd
activel+   63848  2.8  0.0   4920  3264 ?        S    22:17   0:00 /bin/bash /home/activeloguser/activelog/audit_system.sh

NODE_PROCESSES:
No Node.js processes found

PYTHON_PROCESSES:
root         233  0.0  0.1  30096 19008 ?        Ss   01:05   0:00 /usr/bin/python3 /usr/bin/networkd-dispatcher --run-startup-triggers
root         276  0.0  0.1 107160 21312 ?        Ssl  01:05   0:00 /usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal
activel+    3745  0.1  0.3 264444 62484 pts/0    Sl   01:22   1:53 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
activel+    3746  0.1  0.3 240364 58796 pts/0    Sl   01:22   1:52 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8001
activel+    3747  0.1  0.3 358956 56032 pts/0    Sl   01:22   1:53 /usr/bin/python3 /home/activeloguser/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8088
activel+    3825  0.0  0.1 172404 18624 pts/0    S    01:23   0:11 python3 -m http.server 3000
activel+   18413  0.0  0.0   4916  3264 ?        Ss   07:37   0:00 /bin/bash -c -l source /home/activeloguser/.claude/shell-snapshots/snapshot-bash-1755824307642-vixhde.sh && eval 'python3 main_simple.py' \< /dev/null && pwd -P >| /tmp/claude-3953-cwd
activel+   18438  0.1  0.3 128884 51192 ?        Sl   07:37   1:44 python3 main_simple.py
activel+   18439  0.0  0.0  16384 10560 ?        S    07:37   0:00 /usr/bin/python3 -c from multiprocessing.resource_tracker import main;main(5)
activel+   18440  0.0  0.0      0     0 ?        Z    07:37   0:00 [python3] <defunct>
activel+   63823  0.0  0.0   4916  3264 ?        Ss   22:17   0:00 /bin/bash -c -l source /home/activeloguser/.claude/shell-snapshots/snapshot-bash-1755905409738-f0zzkq.sh && eval 'python3 generate_audit_report.py' \< /dev/null && pwd -P >| /tmp/claude-7f86-cwd
activel+   63847  1.2  0.0  17408 12480 ?        S    22:17   0:00 python3 generate_audit_report.py

PORT_USAGE:
tcp        0      0 0.0.0.0:3000            0.0.0.0:*               LISTEN      3825/python3        
tcp        0      0 0.0.0.0:9000            0.0.0.0:*               LISTEN      -                   
tcp        0      0 0.0.0.0:9001            0.0.0.0:*               LISTEN      -                   
tcp        0      0 0.0.0.0:8000            0.0.0.0:*               LISTEN      3745/python3        
tcp        0      0 0.0.0.0:8001            0.0.0.0:*               LISTEN      3746/python3        
tcp6       0      0 :::9000                 :::*                    LISTEN      -                   
tcp6       0      0 :::9001                 :::*                    LISTEN      -                   

SYSTEM_RESOURCES:
CPU Usage:
%Cpu(s):  1.1 us,  0.3 sy,  0.0 ni, 98.6 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
Memory Usage:
               total        used        free      shared  buff/cache   available
Mem:            15Gi       3.8Gi        10Gi        23Mi       1.2Gi        11Gi
Swap:          4.0Gi          0B       4.0Gi
Disk Usage:
/dev/sdf       1007G   14G  943G   2% /
PROCESS_ANALYSIS_END

[0;34m==================================
Audit completed at 2025-08-22 22:17:22
==================================[0m

```
