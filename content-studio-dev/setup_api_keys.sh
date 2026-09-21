#!/bin/bash
# Setup API Keys - Interactive Guide
# Helps you get API keys from all providers

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Multi-Model API Setup - Get Your Keys              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "We'll get API keys from 3 providers:"
echo "  1. Anthropic Claude (required)"
echo "  2. OpenAI GPT (optional but recommended)"
echo "  3. Groq (FREE tier - highly recommended!)"
echo ""
echo "This will take about 5-10 minutes."
echo ""

read -p "Ready to start? (y/n): " ready
if [[ ! "$ready" =~ ^[Yy]$ ]]; then
    echo "No problem! Run this script again when ready."
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Anthropic Claude API Key"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Open: https://console.anthropic.com/"
echo "2. Sign in or create account"
echo "3. Click 'API Keys' in sidebar"
echo "4. Click 'Create Key'"
echo "5. Name it: 'Content Studio v2'"
echo "6. Copy the key (starts with sk-ant-)"
echo ""
read -p "Press ENTER when you have your Claude key..."
echo ""
read -p "Paste your Claude API key: " claude_key

if [[ -z "$claude_key" ]] || [[ "$claude_key" == "your_anthropic_api_key_here" ]]; then
    echo "⚠️  Skipping Claude key (you can add it to .env later)"
    claude_key="your_anthropic_api_key_here"
else
    echo "✓ Claude key received"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: OpenAI API Key (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Open: https://platform.openai.com/api-keys"
echo "2. Sign in or create account"
echo "3. Click '+ Create new secret key'"
echo "4. Name it: 'Content Studio'"
echo "5. Copy the key (starts with sk-proj- or sk-)"
echo ""
read -p "Do you want to add OpenAI? (y/n): " add_openai
openai_key=""

if [[ "$add_openai" =~ ^[Yy]$ ]]; then
    read -p "Paste your OpenAI API key: " openai_key
    if [[ -n "$openai_key" ]]; then
        echo "✓ OpenAI key received"
    else
        echo "⚠️  No key entered, skipping"
    fi
else
    echo "⚠️  Skipping OpenAI (you can add it later)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Groq API Key (FREE - Recommended!)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Groq offers FREE tier with ultra-fast inference!"
echo ""
echo "1. Open: https://console.groq.com/"
echo "2. Sign up (it's FREE!)"
echo "3. Click 'API Keys'"
echo "4. Click 'Create API Key'"
echo "5. Copy the key (starts with gsk_)"
echo ""
read -p "Do you want to add Groq? (y/n): " add_groq
groq_key=""

if [[ "$add_groq" =~ ^[Yy]$ ]]; then
    read -p "Paste your Groq API key: " groq_key
    if [[ -n "$groq_key" ]]; then
        echo "✓ Groq key received"
    else
        echo "⚠️  No key entered, skipping"
    fi
else
    echo "⚠️  Skipping Groq (but you should really get this - it's FREE!)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Updating .env file..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Update .env file
if [[ -n "$claude_key" ]]; then
    sed -i "s|ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$claude_key|" .env
fi

if [[ -n "$openai_key" ]]; then
    sed -i "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$openai_key|" .env
fi

if [[ -n "$groq_key" ]]; then
    sed -i "s|GROQ_API_KEY=.*|GROQ_API_KEY=$groq_key|" .env
fi

echo "✓ .env file updated"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

keys_added=0
if [[ -n "$claude_key" ]] && [[ "$claude_key" != "your_anthropic_api_key_here" ]]; then
    echo "✓ Claude API key added"
    ((keys_added++))
else
    echo "✗ Claude API key missing"
fi

if [[ -n "$openai_key" ]]; then
    echo "✓ OpenAI API key added"
    ((keys_added++))
else
    echo "⚠ OpenAI API key not added (optional)"
fi

if [[ -n "$groq_key" ]]; then
    echo "✓ Groq API key added (FREE tier!)"
    ((keys_added++))
else
    echo "⚠ Groq API key not added (but highly recommended - it's FREE!)"
fi

echo ""
if [[ $keys_added -eq 0 ]]; then
    echo "No API keys added. You'll need at least one to continue."
    echo "Edit .env manually or run this script again."
elif [[ $keys_added -eq 1 ]]; then
    echo "✓ Ready to test with $keys_added provider!"
    echo ""
    echo "Next step: Run the test script"
    echo "  python test_api_v2.py"
else
    echo "✓ Ready to test with $keys_added providers!"
    echo ""
    echo "Next steps:"
    echo "  1. Test APIs: python test_api_v2.py"
    echo "  2. Compare costs: python compare_costs.py"
    echo "  3. Read: cat GETTING_STARTED_V2.md"
fi

echo ""
echo "Note: You can always add more providers later by editing .env"
echo ""
