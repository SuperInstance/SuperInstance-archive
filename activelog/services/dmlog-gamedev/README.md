# DMLog Game Development Converter

🎮 **Transform D&D Campaigns into Professional Game Development Assets**

The DMLog Game Development Converter is a comprehensive TypeScript service that transforms tabletop RPG campaigns into production-ready game development assets. Convert your D&D campaigns into scripts, dialogue trees, quest systems, and complete monetization strategies for Unity, Godot, and Unreal Engine.

## ✨ Features

### 🎯 **Core Conversion Systems**

| System | Status | Description |
|--------|--------|-------------|
| 📜 **Narrative Script Exporter** | ✅ Complete | Export campaign stories in multiple formats (Markdown, Fountain, JSON, YAML, XML, CSV, Twine, Articy) |
| 💬 **Dialogue Tree Generator** | ✅ Complete | Generate branching dialogue with conditional responses and character-specific interactions |
| 🎯 **Quest System Converter** | ✅ Complete | Transform campaign quests into structured game objectives with dependencies and rewards |
| 🤖 **NPC Behavior Scripting** | ✅ Complete | Create AI behavior trees for NPCs with states, reactions, and pathfinding |
| 🏗️ **Level Design Generator** | ✅ Complete | Convert campaign maps into level geometry with gameplay elements and technical constraints |
| ⚔️ **Combat Mechanic Adapter** | ✅ Complete | Transform D&D combat into real-time or turn-based game systems |
| 🎨 **Asset Requirement Generator** | ✅ Complete | Generate comprehensive asset lists with specifications for artists and developers |
| ⚙️ **Game Engine Templates** | ✅ Complete | Export ready-to-use project templates for Unity, Godot, and Unreal Engine |
| 🧪 **Playtesting Framework** | ✅ Complete | Create structured playtesting plans with metrics and automated reporting |
| 🏆 **Achievement Generator** | ✅ Complete | Design comprehensive achievement systems with progression tracking |
| 💾 **Save System Designer** | ✅ Complete | Architect save systems with versioning, compression, and cloud sync |
| 💰 **Monetization Planner** | ✅ Complete | Generate detailed business models with pricing strategies and revenue projections |

### 🎮 **Supported Game Engines**

- **Unity**: Complete C# scripts, prefabs, and scene templates
- **Godot**: GDScript implementations with node structures
- **Unreal Engine**: Blueprint-compatible systems and C++ foundations
- **Custom Engines**: Generic JSON/XML exports for any platform

## 🚀 Quick Start

### Installation

```bash
cd ~/activelog/services/dmlog-gamedev
npm install
npm run build
npm start
```

### Basic Usage

```bash
# Health check
curl http://localhost:3006/health

# Generate monetization plan
curl -X POST http://localhost:3006/generate/monetization-plan \
  -H "Content-Type: application/json" \
  -d '{"campaign": {...}, "options": {"primary_model": "freemium"}}'

# Export complete campaign conversion
curl -X POST http://localhost:3006/convert/full-campaign \
  -H "Content-Type: application/json" \
  -d '{"campaign": {...}, "options": {"includeAll": true}}'
```

## 📋 API Endpoints

### Core Conversion Endpoints

```http
# Script Export
POST /export/script
POST /generate/dialogue-tree
POST /export/dialogue-tree

# Quest Systems  
POST /convert/quests
POST /export/quests

# NPC Behavior
POST /generate/npc-behavior
POST /export/npc-behavior

# Level Design
POST /generate/level-design
POST /export/level-design

# Combat Systems
POST /adapt/combat-system
POST /export/combat-system

# Asset Management
POST /generate/asset-requirements
POST /generate/asset-budget
POST /export/asset-requirements

# Game Engine Templates
POST /generate/engine-template
POST /export/engine-template

# Playtesting
POST /create/playtest-plan
POST /execute/playtest-session
POST /analyze/playtest-session
POST /export/playtest-report

# Achievement Systems
POST /generate/achievement-system
POST /export/achievement-system

# Save Systems
POST /generate/save-system
POST /export/save-system

# Monetization
POST /generate/monetization-plan
POST /export/monetization-plan

# Utilities
GET  /assets/list
GET  /health
```

