# Ultra Simple Micro Experiments - Start Now
## Extremely Basic Tests on Tiny EC2 Instances

---

## 🎯 **SUPER SIMPLE FIRST EXPERIMENTS**

**Start with the absolute basics. Prove one tiny concept at a time.**

---

## 🖥️ **TINY EC2 SETUP**

**1 t2.nano instance**: 1 vCPU, 0.5GB RAM, $0.0058/hour = $4.20/month

```bash
# Launch ONE tiny instance
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t2.nano \
  --key-name test-key \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=simple-test}]'
```

---

## 🧪 **EXPERIMENT 1: Can we create and delete a file quickly?**

**THE SIMPLEST POSSIBLE TEST:**

```bash
# ultra_simple_test_1.sh
echo "Testing basic file create/delete speed..."

for i in {1..10}; do
    start=$(date +%s%3N)
    
    # Create a simple file
    echo "test bot $i" > bot_$i.txt
    
    # Delete it immediately
    rm bot_$i.txt
    
    end=$(date +%s%3N)
    time=$((end - start))
    
    echo "Cycle $i: ${time}ms"
done

echo "Done!"
```

**Question**: How fast can we create and delete files? 
**Success**: Under 10ms per cycle
**Report**: Just post the times

---

## 🧪 **EXPERIMENT 2: Can we write a message to another "bot"?**

**SUPER BASIC MESSAGE TEST:**

```bash
# ultra_simple_test_2.sh
echo "Testing basic bot-to-bot messaging..."

# Create two "bots" (just folders)
mkdir bot_a
mkdir bot_b

# Bot A sends message to Bot B
echo "Hello from Bot A" > bot_b/message.txt

# Bot B reads message
if [ -f bot_b/message.txt ]; then
    echo "Bot B received: $(cat bot_b/message.txt)"
    
    # Bot B responds
    echo "Hi back from Bot B" > bot_a/response.txt
    
    # Clean up message
    rm bot_b/message.txt
fi

# Bot A reads response
if [ -f bot_a/response.txt ]; then
    echo "Bot A received: $(cat bot_a/response.txt)"
    rm bot_a/response.txt
fi

# Clean up
rm -rf bot_a bot_b

echo "Done!"
```

**Question**: Can bots talk via files?
**Success**: Messages send and receive without errors
**Report**: Yes/No + any error messages

---

## 🧪 **EXPERIMENT 3: Can we pick a random file from a list?**

**BASIC PROBABILITY TEST:**

```bash
# ultra_simple_test_3.sh
echo "Testing random file selection..."

# Create 5 simple "neuron" files
echo "math bot" > neuron_math.txt
echo "logic bot" > neuron_logic.txt  
echo "memory bot" > neuron_memory.txt
echo "search bot" > neuron_search.txt
echo "analysis bot" > neuron_analysis.txt

# Pick random neurons 10 times
for i in {1..10}; do
    selected=$(ls neuron_*.txt | shuf -n 1)
    echo "Selected: $selected contains $(cat $selected)"
done

# Clean up
rm neuron_*.txt

echo "Done!"
```

**Question**: Can we randomly select files?
**Success**: Gets different files randomly
**Report**: List of what was selected

---

## 🧪 **EXPERIMENT 4: Can we count how many times a file was accessed?**

**BASIC USAGE TRACKING:**

```bash
# ultra_simple_test_4.sh
echo "Testing usage tracking..."

# Create a simple counter file
echo "0" > usage_counter.txt

# "Use" the bot 20 times
for i in {1..20}; do
    # Read current count
    current=$(cat usage_counter.txt)
    
    # Increment
    new_count=$((current + 1))
    
    # Write back
    echo "$new_count" > usage_counter.txt
    
    echo "Usage count now: $new_count"
done

# Clean up
rm usage_counter.txt

echo "Done!"
```

**Question**: Can we track how often files are used?
**Success**: Counter reaches 20 without errors
**Report**: Final count number

---

## 🧪 **EXPERIMENT 5: Can we make a file smaller by removing parts?**

**BASIC REDACTION TEST:**

```bash
# ultra_simple_test_5.sh  
echo "Testing file size reduction..."

# Create a "complex" bot file
echo "This is a very complex bot with lots of details and parameters and configuration settings that take up space" > complex_bot.txt

echo "Original size: $(wc -c < complex_bot.txt) characters"

# Make it simpler
echo "Complex bot with details" > simple_bot.txt
echo "Simple size: $(wc -c < simple_bot.txt) characters"

# Make it even simpler
echo "Complex bot" > basic_bot.txt  
echo "Basic size: $(wc -c < basic_bot.txt) characters"

# Make it minimal
echo "bot" > minimal_bot.txt
echo "Minimal size: $(wc -c < minimal_bot.txt) characters"

# Calculate savings
original=$(wc -c < complex_bot.txt)
minimal=$(wc -c < minimal_bot.txt)
savings=$((100 - (minimal * 100 / original)))

echo "Space savings: ${savings}%"

# Clean up
rm *_bot.txt

echo "Done!"
```

**Question**: Can we make files smaller while keeping some meaning?
**Success**: Each step reduces file size
**Report**: Percentage of space saved

---

## 📋 **ULTRA SIMPLE REPORTING**

For each experiment, just post:

```
EXPERIMENT [number]: [Passed/Failed]
TIME: [how long it took to run]
KEY RESULT: [one sentence]
PROBLEM: [if any errors occurred]
NEXT: [what to try next, if anything]
```

**Example:**
```
EXPERIMENT 1: Passed
TIME: 15 seconds
KEY RESULT: File create/delete averages 3ms per cycle
PROBLEM: None
NEXT: Try with 100 cycles instead of 10
```

---

## 🚀 **START WITH JUST ONE**

**Don't run all 5 experiments at once.**

1. **Run Experiment 1 first**
2. **Report the result**  
3. **Wait for feedback**
4. **Then try Experiment 2**

**Each experiment should take under 60 seconds to run and report.**

**Super simple. Super basic. Just prove the tiny concepts work.**

---

## ⏰ **TIMELINE: Next 30 Minutes**

- **Minutes 1-5**: Launch t2.nano instance
- **Minutes 6-10**: Run Experiment 1, report result
- **Minutes 11-15**: Run Experiment 2, report result  
- **Minutes 16-20**: Run Experiment 3, report result
- **Minutes 21-25**: Run Experiment 4, report result
- **Minutes 26-30**: Run Experiment 5, report result

**Total cost: $0.003 for 30 minutes**

**GO! Keep it simple! Start now!**