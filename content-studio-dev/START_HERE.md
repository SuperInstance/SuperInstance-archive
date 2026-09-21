# Loopless Content Studio - Quick Start

## What Was Built

A **multi-agent content creation system** based on your friend's multi-agent coding architecture, adapted for producing animated content from your 60 story files.

### System Architecture

```
                    Claude Orchestrator (You)
                             ↓
              ┌──────────────┴──────────────┐
              │                             │
         Task Manager              Message Bus
              │                             │
              └──────────┬──────────────────┘
                         ↓
        ┌────────────────────────────────┐
        │     Bot Team (14 bots)         │
        ├────────────────────────────────┤
        │ 1. script_writer_1, _2         │ ← Adapt stories to scripts
        │ 2. image_prompter_1            │ ← Generate image prompts
        │ 3. dialogue_formatter_1        │ ← Format for voice synthesis
        │ 4. sound_designer_1            │ ← Sound effects/music
        │ 5. sequence_editor_1           │ ← Video assembly planning
        │ 6. metadata_gen_1              │ ← YouTube/podcast metadata
        │ 7. qa_content_1                │ ← Quality assurance
        │ 8. social_clipper_1            │ ← Promotional clips
        │                                │
        │ Always-Running:                │
        │ 9. story_indexer_1            │ ← Indexes 60 stories
        │ 10. asset_monitor_1           │ ← Tracks assets
        │ 11. progress_tracker_1        │ ← Episode progress
        │ 12. cost_monitor_1            │ ← API cost tracking
        └────────────────────────────────┘
                         ↓
            Knowledge Base (ChromaDB)
                  + LoRA Manager
```

## Files Created

**Configuration** (in `config/`):
- `content_bootcamp.md` - 9K context file for Claude orchestrator
- `content_bot_configs.yaml` - 14 bot definitions

**Python Code** (in `src/`):
- `orchestrator/main.py` - FastAPI server + Claude API integration
- `orchestrator/task_manager.py` - Priority task queue
- `bots/base_bot.py` - Generic bot foundation (help queue, retry, metrics)
- `bots/content_bots.py` - 7 specialized content creation bots
- `communication/message_bus.py` - Pub/sub messaging
- `communication/help_queue.py` - Bot escalation system
- `knowledge/knowledge_base.py` - ChromaDB vector store
- `lora/lora_manager.py` - User/project adapter management

**Dependencies**:
- `requirements.txt` - All Python packages

## How It Works

1. **You send a request**: "Create Episode 1 for YouTube (28 minutes)"

2. **Claude orchestrator** (main.py):
   - Reads `content_bootcamp.md` for system context
   - Analyzes your request
   - Breaks it into bot-sized tasks
   - Assigns tasks to appropriate bots

3. **Bots execute in parallel**:
   - `story_indexer_1` finds Story_01_v3.md
   - `script_writer_1` adapts to video script
   - `image_prompter_1` generates image prompts
   - `dialogue_formatter_1` formats for ElevenLabs
   - `sound_designer_1` plans sound effects

4. **If a bot gets stuck**:
   - Bot signals help request 🆘
   - System tries more capable bot
   - If still stuck, escalates to Claude
   - Claude provides guidance or completes task

5. **Quality assurance**:
   - `qa_content_1` reviews everything
   - `metadata_gen_1` creates YouTube metadata
   - `social_clipper_1` extracts promotional clips

## Installation & Setup

### 1. Install Ollama Models

```bash
# Required models for bots
ollama pull llama3.2:1b      # Always-running bots
ollama pull llama3.2:3b      # Script/image/QA bots
ollama pull qwen2.5-coder:3b # Complex content generation
```

### 2. Install Python Dependencies

```bash
cd /home/activeloguser/content-studio-dev
pip install -r requirements.txt
```

### 3. Set Environment Variables

```bash
# Add to ~/.bashrc or export in terminal
export ANTHROPIC_API_KEY="your_claude_api_key_here"
```

### 4. Start the System

```bash
cd /home/activeloguser/content-studio-dev
python -m src.orchestrator.main
```

The system will start on `http://localhost:8000`

## Testing the System

### Method 1: API Request

```bash
curl -X POST http://localhost:8000/api/request \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create Episode 1 for YouTube (28 minutes)",
    "user_id": "user123"
  }'
```

### Method 2: Python Script

```python
import requests

response = requests.post(
    "http://localhost:8000/api/request",
    json={
        "message": "Create Episode 1 for YouTube (28 minutes)",
        "user_id": "user123"
    }
)

print(response.json()["response"])
```

### Method 3: Check System Status

```bash
curl http://localhost:8000/api/status
```

## What Each Bot Does

| Bot | Purpose | Model | When to Use |
|-----|---------|-------|-------------|
| **script_writer_1** | Story → video script | llama3.2:3b | First step in episode production |
| **script_writer_2** | Story → podcast script | llama3.2:3b | For podcast versions |
| **image_prompter_1** | Generate SD/DALL-E prompts | llama3.2:3b | After script is ready |
| **dialogue_formatter_1** | Format for voice synthesis | llama3.2:1b | Parallel with image generation |
| **sound_designer_1** | Sound effects & music cues | llama3.2:1b | Parallel with other audio work |
| **sequence_editor_1** | Video assembly planning | llama3.2:3b | After all assets generated |
| **metadata_gen_1** | YouTube/podcast metadata | llama3.2:1b | Near completion |
| **qa_content_1** | Quality review | llama3.2:3b | Before publishing |
| **social_clipper_1** | Promotional clips | llama3.2:1b | After episode complete |
| **story_indexer_1** | Index all 60 stories | llama3.2:1b | Always running |
| **asset_monitor_1** | Track generated files | llama3.2:1b | Always running |
| **progress_tracker_1** | Episode completion | llama3.2:1b | Always running |
| **cost_monitor_1** | Track API costs | llama3.2:1b | Always running |

