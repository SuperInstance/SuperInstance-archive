# 🪟 AI Builder CLI - Windows Installation Guide

**Build applications from natural language descriptions on Windows!**

## 🚀 Quick Install (PowerShell Method - Recommended)

1. **Download the AI Builder files** to a folder (e.g., `C:\AIBuilder\`)

2. **Open PowerShell as Administrator** (right-click PowerShell → "Run as Administrator")

3. **Navigate to the AI Builder folder:**
   ```powershell
   cd "C:\AIBuilder"
   ```

4. **Run the installer:**
   ```powershell
   .\install-windows.ps1
   ```

5. **Follow the prompts** - the installer will:
   - ✅ Check Python installation
   - ✅ Copy files to the right location
   - ✅ Add to your PATH
   - ✅ Create desktop shortcut (optional)

6. **Start using it:**
   ```cmd
   aibuilder "a task management app"
   ```

---

## 🛠️ Manual Installation (If PowerShell doesn't work)

### Step 1: Prerequisites
- **Python 3.7+** installed from [python.org](https://python.org)
- **Make sure "Add Python to PATH"** was checked during installation

### Step 2: Download Files
Download these files to a folder (e.g., `C:\AIBuilder\`):
- `aibuilder` (main script)
- `aibuilder.bat` (Windows wrapper)
- `aibuilder.cmd` (alternative wrapper)
- `working_ai_builder.py` (core functionality)

### Step 3: Add to PATH
1. **Copy the folder path** (e.g., `C:\AIBuilder\`)
2. **Open System Environment Variables:**
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   - Click "Environment Variables"
   - Under "User Variables", select "Path", click "Edit"
   - Click "New" and paste your folder path
   - Click OK on all dialogs

### Step 4: Test Installation
Open Command Prompt and run:
```cmd
aibuilder --help
```

---

## 🎯 Usage Examples

```cmd
REM Build any app from description
aibuilder "a todo list app with priorities"

REM Custom options
aibuilder "blog platform" --name myblog --port 3001

REM List built apps
aibuilder --list

REM Interactive mode
aibuilder --interactive
```

---

## 🔧 Troubleshooting

### "Python is not recognized"
- Reinstall Python from [python.org](https://python.org)
- **Check "Add Python to PATH"** during installation
- Or add Python manually to PATH

### "'aibuilder' is not recognized"
- Make sure the AI Builder folder is in your PATH
- Try using the full path: `C:\AIBuilder\aibuilder.bat`
- Or run from the AI Builder directory

### PowerShell Execution Policy Error
Run this in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Permission Errors
- Run Command Prompt or PowerShell as Administrator
- Or install to a user directory instead of Program Files

---

## 📁 File Structure

After installation, you'll have:
```
C:\Users\YourName\AppData\Local\AIBuilder\
├── aibuilder           # Main Python script
├── aibuilder.bat       # Windows batch wrapper
└── working_ai_builder.py # Core functionality

Your built apps will be in:
C:\Users\YourName\AppData\Local\AIBuilder\built_apps\
```

---

## 🚀 What You Can Build

```cmd
aibuilder "expense tracker with categories"
aibuilder "chat app for my team"
aibuilder "inventory management system"
aibuilder "blog with user authentication"
aibuilder "dashboard with real-time charts"
aibuilder "recipe manager with search"
aibuilder "project tracker with kanban board"
```

Each app gets:
- ✅ **Complete backend** (Node.js server)
- ✅ **Professional frontend** (HTML/CSS/JavaScript)
- ✅ **Database operations** (in-memory or configurable)
- ✅ **Ready to run** with `npm start`

---

## 🎯 Starting Your Apps

After building an app:
```cmd
cd "C:\Users\YourName\AppData\Local\AIBuilder\built_apps\your-app-name"
npm start
```

Visit: `http://localhost:3000`

---

## 🔄 Updates

To update AI Builder:
1. Download new files
2. Run `install-windows.ps1` again
3. It will overwrite the old installation

---

## 🆘 Support

If you run into issues:
1. **Check Python installation:** `python --version`
2. **Check PATH:** `echo %PATH%` (should include AI Builder folder)
3. **Try full path:** `C:\AIBuilder\aibuilder.bat --help`
4. **Run as Administrator** if permission errors

---

**🎉 Ready to build applications with AI on Windows!**

```cmd
aibuilder "describe your dream application here"
```