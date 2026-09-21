# ActiveLog App Factory

Multi-app deployment system for the ActiveLog.ai ecosystem. This factory creates and manages specialized frontend applications for different verticals while maintaining shared infrastructure.

## Apps Managed

- **PersonalLog.ai** - Consumer-friendly, ad-supported personal logging
- **BusinessLog.ai** - Inventory, payroll, tax receipt scanning for businesses
- **FishingLog.ai** - Depth sounder, radar, fish counting for fishing
- **RealLog.ai** - Final Cut Pro-like interface for video editing
- **StudyLog.ai** - Education tracking and tutoring tools
- **PlayerLog.ai** - Screen recording and game analysis
- **MakerLog.ai** - Design, manufacturing, and logistics tracking
- **CoCapn.ai** - Simplified marine navigation
- **Capitaine.ai** - Advanced marine navigation
- **DMLog.ai** - Tabletop RPG management tools

## Directory Structure

```
app-factory/
├── base/                  # Base template for all apps
├── configs/               # App-specific configurations
├── themes/                # UI themes and layouts
├── auth/                  # Shared authentication system
├── data-sync/             # Cross-app data sharing
├── ai-models/             # App-specific AI model loading
├── settings/              # Unified settings sync
└── build/                 # Build system for all apps
```

## Features

- Shared authentication across all apps
- App-specific UI themes and layouts
- Cross-app data sharing protocols
- App-specific AI model loading
- Unified settings synchronization
- Modular build system