## Example: Full Episode 1 Workflow

```
USER: "Create Episode 1 for YouTube (28 minutes)"

CLAUDE ORCHESTRATOR:
  ├─ Reads content_bootcamp.md
  ├─ Analyzes: Need full episode production
  └─ Creates tasks:
      1. Find Story 1 → story_indexer_1
      2. Adapt to script → script_writer_1
      3. Generate image prompts → image_prompter_1 (parallel)
      4. Format dialogue → dialogue_formatter_1 (parallel)
      5. Plan sound design → sound_designer_1 (parallel)
      6. Review quality → qa_content_1
      7. Create metadata → metadata_gen_1
      8. Extract clips → social_clipper_1

BOT EXECUTION:
  ├─ story_indexer_1: "Found Story_01_The_Knock_That_Changes_Everything_v3.md"
  ├─ script_writer_1: "Adapted to 10 scenes, 28-minute script"
  ├─ [PARALLEL]
  │   ├─ image_prompter_1: "Generated 25 character/background prompts"
  │   ├─ dialogue_formatter_1: "Formatted 50 dialogue lines for ElevenLabs"
  │   └─ sound_designer_1: "Specified music cues and SFX"
  ├─ qa_content_1: "Score 9/10, approved for production"
  ├─ metadata_gen_1: "Created YouTube title, description, tags"
  └─ social_clipper_1: "Extracted 7 promotional clips"

RESULT:
  ✓ Script ready for animation
  ✓ Image prompts ready for generation
  ✓ Dialogue ready for voice synthesis
  ✓ Sound design plan complete
  ✓ Quality verified
  ✓ Metadata ready for upload

Total bot time: 15-20 minutes
(External image/voice generation: 2-3 hours additional)
```

## Key Advantages

### From Friend's Architecture:
1. **Help Queue System** - Bots automatically escalate when stuck
2. **Parallel Execution** - Multiple bots work simultaneously
3. **Knowledge Base** - ChromaDB stores all patterns and context
4. **LoRA Adapters** - System learns your preferences over time
5. **Always-Running Bots** - Continuous monitoring and indexing

### Adapted for Content:
1. **Story Indexing** - Automatically indexes 60 story files
2. **Multi-Format** - YouTube, podcast, social media
3. **Asset Tracking** - Monitors images, audio, video files
4. **Cost Management** - Tracks API usage (target: <$50/episode)
5. **Quality Assurance** - Checks story accuracy and consistency

## Cost Efficiency

- **90%+ local processing**: Free (via Ollama on ProArt RTX 5090)
- **10% cloud processing**: Claude orchestrator only (~$1-2 per episode)
- **Total estimate**: $2-5 per episode vs $50-200 all-cloud

## Next Steps

1. **Test basic functionality**:
   ```bash
   # Start system
   python -m src.orchestrator.main

   # In another terminal, test
   curl http://localhost:8000/api/status
   ```

2. **Test story indexing**:
   - story_indexer_1 should automatically find your 60 story files
   - Check logs for "Indexed: Story_XX..."

3. **Test Episode 1 workflow**:
   - Send request to create Episode 1
   - Watch bots execute in parallel
   - Review generated script/prompts

4. **Integration** (future):
   - Connect to existing image_generator.py
   - Connect to ElevenLabs for voice
   - Connect to video editor (DaVinci Resolve/FFmpeg)

## Monitoring

Watch logs in terminal for:
- 🤖 Bot starts
- 📋 Task assignments
- 🆘 Help requests
- ✅ Completions
- ❌ Errors

## Troubleshooting

**"Bots not starting"**:
- Check Ollama is running: `ollama list`
- Verify models downloaded: `ollama list`

**"No story files found"**:
- Check path in config: `/home/activeloguser/Story_*_v3.md`
- Verify files exist: `ls ~/Story_*_v3.md | wc -l` (should be 60)

**"Claude API errors"**:
- Verify ANTHROPIC_API_KEY is set
- Check API key is valid

## Architecture Decisions

### Why This Approach?

1. **Scalable**: Add more bots without changing core system
2. **Fault-tolerant**: Help queue handles failures gracefully
3. **Cost-effective**: 90% local processing
4. **Learning**: LoRA adapters improve over time
5. **Parallel**: Multiple bots work simultaneously

### Key Design Patterns

- **Observer Pattern**: Message bus for bot communication
- **Strategy Pattern**: Different bots for different tasks
- **Chain of Responsibility**: Help queue escalation
- **Repository Pattern**: Knowledge base for data access

## See Also

- **BUILD_LOG.md** - Detailed build history
- **config/content_bootcamp.md** - Full system context for Claude
- **config/content_bot_configs.yaml** - All bot configurations

---

**Built**: 2025-10-12
**Based on**: Friend's multi-agent coding architecture
**Adapted for**: Loopless/SuperInstance content production
