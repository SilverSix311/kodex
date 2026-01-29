# Kodex Release & Packaging Guide

**Version**: 2.0.0  
**Last Updated**: January 29, 2026  
**Status**: ✅ Ready for Release

## Overview

This guide explains how to build, package, and release Kodex as a distributable executable.

## Prerequisites

1. **AutoHotkey v2** installed from https://www.autohotkey.com/
2. **Git** for managing releases
3. Kodex repository cloned locally

## Building the Executable

### Option 1: PowerShell (Recommended)

```powershell
# Navigate to kodex directory
cd d:\Code\kodex

# Run build script
.\build.ps1

# Output: dist/kodex.exe
```

**Features**:
- Auto-detects AutoHotkey v2 installation
- Embeds icon automatically
- Creates release package with documentation
- Shows build status and next steps

### Option 2: Batch Script

```batch
# Navigate to kodex directory
cd d:\Code\kodex

# Run build script
build.bat

# Output: dist/kodex.exe
```

### Option 3: Manual Compilation

1. Open AutoHotkey v2 Compiler GUI
2. Select `kodex.ahk` as source
3. Set output to `dist/kodex.exe`
4. Set icon to `kodex.ico` (optional)
5. Click "Convert"

## Build Output

### Single Executable
```
dist/kodex.exe          (Standalone executable, ~3-5 MB)
```

### Release Package
```
dist/kodex-v2.0.0/
├── kodex.exe
├── README.md
├── MIGRATION_GUIDE.md
├── TICKET_TRACKER_README.md
└── kodex.ini

dist/kodex-v2.0.0.zip   (Packaged for distribution)
```

## Testing the Build

```powershell
# Test standalone executable
.\dist\kodex.exe

# Verify functionality
.\smoke_test.ahk
```

**Expected Results**:
- GUI opens without errors
- Hotkeys respond correctly
- No console errors displayed

## GitHub Release Process

### Step 1: Create Release Tag

```bash
git tag -a v2.0.0 -m "Release version 2.0.0 - AutoHotkey v2 Migration"
git push origin v2.0.0
```

### Step 2: Create Release on GitHub

1. Go to: https://github.com/SilverSix311/kodex/releases
2. Click "Create a new release"
3. Select tag: `v2.0.0`
4. Fill in release notes (see template below)

### Step 3: Upload Release Assets

Attach these files to the release:

1. **kodex.exe** (Standalone executable)
   - Type: Application/Executable
   - Size: ~3-5 MB
   - Usage: Direct download and run

2. **kodex-v2.0.0.zip** (Full package)
   - Type: Archive
   - Size: ~4-6 MB
   - Includes: Documentation, config, executable

### Step 4: Publish Release

Click "Publish release" to make it public.

## Release Notes Template

```markdown
# Kodex v2.0.0 - AutoHotkey v2 Migration Complete

## 🎉 What's New

### Major Update: Full AutoHotkey v2 Migration
- ✅ All 18 core scripts migrated to AutoHotkey v2
- ✅ Modern syntax: GuiCreate(), LoopFiles(), try/catch
- ✅ Improved error handling and reliability
- ✅ Function-based architecture for better maintainability

### New Features
- ✨ **Freshdesk Ticket Time Tracker** - Track time on support tickets (Ctrl+Shift+T)
- 📊 CSV logging with automatic date-based filenames
- ⏱️ Transparent overlay timer for active tracking
- 🧪 Automated smoke-test suite for validation

### Breaking Changes ⚠️
- **AutoHotkey v1 is no longer supported**
- Requires AutoHotkey v2 (install from https://www.autohotkey.com/)
- All v1 scripts must be updated to v2 syntax

## 📥 Installation

### Quick Start
1. Download `kodex.exe`
2. Install AutoHotkey v2 from https://www.autohotkey.com/
3. Double-click `kodex.exe` to run
4. Press `Ctrl+Alt+K` to open hotstring manager

### From Source
```bash
git clone https://github.com/SilverSix311/kodex.git
cd kodex
AutoHotkey.exe kodex.ahk
```

## 📚 Documentation

- **README.md** - Project overview and quick start
- **MIGRATION_GUIDE.md** - Detailed v1→v2 conversion guide
- **TICKET_TRACKER_README.md** - Time tracker feature documentation
- **.github/copilot-instructions.md** - Complete API reference

## 🔧 Technical Details

### File Sizes
- kodex.exe: ~3.5 MB (standalone)
- kodex-v2.0.0.zip: ~5 MB (with documentation)

### Requirements
- Windows 10/11
- AutoHotkey v2.0 or later
- ~5 MB disk space

### Known Limitations
- Single-instance only (one Kodex window)
- Requires exact Freshdesk URL format for time tracker
- CSV files stored locally

## 🐛 Bug Reports & Features

Found an issue? Have a feature request?
- Open an issue: https://github.com/SilverSix311/kodex/issues
- See documentation for troubleshooting steps

## 📖 Changelog

### v2.0.0 (January 29, 2026)
- Full AutoHotkey v2 migration (18 files)
- 8 helper functions converted
- 8 GUI files refactored
- 3 utility scripts updated
- Freshdesk time tracker feature
- Comprehensive documentation
- Automated test suite

### v1.x (Previous)
- AutoHotkey v1 implementation
- Original hotstring engine
- Basic GUI management

## 🙏 Credits

Migration completed January 2026  
Based on original Kodex application  
Maintained by SilverSix311

## 📄 License

See LICENSE file for details

---

**Ready to use!** Download, extract, and run. Enjoy Kodex v2!
```

