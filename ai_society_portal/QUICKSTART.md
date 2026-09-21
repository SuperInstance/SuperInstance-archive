# 🚀 AI Society Portal - Quick Start Guide

## ⚡ Get Running in 5 Minutes

### 1. Prerequisites Check
```bash
# Verify you have:
python --version  # Should be 3.9+
node --version    # Should be 16+
docker --version  # For vector database
```

### 2. Start Vector Database
```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### 3. Backend Setup
```bash
cd ai_society_portal/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies (takes 2-3 minutes)
pip install -r requirements.txt

# Set up your API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and ANTHROPIC_API_KEY

# Start the server
python api_server.py
```

Backend will run at: `http://localhost:8000`

### 4. Frontend Setup (New Terminal)
```bash
cd ai_society_portal/frontend

# Install dependencies (takes 2-3 minutes)
npm install

# Start development server
npm start
```

Frontend will open at: `http://localhost:3000`

---

## 🎯 Your First Session

### Create a Character
1. Open http://localhost:3000
2. Click "➕ Create Character"
3. Fill in:
   ```
   Name: Dr. Nova
   Specialization: AI Researcher
   Backstory: Fascinated by emergent intelligence and creative systems...
   Skills: Machine Learning, Systems Thinking, Philosophy
   Goals: Understand consciousness
   ```
4. Click "Create Character"

### Create a Room
1. Click "➕ Create Room"
2. Select:
   ```
   Name: Creative Lab
   Room Type: jazz_club
   Purpose: Explore creative AI ideas
   ```
3. Add Dr. Nova to the room
4. Click "Create Room"

### Start Conversation
1. In the Rooms list, find "Creative Lab"
2. Click "▶️ Start" 
3. Click "👁️ Watch" to open live window
4. Watch the conversation stream!

---

## 💡 What to Try

### Experiment with Room Types
- **Jazz Club**: Creative, improvisational discussions
- **Laboratory**: Rigorous, evidence-based analysis
- **Study Hall**: Focused work with occasional peer questions
- **Debate Hall**: Adversarial idea testing

### Try Multiple Characters
Create 3-4 characters with different specializations:
- A creative (poet, designer)
- An analyst (scientist, engineer)
- A philosopher (deep thinker)
- A builder (maker, coder)

Watch how they interact differently in different rooms!

### Use Human-in-the-Loop
While watching a conversation:
- Click ⏸️ to pause
- Click 💬 to inject your own message
- See how characters respond to your input

### Monitor Activity
Watch in real-time:
- What characters are saying
- What they're working on (laptop activity)
- Token consumption
- Room atmosphere effects

---

## 🐛 Troubleshooting

**Backend won't start**
- Check you have API keys in .env
- Verify virtual environment is activated
- Check port 8000 isn't in use

**Frontend won't connect**
- Ensure backend is running on port 8000
- Check browser console for errors
- Try hard refresh (Ctrl+Shift+R)

**No conversations happening**
- Verify characters are added to the room
- Check you clicked "Start Session"
- Look at backend terminal for errors

**WebSocket not connecting**
- Check backend logs for websocket errors
- Verify no firewall blocking port 8000
- Try closing and reopening room window

---

## 📚 Next Steps

1. **Read the main README.md** for comprehensive documentation
2. **Explore different room types** to see how atmosphere affects thinking
3. **Create specialized characters** for specific domains
4. **Try multi-round sessions** to see knowledge building
5. **Experiment with room objects** (books, music, visuals)

---

## 🎓 Learning Resources

### Understanding Room Types
Each room type creates different cognitive effects:
- `jazz_club` (T=0.85): High creativity, associative thinking
- `laboratory` (T=0.2): Low creativity, high precision
- `coffee_house` (T=0.6): Balanced, social comfort
- `study_hall` (T=0.5): Focused, independent work

### Character Development
Characters build memories across sessions:
- Working memory: Current conversation
- Episodic memory: Specific experiences
- Semantic memory: General knowledge

### Cost Management
- Study Hall: ~$0.05 per 10-minute session
- Coffee House: ~$0.10-0.20 per 20-minute session
- Jazz Club: ~$0.30-0.50 per 30-minute session

Use cheaper models (GLM-4, DeepSeek) for exploration!

---

## ✨ Pro Tips

1. **Start simple**: Create 2-3 characters, one room, short sessions
2. **Watch the feed**: See how room atmosphere actually affects responses
3. **Pause often**: Inject questions or change direction
4. **Try contrasts**: Same characters, different rooms → different insights
5. **Let characters work at home**: Build their backstory through projects

---

## 🤝 Get Help

- Check the main README.md for detailed documentation
- Look at backend logs for error messages
- Open browser console (F12) for frontend errors
- File issues on GitHub (coming soon)

---

**Happy Building! 🎉**

The AI Society awaits your characters...
