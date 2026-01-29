Kodex
======

Text replacement/substitution application for Windows, written in **AutoHotkey v2**.

## Overview

Kodex is a powerful hotstring replacement engine that monitors your keyboard input and replaces typed phrases with predefined text or scripts. It's ideal for:

- **Text Expansion**: Type short abbreviations that expand to longer phrases
- **Macro Execution**: Run AutoHotkey scripts on demand via special hotstring prefixes
- **Productivity**: Organize replacements into bundles for different workflows
- **Customization**: Trigger replacements via Space, Tab, Enter, or automatically

## Quick Start

### Option A: Download Executable
1. Download `kodex.exe` from [GitHub Releases](https://github.com/SilverSix311/kodex/releases)
2. Install [AutoHotkey v2](https://www.autohotkey.com/)
3. Run `kodex.exe`
4. Press `Ctrl+Alt+K` to open the hotstring manager

### Option B: Run from Source
1. Clone this repository: `git clone https://github.com/SilverSix311/kodex.git`
2. Install [AutoHotkey v2](https://www.autohotkey.com/)
3. Run: `AutoHotkey.exe kodex.ahk`
4. Press `Ctrl+Alt+K` to open the hotstring manager

### Using Kodex
1. **Add a Hotstring**: Click "New Hotstring" in the manager
2. **Enter Details**: Type phrase, replacement, select trigger type
3. **Start Typing**: Your hotstrings expand automatically!
4. **Manage**: Edit, delete, or organize into bundles

## Features

- **Hex-Encoded Storage**: Safely stores hotstrings with special characters via hex encoding
- **Bundle System**: Organize hotstrings into categories (bundles) and enable/disable them
- **Trigger Types**: Choose from Space, Tab, Enter, or instant (no trigger) replacements
- **Script Execution**: Prefix hotstrings with `::scr::` to execute AutoHotkey code
- **Import/Export**: Share hotstring bundles with team members
- **Printable Reference**: Generate an HTML cheatsheet of all active hotstrings

## Recent Migration to AutoHotkey v2 ✓

**Date**: January 2026  
**Status**: Complete  
**Version**: 2.0.0

All 18 core scripts have been migrated from AutoHotkey v1 to v2. Key improvements:

- Modern v2 syntax with cleaner variable handling (no more `%varname%`)
- Function-based architecture replacing v1 label/Gosub patterns
- `GuiCreate()` objects with event callbacks for improved GUI code
- Enhanced error handling with `try/catch` for file operations
- `LoopFiles()` integration for robust file iteration
- New Freshdesk ticket time tracker feature

**Downloads**: [Latest Release](https://github.com/SilverSix311/kodex/releases/latest)

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed v2 migration notes and API reference.

## Releases & Downloads

| Version | Release Date | Status | Download |
|---------|--------------|--------|----------|
| **2.0.0** | January 29, 2026 | ✅ Current | [kodex-v2.0.0.zip](https://github.com/SilverSix311/kodex/releases/latest) |
| 1.x | Previous | Deprecated | [Archive](https://github.com/SilverSix311/kodex/releases) |

**Installation Options**:
1. **Standalone Executable**: Download `kodex.exe` from releases
2. **Full Package**: Download `kodex-v2.0.0.zip` with documentation
3. **Build from Source**: Clone repo and run `AutoHotkey.exe kodex.ahk`

See [RELEASE_GUIDE.md](RELEASE_GUIDE.md) for building and packaging instructions.

## Recent Migration to AutoHotkey v2 ✓

## Testing

Run the smoke-test script to validate your installation:

```powershell
AutoHotkey.exe smoke_test.ahk
```

This will:
- Verify directory structure
- Test hotstring creation and deletion
- Validate CSV bank files
- Check Active directory compilation
- Generate `test_results.log` with detailed results

## File Structure

```
kodex/
├── kodex.ahk                    # Main application entry point
├── KodexInstaller.ahk           # Installation utility
├── smoke_test.ahk               # Automated testing script
├── export.ahk                   # Export hotstrings to bundle
├── import.ahk                   # Import hotstrings from bundle
├── printable.ahk                # Generate HTML reference
├── replacements/                # Default bundle hotstrings
│   └── [HEX_NAME].txt          # Individual hotstring files
├── bank/                        # Default bundle trigger mappings
│   ├── enter.csv
│   ├── tab.csv
│   ├── space.csv
│   └── notrig.csv
├── Bundles/                     # Custom bundle directories
│   └── [BUNDLE_NAME]/
│       ├── replacements/
│       └── bank/
├── Active/                      # Runtime-compiled active hotstrings
│   ├── replacements/
│   └── bank/
├── includes/
│   ├── functions/              # Helper function modules
│   └── GUI/                    # GUI definitions
├── resources/                  # Static assets
├── kodex.ini                   # Configuration file
└── .github/
    └── copilot-instructions.md # AI copilot API reference
```

## Configuration

Edit `kodex.ini` to customize Kodex behavior:

```ini
[Bundles]
Default=1          ; Enable/disable the Default bundle
CustomBundle=1     ; Enable/disable custom bundles

[Triggers]
Space=1             ; Enable Space trigger
Tab=1               ; Enable Tab trigger
Enter=1             ; Enable Enter trigger
NoTrig=1            ; Enable instant replacements
```

## Development

### Adding a New Hotstring Programmatically

```autohotkey
SaveHotstring("btw", "by the way", "Space", "Default")
```

This will:
1. Create `replacements/[hex_name].txt` with the replacement text
2. Add the hotstring to the appropriate trigger bank
3. Rebuild the Active directory automatically

### Running Tests

```powershell
AutoHotkey.exe smoke_test.ahk
```

See the generated `test_results.log` for detailed test output.

### API Reference

For detailed function signatures, architectural patterns, and migration notes, see:
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Complete API reference and v2 migration guide

## Requirements

- **Windows 10/11**
- **AutoHotkey v2** (download from https://www.autohotkey.com/)

## License

See LICENSE file for details.

## Support

For issues, feature requests, or questions:
1. Check [.github/copilot-instructions.md](.github/copilot-instructions.md) for technical documentation
2. Review `test_results.log` after running smoke_test.ahk
3. Open an issue on GitHub

---

**Last Updated**: January 2026  
**Version**: 0.1