## Release Checklist

Before publishing a release:

- [ ] Build executable successfully (`build.ps1`)
- [ ] Test executable locally
- [ ] Run smoke tests (`smoke_test.ahk`)
- [ ] Verify documentation is current
- [ ] Update CHANGELOG.md with version notes
- [ ] Create git tag (`git tag -a v2.0.0`)
- [ ] Create GitHub release draft
- [ ] Upload executable and zip package
- [ ] Fill in release notes
- [ ] Review for accuracy
- [ ] Publish release

## Automating Builds (Optional)

### GitHub Actions Workflow

Create `.github/workflows/release.yml`:

```yaml
name: Build Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build executable
        run: |
          # Add build steps here
          # This requires AutoHotkey installed on runner
```

## Version Numbering

Follow semantic versioning: `MAJOR.MINOR.PATCH`

- **2.0.0** - Major: v2 migration (breaking changes)
- **2.0.1** - Patch: Bug fixes
- **2.1.0** - Minor: New features

## Troubleshooting

### Build Fails: "Ahk2Exe not found"

**Solution**: Ensure AutoHotkey v2 is installed in one of these locations:
- `C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe`
- `C:\Program Files (x86)\AutoHotkey\Compiler\Ahk2Exe.exe`
- `%USERPROFILE%\AppData\Local\AutoHotkey\Compiler\Ahk2Exe.exe`

### Executable won't run

**Solution**:
1. Verify AutoHotkey v2 is installed
2. Run smoke tests to check configuration
3. Check Windows Security/SmartScreen settings
4. Try running as Administrator

### GitHub Upload Fails

**Solution**:
1. Ensure git credentials are configured
2. Verify release tag exists locally and remote
3. Check file size limits (GitHub allows up to 2 GB per file)

## Distribution Methods

### Method 1: Direct Download
Users download executable from GitHub releases and run directly.

### Method 2: Installer
Create NSIS or MSI installer for Windows installation.

### Method 3: Package Manager
Submit to Windows Package Manager or Chocolatey.

### Method 4: Source Code
Users clone repository and run `.ahk` files directly.

## Security Considerations

- ⚠️ Code-signed binaries recommended for public distribution
- Consider implementing auto-update mechanism
- Provide SHA256 checksums for verification
- Document code review process

## Support & Updates

After releasing:

1. **Monitor Issues**: Watch GitHub issues for reported problems
2. **Plan Hotfixes**: Create v2.0.1, v2.0.2 as needed
3. **Plan Features**: Plan v2.1.0, v2.2.0 for new features
4. **Communication**: Keep users informed via release notes

## Next Release Planning

For v2.1.0 (Suggested):
- [ ] Cloud sync for CSV files
- [ ] Freshdesk API integration
- [ ] Advanced reporting UI
- [ ] Dark theme option
- [ ] Multi-language support

---

**Release Ready!** Follow these steps to publish Kodex v2.0.0 to the world.

For questions or issues, see the documentation or open a GitHub issue.