### Full Campaign Conversion

```http
POST /convert/full-campaign
```

Convert an entire D&D campaign into a complete game development package including:
- Narrative scripts in multiple formats
- Complete dialogue trees for all NPCs
- Structured quest systems with dependencies
- AI behavior scripts for all characters
- Level designs from campaign maps
- Balanced combat mechanics
- Comprehensive asset requirements
- Engine-specific project templates
- Monetization strategy
- Achievement systems
- Save system architecture

## 🎯 Campaign Input Format

```typescript
interface Campaign {
  id: string;
  title: string;
  description: string;
  setting: string;
  theme: string;
  genre: string;
  sessions: Session[];
  characters: Character[];
  npcs: NPC[];
  locations: Location[];
  quests: Quest[];
  items: Item[];
  encounters: Encounter[];
  scenes?: Scene[];
  maps?: Map[];
  worldbuilding: Worldbuilding;
  mechanics: CampaignMechanics;
  notes: string[];
  assets: Asset[];
}
```

## 💰 Monetization Models Supported

- **Premium**: One-time purchase model
- **Freemium**: Free-to-play with premium upgrades
- **Subscription**: Recurring revenue model
- **DLC/Expansion**: Additional content packs
- **Cosmetics**: Appearance-only monetization
- **Battle Pass**: Seasonal progression systems
- **In-App Purchases**: Convenience and enhancement items

## 🎮 Game Engine Export Examples

### Unity C# Script Export

```csharp
// Generated Achievement System for Unity
using UnityEngine;
using System.Collections.Generic;

public class AchievementManager : MonoBehaviour
{
    [SerializeField]
    private List<Achievement> achievements = new List<Achievement>();
    
    public void UnlockAchievement(string achievementId)
    {
        Achievement achievement = achievements.Find(a => a.id == achievementId);
        if (achievement != null && !achievement.unlocked)
        {
            achievement.unlocked = true;
            Debug.Log("Achievement Unlocked: " + achievement.name);
        }
    }
}
```

### Godot GDScript Export

```gdscript
# Generated Achievement System for Godot
extends Node

signal achievement_unlocked(achievement_id)

var achievements = {}

func unlock_achievement(achievement_id: String):
    if achievements.has(achievement_id) and not achievements[achievement_id]["unlocked"]:
        achievements[achievement_id]["unlocked"] = true
        emit_signal("achievement_unlocked", achievement_id)
        print("Achievement Unlocked: ", achievements[achievement_id]["name"])
```

## 🏗️ Architecture

```
dmlog-gamedev/
├── src/
│   ├── narrative/          # Script and story conversion
│   ├── dialogue/           # Dialogue tree generation
│   ├── quests/             # Quest system conversion
│   ├── behavior/           # NPC AI behavior scripting
│   ├── level/              # Level design generation
│   ├── combat/             # Combat system adaptation
│   ├── assets/             # Asset requirement generation
│   ├── templates/          # Game engine templates
│   ├── testing/            # Playtesting framework
│   ├── achievements/       # Achievement system generation
│   ├── saves/              # Save system design
│   ├── monetization/       # Business model generation
│   ├── types/              # TypeScript type definitions
│   └── index.ts            # Main service entry point
├── test-api.js             # API testing script
├── package.json
└── README.md
```

## 🔧 Development

### Prerequisites

- Node.js 18+
- TypeScript 5.2+
- npm or yarn

### Development Commands

```bash
npm run dev      # Start development server with hot reload
npm run build    # Compile TypeScript to JavaScript
npm run start    # Start production server
npm run test     # Run test suite
npm run lint     # Run ESLint
npm run clean    # Clean build directory
```

