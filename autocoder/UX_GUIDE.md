# AutoCoder UX Guide - For Everyone!

**Version**: 0.3.0
**Status**: ✅ Beginner-Friendly & Professional-Ready

---

## 🎯 What's New: User Experience Levels

AutoCoder now adapts to YOUR experience level! Whether you're a complete beginner or a seasoned pro, the interface adjusts to give you exactly what you need.

###  **Three Experience Levels**

1. **🎓 Beginner** - New to AI coding assistants
   - Helpful hints and tips appear automatically
   - Detailed explanations of what's happening
   - Warnings before expensive operations
   - Setup wizard guides you through everything
   - Perfect for learning!

2. **⚡ Intermediate** - Some experience with AI tools
   - Fewer hints, more efficiency
   - Keyboard shortcuts enabled
   - Higher daily budget
   - Good balance of help and speed

3. **🚀 Professional** - I know what I'm doing
   - Minimal UI, maximum efficiency
   - No confirmations or warnings
   - Highest daily budget ($50/day)
   - Power features and shortcuts

---

## 🌟 For Beginners: Getting Started

### First Time Setup

When you first run AutoCoder, you'll be greeted with a **friendly setup wizard**:

```bash
python3 main.py
```

The wizard will:
1. ✅ Ask about your experience level
2. ✅ Help you set a daily budget
3. ✅ Check if you have local models installed
4. ✅ Check if you have an API key
5. ✅ Give you a quick tutorial

**Total time**: 2 minutes!

### Your First Interaction

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                Welcome to AutoCoder! 🎉                      ║
║                                                              ║
║  A smart coding assistant that saves you money by using     ║
║  your local GPU for simple tasks and cloud AI only when     ║
║  needed for complex work.                                   ║
║                                                              ║
║  🎓 BEGINNER MODE ACTIVE                                     ║
║                                                              ║
║  Type ':help' to get started or just ask a question!        ║
║  Example: "Write a Python function to sort a list"          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

💡 Tip: Type ':help' to see all available commands

You: Write a Python function to calculate fibonacci numbers

→ Routing to qwen2.5-coder:7b (complexity: SIMPLE)
[Shows response - this ran on your GPU for FREE!]

💡 Tip: Green text means the task was handled locally for FREE

