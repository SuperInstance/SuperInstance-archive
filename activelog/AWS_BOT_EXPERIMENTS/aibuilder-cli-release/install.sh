#!/bin/bash
# AI Builder CLI Installation Script

echo "🤖 Installing AI Builder CLI..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AIBUILDER_PATH="$SCRIPT_DIR/aibuilder"

# Check if aibuilder exists
if [ ! -f "$AIBUILDER_PATH" ]; then
    echo "❌ Error: aibuilder not found at $AIBUILDER_PATH"
    exit 1
fi

# Make sure it's executable
chmod +x "$AIBUILDER_PATH"

# Create symlink in user's local bin (if it exists)
if [ -d "$HOME/.local/bin" ]; then
    ln -sf "$AIBUILDER_PATH" "$HOME/.local/bin/aibuilder"
    echo "✅ Installed aibuilder to ~/.local/bin/aibuilder"
    
    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo "⚠️  Warning: ~/.local/bin is not in your PATH"
        echo "   Add this to your ~/.bashrc or ~/.zshrc:"
        echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
else
    # Create ~/.local/bin if it doesn't exist
    mkdir -p "$HOME/.local/bin"
    ln -sf "$AIBUILDER_PATH" "$HOME/.local/bin/aibuilder"
    echo "✅ Created ~/.local/bin and installed aibuilder"
    echo "⚠️  Add this to your ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Try to install to /usr/local/bin if user has sudo access
if command -v sudo >/dev/null 2>&1; then
    echo ""
    echo "🔑 Would you like to install globally? (requires sudo)"
    read -p "Install to /usr/local/bin? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if sudo ln -sf "$AIBUILDER_PATH" /usr/local/bin/aibuilder; then
            echo "✅ Globally installed aibuilder to /usr/local/bin/aibuilder"
        else
            echo "❌ Failed to install globally"
        fi
    fi
fi

echo ""
echo "🎉 AI Builder CLI Installation Complete!"
echo ""
echo "Usage:"
echo "  aibuilder \"description of your app\"        # Build an app"
echo "  aibuilder --list                            # List built apps"
echo "  aibuilder --interactive                     # Interactive mode"
echo "  aibuilder --help                            # Show help"
echo ""
echo "Examples:"
echo "  aibuilder \"a task management app for teams\""
echo "  aibuilder \"blog platform\" --name myblog --port 3001 --start"
echo ""

# Test the installation
echo "Testing installation..."
if command -v aibuilder >/dev/null 2>&1; then
    echo "✅ aibuilder command is available!"
    aibuilder --help | head -5
else
    echo "⚠️  aibuilder command not found in PATH"
    echo "   Try running: $AIBUILDER_PATH --help"
fi

echo ""
echo "🚀 Ready to build applications with AI!"