#!/bin/bash
# Create a release package for AI Builder CLI

echo "📦 Creating AI Builder CLI Release Package..."

# Create release directory
RELEASE_DIR="aibuilder-cli-release"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

echo "📁 Created release directory: $RELEASE_DIR"

# Copy core files
echo "📄 Copying core files..."
cp aibuilder "$RELEASE_DIR/"
cp working_ai_builder.py "$RELEASE_DIR/"
cp README.md "$RELEASE_DIR/"

# Copy installation scripts
echo "🔧 Copying installation scripts..."
cp install.sh "$RELEASE_DIR/"
cp install-windows.ps1 "$RELEASE_DIR/"
cp WINDOWS-INSTALL.md "$RELEASE_DIR/"

# Copy Windows files
echo "🪟 Copying Windows files..."
cp aibuilder.bat "$RELEASE_DIR/"
cp aibuilder.cmd "$RELEASE_DIR/"

# Make scripts executable
chmod +x "$RELEASE_DIR/aibuilder"
chmod +x "$RELEASE_DIR/install.sh"

# Create a quick start guide
cat > "$RELEASE_DIR/QUICK-START.md" << 'EOF'
# 🚀 AI Builder CLI - Quick Start

## Linux/Mac Installation
```bash
./install.sh
```

## Windows Installation
```powershell
.\install-windows.ps1
```

## Usage
```bash
aibuilder "a task management app"
aibuilder --interactive
aibuilder --help
```

## What You Get
- ✅ Complete working applications
- ✅ Professional UI/UX
- ✅ Backend + Frontend + Database
- ✅ Ready to run with npm start

Built with Local AI Processing Power 🧠
EOF

# Create version info
cat > "$RELEASE_DIR/VERSION" << EOF
AI Builder CLI v1.0.0
Built: $(date)
Platform: Cross-platform (Linux, Mac, Windows)
Requirements: Python 3.7+, Node.js (for running built apps)
EOF

echo "📋 Created quick start guide and version info"

# Create archive
echo "📦 Creating release archive..."
tar -czf "${RELEASE_DIR}.tar.gz" "$RELEASE_DIR"
zip -r "${RELEASE_DIR}.zip" "$RELEASE_DIR" > /dev/null 2>&1

echo "✅ Release package created:"
echo "  📁 Directory: $RELEASE_DIR/"
echo "  📦 Archive: ${RELEASE_DIR}.tar.gz"
echo "  📦 Zip file: ${RELEASE_DIR}.zip"

# Show contents
echo ""
echo "📄 Package contents:"
ls -la "$RELEASE_DIR/"

echo ""
echo "🎉 AI Builder CLI release package ready!"
echo "📤 Ready to distribute to users on all platforms"