You: :cost
[Shows you've spent $0.00 so far]
```

### Helpful Commands for Beginners

```bash
:help       # See all commands
:examples   # See real usage examples
:cost       # Check your spending
:status     # See GPU temperature and system status
:profile    # See your settings
```

### Learning Examples

Type `:examples` to see:
- **Simple tasks**: "Write a function to..."
- **Code explanation**: "Explain how this works..."
- **Bug fixes**: "Why is my function returning None?"
- **Projects**: "Build a REST API for..."

Each example shows:
- What to type
- What model will handle it
- How much it costs (usually FREE!)

---

## ⚡ For Intermediate Users

### Quick Setup

If you're coming from another AI tool, the wizard still helps but asks fewer questions. You'll get:
- Higher default budget ($10/day)
- Keyboard shortcuts enabled
- Fewer confirmation dialogs

### Power Features You'll Love

**1. Keyboard Shortcuts**
```
Ctrl+R    # Search command history
↑/↓       # Navigate history
Ctrl+C    # Cancel operation
Ctrl+D    # Exit
```

**2. Quick Commands**
```bash
:h    # Help
:m    # Models
:c    # Cost
:s    # Status
:ctx  # Context
```

**3. Smart Defaults**
- Auto-decomposition ON
- Routing details visible
- No confirmation for moderate costs
- Context saved automatically

### Cost Optimization Tips

```bash
# Check costs regularly
:cost

# Set custom budget
:cost limit 20.00

# Force local for simple tasks
@local Write a helper function

# Use cloud for complex
@claude Design this system architecture
```

### Multi-Step Workflows

AutoCoder remembers context, so you can build incrementally:

```
You: Create a User model with fields name and email

[AutoCoder creates it]

You: Now add password hashing to that User model

[AutoCoder knows which User model you mean!]

You: Write tests for the User model

[Tests are aware of the hashing you just added]
```

---

## 🚀 For Professionals

### Minimal Setup

The wizard detects professional mode and asks minimal questions:

```
╔════════════════════════════════════════════════════════╗
║                                                        ║
║              AutoCoder v0.3.0 - Pro Mode               ║
║                                                        ║
║  Decomposition: ON | Budget: $50/day | GPU: Ready     ║
║  :h :m :c :s :ctx :q | @local @claude @haiku          ║
║                                                        ║
╚════════════════════════════════════════════════════════╝

You:
```

No hints, no tips, just the interface.

### Advanced Features

**1. Direct Profile Editing**
```bash
# Edit profile file directly
nano ~/.autocoder/profile.json

# Or use CLI
:profile set professional
```

**2. Context Inspection**
```bash
# View saved contexts
ls ~/.autocoder/contexts/

# Inspect specific session
cat ~/.autocoder/contexts/<session_id>.json

# Watch logs in real-time
tail -f logs/autocoder_$(date +%Y-%m-%d).jsonl
```

**3. Programmatic Control**
```python
# In main.py, disable features
router = Router(
    providers=providers,
    enable_decomposition=False  # Manual control
)

# Or set environment variables
export AUTOCODER_MAX_DAILY=100.00
export AUTOCODER_QUIET_MODE=1
```

**4. Cost Analysis**
```bash
# Export cost data
:cost

# Analyze with jq
cat logs/autocoder_*.jsonl | jq '.cost' | awk '{sum+=$1} END {print sum}'
```

**5. Parallel Workflows**
```bash
# Run multiple sessions
python3 main.py &  # Session 1
python3 main.py &  # Session 2

# Each gets its own context
ls ~/.autocoder/contexts/
```

---

## 🎮 Commands Reference

### Available Commands

| Command | Shortcut | Beginner | Intermediate | Professional |
|---------|----------|----------|--------------|--------------|
| `:help` | `:h` | ✓ Detailed | ✓ Concise | ✓ Minimal |
| `:examples` | `:ex` | ✓ Full guide | ✓ Patterns | ✓ Quick ref |
| `:models` | `:m` | ✓ Explained | ✓ Listed | ✓ Listed |
| `:cost` | `:c` | ✓ Breakdown | ✓ Summary | ✓ Numbers |
| `:status` | `:s` | ✓ Detailed | ✓ Key info | ✓ Minimal |
| `:context` | `:ctx` | ✓ Explained | ✓ Summary | ✓ Raw data |
| `:profile` | - | ✓ Settings | ✓ Settings | ✓ JSON path |
| `:setup` | - | ✓ Wizard | ✓ Fast setup | ✓ Skippable |

### Model Override Syntax

```bash
@local <task>    # Force local GPU (FREE)
@claude <task>   # Force Claude Sonnet (fast, $$$)
@haiku <task>    # Force Claude Haiku (balanced)
```

**When to use:**
- `@local`: Simple tasks, learning, cost-conscious
- `@claude`: Complex architecture, critical code
- `@haiku`: Moderate tasks, good balance

---

## 🎛️ Profile Settings

### View Your Profile

```bash
:profile

Your Profile
┌─────────────────────────┬──────────────┐
│ Experience Level        │ BEGINNER     │
│ Show Hints              │ Yes          │
│ Show Routing Details    │ Yes          │
│ Auto-Decompose          │ Yes          │
│ Confirm Expensive Tasks │ Yes          │
│ Daily Budget Limit      │ $5.00        │
└─────────────────────────┴──────────────┘
```

### Change Your Profile

```bash
:profile set beginner        # Switch to beginner
:profile set intermediate    # Switch to intermediate
:profile set professional    # Switch to professional
:profile set pro             # Shortcut for professional
```

### What Each Level Changes

| Setting | Beginner | Intermediate | Professional |
|---------|----------|--------------|--------------|
| Hints | ✓ On | ✗ Off | ✗ Off |
| Routing Details | ✓ Shown | ✓ Shown | ✗ Hidden |
| Cost Warnings | ✓ Yes | ✓ Yes | ✗ No |
| Confirmations | ✓ Yes | ✗ No | ✗ No |
| Verbose Errors | ✓ Yes | ✓ Yes | ✗ No |
| Shortcuts | ✗ No | ✓ Yes | ✓ Yes |
| Daily Budget | $5 | $10 | $50 |

---

## 💡 Tips & Tricks

### For Beginners

1. **Start Simple**
   ```
   You: Write a hello world function
   ```
   See how it works before trying complex tasks.

2. **Use :examples Frequently**
   ```
   :examples
   ```
   See real examples of what you can ask for.

3. **Check Costs After Each Task**
   ```
   :cost
   ```
   Understand what costs money and what's free.

4. **Don't Be Afraid to Ask**
   - AutoCoder is patient!
   - There's no such thing as a "dumb question"
   - Everything is logged so you can review later

5. **Use @local for Practice**
   ```
   @local Explain decorators
   ```
   Practice for FREE on your GPU.

### For Intermediate Users

1. **Build Context Incrementally**
   - Ask for one piece at a time
   - Each response becomes context for the next
   - More accurate than asking for everything at once

2. **Monitor Your Budget**
   ```
   :cost limit 15.00
   ```
   Set comfortable limits.

3. **Use Decomposition**
   - Let complex tasks decompose automatically
   - Watch the subtasks to learn

4. **Leverage Shortcuts**
   - `:h` instead of `:help`
   - `:c` instead of `:cost`
   - `:m` instead of `:models`

5. **Review Context**
   ```
   :context
   ```
   See what the models know about your conversation.

### For Professionals

1. **Customize Your Workflow**
   ```bash
   # Edit config directly
   nano ~/.autocoder/profile.json

   # Set environment variables
   export AUTOCODER_MAX_DAILY=100.00
   ```

2. **Analyze Cost Data**
   ```bash
   # Export and analyze
   cat logs/*.jsonl | jq '.cost' | stats
   ```

3. **Multiple Sessions**
   ```bash
   # Run concurrent sessions
   python3 main.py &
   ```

4. **Debug Decomposition**
   ```bash
   # Inspect decomposition plans
   cat ~/.autocoder/contexts/*.json | jq '.tasks'
   ```

5. **Batch Operations**
   ```bash
   # Script interactions
   echo "task 1" | python3 main.py
   echo "task 2" | python3 main.py
   ```

---

## 🐛 Troubleshooting

### Beginner-Friendly Errors

AutoCoder now gives helpful error messages tailored to your level:

**No API Key (Beginner Message)**:
```
❌ No API key found for Claude.

To use cloud models, you need an API key from Anthropic:
1. Go to https://console.anthropic.com
2. Create an account (free trial available!)
3. Get your API key
4. Run: export ANTHROPIC_API_KEY='your-key-here'

OR you can use local models only (FREE but slower):
- They'll be used automatically if no API key is set
- Perfect for practice and simple tasks!

Type ':help setup' for more details.
```

**No API Key (Professional Message)**:
```
❌ ANTHROPIC_API_KEY not set

  export ANTHROPIC_API_KEY='sk-ant-...'

Local models still available.
```

### Common Issues

1. **"I don't see hints"**
   - You're probably in Intermediate or Professional mode
   - Switch with: `:profile set beginner`

2. **"Too many confirmations"**
   - Switch to Intermediate or Professional
   - `:profile set intermediate`

3. **"Interface is too minimal"**
   - Switch to Beginner mode
   - `:profile set beginner`

4. **"Want to reset everything"**
   - Delete profile: `rm ~/.autocoder/profile.json`
   - Restart: `python3 main.py`
   - Setup wizard runs again!

---

## 📖 Examples by Experience Level

### Beginner Examples

```bash
# See full tutorial
:examples

# Try your first task
You: Write a Python function to add two numbers

# Check what it cost
:cost

# Try a FREE explanation
You: @local What is a Python decorator?

# Try something more complex
You: Build a simple todo list app

# See it decompose!
```

### Intermediate Examples

```bash
# Multi-step workflow
You: Create a User model
You: Add password hashing to User
You: Write tests for User

# Cost control
:cost limit 20.00
You: Build a REST API

# Check decomposition
:context

# Force specific routing
You: @haiku Implement JWT auth
```

### Professional Examples

```bash
# Quick task
You: refactor this for perf

# Check cost
:c

# Complex architecture
You: design distributed system for 1M users

# Inspect result
:ctx

# Export session
cat ~/.autocoder/contexts/*.json > backup.json
```

---

## 🎯 Best Practices

### For Everyone

1. **Start with Your Level**
   - Be honest about your experience
   - You can always change later

2. **Use :examples**
   - See what's possible
   - Learn from examples

3. **Check :cost Regularly**
   - Understand your spending
   - Adjust as needed

4. **Build Context**
   - Ask follow-up questions
   - Reference previous work

5. **Experiment**
   - Try different models (@local, @claude)
   - See what works best for you

---

## 📊 Feature Comparison

| Feature | Beginner | Intermediate | Professional |
|---------|----------|--------------|--------------|
| **Welcome Message** | Full tutorial | Quick intro | Minimal header |
| **Hints** | Every 5 interactions | Rarely | Never |
| **Examples** | Full guide | Pattern library | Quick reference |
| **Error Messages** | Detailed + links | Concise + tips | Minimal |
| **Confirmations** | Before $ operations | Rarely | Never |
| **Routing Display** | Always visible | Visible | Hidden |
| **Shortcuts** | Disabled | Enabled | Enabled |
| **Daily Budget** | $5 | $10 | $50 |
| **Setup Wizard** | Full walkthrough | Quick setup | Skippable |

---

## 🚀 Upgrading Your Experience

### From Beginner to Intermediate

When you're comfortable:
```bash
:profile set intermediate
```

You'll notice:
- Fewer hints and tips
- Faster interface
- Higher budget
- More trust in your decisions

### From Intermediate to Professional

When you're a power user:
```bash
:profile set professional
```

You'll get:
- Minimal UI
- No hand-holding
- Maximum efficiency
- Full control

### Going Back

Changed your mind? No problem:
```bash
:profile set beginner    # Back to beginner
:setup                   # Re-run wizard
```

---

## 📝 Summary

AutoCoder now has **three experience levels** that adapt the interface to you:

✅ **Beginners** get:
- Welcome wizard
- Helpful hints and tips
- Detailed explanations
- Example library
- Safety confirmations

✅ **Intermediate users** get:
- Balanced interface
- Keyboard shortcuts
- Fewer interruptions
- Higher budget

✅ **Professionals** get:
- Minimal UI
- Maximum efficiency
- No confirmations
- Full control

**Switch anytime**: `:profile set <level>`

**Try it now:**
```bash
python3 main.py
```

The first time you run it, the friendly setup wizard will guide you through everything!

---

**Version**: 0.3.0
**Status**: ✅ Ready for All Skill Levels
**Feedback**: We learn from YOU - the interface adapts!