### Testing

```bash
# Start the service
npm run dev

# In another terminal, run API tests
node test-api.js
```

## 🌐 Integration with DMLog Services

The Game Development Converter integrates seamlessly with other DMLog services:

- **DMLog Core**: Retrieves campaign data and character information
- **DMLog AI-DM**: Leverages AI-generated content for enhanced narratives
- **DMLog Characters**: Imports detailed character profiles and relationships
- **DMLog Session**: Integrates session recordings and player interactions
- **DMLog Templates**: Uses campaign templates for consistent generation

## 📊 Export Formats Supported

### Narrative Scripts
- **Markdown** (.md): Human-readable documentation
- **Fountain** (.fountain): Industry-standard screenwriting format
- **JSON** (.json): Structured data for programming
- **YAML** (.yaml): Configuration-friendly format
- **XML** (.xml): Enterprise integration format
- **CSV** (.csv): Spreadsheet-compatible format
- **Twine** (.tw2): Interactive fiction format
- **Articy** (.xml): Professional narrative tool format

### Technical Exports
- **Unity** (.cs, .prefab, .unity): Complete Unity project files
- **Godot** (.gd, .tscn, .godot): Godot Engine native formats
- **Unreal** (.cpp, .h, .uasset): Unreal Engine compatible files
- **JSON/XML**: Universal game engine formats

## 💡 Use Cases

### Indie Game Development
Convert your successful D&D campaigns into indie video games with complete development assets.

### Educational Games
Transform educational campaigns into interactive learning experiences.

### Mobile Games
Generate mobile-friendly quest systems and monetization strategies.

### VR/AR Experiences
Create immersive virtual reality campaigns from tabletop adventures.

### Interactive Fiction
Export narrative-heavy campaigns as interactive stories.

## 🎯 Configuration Options

### Full Campaign Conversion Options

```typescript
interface ConversionOptions {
  includeScript?: boolean;           // Export narrative scripts
  includeDialogue?: boolean;         // Generate dialogue trees
  includeQuests?: boolean;           // Convert quest systems
  includeNPCBehavior?: boolean;      // Create NPC AI
  includeLevelDesign?: boolean;      // Generate level layouts
  includeCombatSystem?: boolean;     // Adapt combat mechanics
  includeAssets?: boolean;           // List asset requirements
  includeTemplates?: boolean;        // Generate engine templates
  includeAchievements?: boolean;     // Create achievement systems
  includeSaveSystem?: boolean;       // Design save architecture
  includeMonetization?: boolean;     // Generate business model
  
  // Format options
  scriptFormats?: string[];          // ['markdown', 'fountain', 'json']
  dialogueFormats?: string[];        // ['json', 'xml', 'yaml']
  questFormats?: string[];           // ['json', 'unity', 'godot']
  
  // Engine-specific options
  targetEngine?: 'unity' | 'godot' | 'unreal' | 'generic';
  platformTarget?: 'pc' | 'mobile' | 'console' | 'web';
}
```

## 📈 Performance & Scalability

- **Concurrent Processing**: Convert multiple campaign elements simultaneously
- **Streaming Exports**: Handle large campaigns with memory-efficient streaming
- **Caching**: Intelligent caching for repeated conversions
- **WebSocket Updates**: Real-time progress updates for long conversions
- **Background Processing**: Queue large conversion jobs

## 🛡️ Security & Compliance

- **Input Sanitization**: All campaign data is validated and sanitized
- **Rate Limiting**: API endpoints are rate-limited to prevent abuse
- **Authentication**: Integration with DMLog auth system
- **Data Privacy**: Campaign data is processed securely and not stored permanently
- **GDPR Compliance**: Privacy-first data handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built for the DMLog ecosystem
- Supports the tabletop gaming community
- Bridges the gap between TTRPGs and video games

---

**⚡ Transform your D&D campaigns into professional game development assets with the DMLog Game Development Converter!**