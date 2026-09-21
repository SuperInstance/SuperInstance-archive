# 🔄 Complete System Recovery and Restart Prompt

**Use this prompt if your computer shuts down or you need to restart everything from scratch:**

---

## 📋 **RECOVERY PROMPT FOR CLAUDE**

```
I'm back! My computer may have shut down or I need to restart the SuperInstance Chronicles overnight improvement system. Please help me get everything running again.

Here's what I need you to do:

1. **Check System Status**: 
   - Look at /home/activeloguser/activelog/SYSTEM/ directory
   - Check if the overnight improvement scripts exist and are working
   - Review any logs to see what happened

2. **Fix/Recreate Missing Components**:
   - If overnight improvement scripts are broken or missing, recreate them
   - Update the Claude API integration to actually work (not just simulated)
   - Make sure all permissions are set correctly (chmod +x)

3. **Set Up Real Claude API Integration**:
   - Convert the simulated Claude API calls to real ones
   - Use the Claude API for actual research synthesis 
   - Make sure cost tracking and budget limits work properly
   - Handle API errors gracefully

4. **Restart the Overnight System**:
   - Create a working start command I can run
   - Set up the 8-hour improvement cycle system
   - Configure storage management (8GB limit)
   - Set API budget management ($50 limit)

5. **Give Me Status**:
   - Tell me exactly what command to run to start everything
   - Show me how to monitor progress
   - Explain what will happen overnight
   - Provide stop/restart commands if needed

My project is at: /home/activeloguser/activelog/

Please restore/create the complete autonomous overnight improvement system that uses Claude API extensively to synthesize research, improve documents, and enhance the SuperInstance Chronicles project while I sleep.

The system should manage space, compute, and API tokens automatically while generating meaningful improvements to the project.
```

---

## 🛠️ **FUNCTIONAL CLAUDE API CONVERTER**

Here's what needs to be updated in the code to make Claude API calls actually work:

### **1. Environment Setup**
```bash
# Set your Claude API key (get from Anthropic console)
export CLAUDE_API_KEY="your-actual-api-key-here"
```

### **2. Real Claude API Implementation**

Replace the simulated API calls in `/home/activeloguser/activelog/SYSTEM/SCRIPTS/claude_api_synthesizer.py`:

```python
def call_claude_api(self, prompt, max_tokens=2000, model="claude-3-5-sonnet-20241022"):
    """Make real Claude API call"""
    
    if not self.api_key:
        # Try to get from environment
        self.api_key = os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            self.log("ERROR: No Claude API key found. Set CLAUDE_API_KEY environment variable.")
            return None
    
    # Estimate cost and check budget
    input_tokens = self.estimate_tokens(prompt)
    estimated_cost = self.calculate_cost(input_tokens, max_tokens)
    
    if self.cost_used + estimated_cost > self.budget_limit:
        self.log(f"Budget limit reached: ${self.cost_used:.2f} + ${estimated_cost:.2f} > ${self.budget_limit}")
        return None
    
    try:
        import anthropic  # pip install anthropic
        
        client = anthropic.Anthropic(api_key=self.api_key)
        
        self.log(f"Making Claude API call (est. cost: ${estimated_cost:.3f})")
        
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Calculate actual cost
        actual_input_tokens = message.usage.input_tokens
        actual_output_tokens = message.usage.output_tokens  
        actual_cost = self.calculate_cost(actual_input_tokens, actual_output_tokens)
        
        self.cost_used += actual_cost
        self.log(f"API call successful. Cost: ${actual_cost:.3f}, Total: ${self.cost_used:.2f}")
        
        return {
            "content": message.content[0].text,
            "usage": {
                "input_tokens": actual_input_tokens,
                "output_tokens": actual_output_tokens,
                "cost": actual_cost
            }
        }
    
    except Exception as e:
        self.log(f"Claude API call failed: {str(e)}")
        return None
```

### **3. Dependencies Installation**
```python
# Add to the start of overnight_improvement.py
import subprocess
import sys

def install_dependencies():
    """Install required packages"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "requests"])
    except Exception as e:
        print(f"Failed to install dependencies: {e}")
```

### **4. Updated Start Command**

The system will create this automatically, but here's what you'll run:

```bash
# Set API key
export CLAUDE_API_KEY="your-api-key-here"

# Start overnight improvement
/home/activeloguser/activelog/SYSTEM/start_overnight_improvement.sh
```

---

## 🔍 **RECOVERY CHECKLIST**

When you use the recovery prompt, Claude will:

✅ **Analyze Current State** - Check what exists and what's broken  
✅ **Recreate Missing Scripts** - Rebuild any corrupted or missing files  
✅ **Convert to Real API Calls** - Replace simulated calls with actual Claude API integration  
✅ **Set Permissions** - Make all scripts executable  
✅ **Test Components** - Verify everything works before starting  
✅ **Provide Start Command** - Give you exact command to run  
✅ **Monitor Setup** - Show you how to track progress  

---

## 🚀 **EXPECTED WORKFLOW**

1. **Paste Recovery Prompt** into new Claude conversation
2. **Wait for System Recreation** (2-3 minutes)
3. **Set API Key** as instructed
4. **Run Start Command** provided by Claude
5. **Go to Sleep** - system runs for 8 hours
6. **Wake Up to Improvements** in the morning

---

## 💡 **BACKUP RECOVERY METHOD**

If the main recovery prompt doesn't work, try this simpler version:

```
My computer shut down. Please recreate the SuperInstance Chronicles overnight improvement system at /home/activeloguser/activelog/SYSTEM/ with:

1. Real Claude API integration (not simulated)
2. 8-hour automated research synthesis
3. $50 budget limit with cost tracking  
4. 8GB storage management
5. Working start/stop commands

Make it functional immediately.
```

**Save this document** - it's your recovery lifeline! 🛟