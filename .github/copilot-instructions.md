# Kodex AI Copilot Instructions

Kodex is a **text replacement/substitution application for Windows** written in **AutoHotkey v2**. It monitors keyboard input and replaces typed hotstrings with predefined replacements.

## Architecture Overview

**Core Data Flow:**
1. **Main Loop** ([kodex.ahk](../kodex.ahk#L30-L120)): Continuously waits for character input using AutoHotkey's `Input` command
2. **Hotstring Matching**: Typed characters are accumulated and checked against active hotstring list
3. **Hex Encoding**: Hotstrings are stored/retrieved as hex-encoded filenames (via `Hexify()` function) to avoid filesystem restrictions with special characters
4. **Bundle System**: Hotstrings are organized into "bundles" (categories). The "Default" bundle + enabled bundles are compiled into the "Active" directory at runtime
5. **Trigger Types**: Replacements can be triggered by Enter, Tab, Space, or explicitly (no trigger required)

**Directory Structure:**
- `replacements/` + `bank/` → Default bundle hotstrings and trigger mappings
- `Bundles/[name]/` → Custom bundle directories (same structure as Default)
- `Active/` → Runtime-generated directory with merged active hotstrings from all enabled bundles
- `includes/functions/` → Reusable subroutines (called via `Gosub`)
- `includes/GUI/` → GUI window definitions
- `resources/` → autocorrect.txt, style.css

## Critical Patterns & Conventions

### File Storage & Naming
- Hotstring files: `replacements/[HEX_ENCODED_NAME].txt` containing the replacement text
- Trigger mapping: Four CSV banks (`bank/{enter,tab,space,notrig}.csv`) list hotstrings that trigger on each key
- Hex encoding prevents filename issues (e.g., hotstring "foo:bar" → filename with hex equivalent)

### Key Functions (in `includes/functions/`)
- `Hexify(string)` / `DeHexify(hex)` → Convert strings to/from hex for filenames (v2 functions with Format and StrLen)
- `SaveHotstring(hotstring, replacement, trigger, bundleName)` → Validates input, writes file, updates CSV banks, triggers `BuildActive()`
- `DeleteHotstring(hotstring, bundleName)` → Removes file and removes from all CSV banks
- `BuildActive()` → Compiles enabled bundles into Active/ directory via LoopFiles iteration (called after any hotstring change)
- `AddToBank(hotstring, trigger, bundleName)` / `DelFromBank(hotstring, trigger, bundleName)` → Manage CSV trigger mappings

### Configuration
- **kodex.ini**: INI file with sections: `[Bundles]` (enable/disable bundles), `[Triggers]` (Space/Tab/Enter/NoTrig defaults)
- **CurrentVersion.txt**: Version number (currently 0.1)
- Settings read on startup via `IniRead` commands in initialization subroutines

### GUI Structure
- GUIs created via `GuiCreate()` objects (v2 pattern)
- Callback handlers use `OnEvent()` method (e.g., `MyGui.Show("auto", "Title")` with `MyGui.Button := ButtonHandler`)
- Main management GUI in `management_GUI.ahk`: ManageGUI() function with tab control and ListBox
- All supplemental GUIs (newkey, preferences, help, about, traymenu, textprompt) follow same v2 GuiCreate pattern

## Workflow Commands

**Building/Running:**
- Script must be run with AutoHotkey v2 interpreter (`AutoHotkey.exe kodex.ahk`)
- Initialization happens in `kodex.ahk` via function calls: AssignVars() → ReadINI() → TrayMenu_Init() → BuildActive()
- Main loop uses `Input()` function (v2 return-value style) with character-by-character hotstring matching
- KodexInstaller.ahk packages the application for distribution

**Supplementary Tools:**
- `export.ahk` / `import.ahk` → ExportUtility() / ImportUtility() functions with GUI wrappers
- `printable.ahk` → PrintableList() generates HTML reference cheatsheet
- `smoke_test.ahk` → Validates core functionality with 8 test suites

## Key Development Constraints

1. **No Delay Keystrokes**: `SetKeyDelay(-1)` is set for performance (replacements fire immediately)
2. **Case-Sensitive Strings**: `StringCaseSense("On")` → hotstrings are case-sensitive by default
3. **AutoTrim Off**: `AutoTrim(false)` → Leading/trailing spaces in replacements are preserved
4. **Special Keys State**: Code manages Shift key state to prevent it from "sticking" after rapid replacement firing
5. **AutoCorrect / AutoClose**: Currently disabled but infrastructure exists in `includes/functions/`

## Integration Points

- **Startup**: Tray menu built, INI settings loaded, Active directory compiled
- **Hotstring Addition**: Must update CSV banks and rebuild Active directory
- **Bundle Management**: Bundles are directories with `/replacements` and `/bank` subdirectories
- **Script Execution**: Replacements prefixed with `::scr::` are executed as AHK code rather than typed text

## Common Tasks

| Task | Key Files |
|------|-----------|
| Add/edit a hotstring | `management_GUI.ahk` → calls `SaveHotstring()` |
| Create new bundle | Menu handler → creates `Bundles/[name]/replacements/` and `/bank/` directories |
| Debug hotstring matching | Check `Active/bank/*.csv` and ensure `BuildActive` was called |
| Export/import bundles | `export.ahk` / `import.ahk` |
| Test script replacements | Add hotstring with `::scr::` prefix containing AHK code |

## Notes for AI Agents

- This is **AutoHotkey v2 syntax**—variable references use direct variables (`var`), not `%varname%` dereferencing
- The `Input()` function (v2 return-value style) is the core of hotstring detection; understand its EndKey behavior
- Hex encoding is non-negotiable for filenames; any new hotstring storage must use `Hexify()`
- `BuildActive()` is the critical rebuild step—any data structure change requires rebuilding
- GUIs use `GuiCreate()` objects with `OnEvent()` callbacks; destroying and recreating is the pattern
- Test changes with actual keyboard input; the app relies on Windows Input API timing
- File I/O operations (`IniRead`, `FileRead`) should be wrapped in `try/catch` for error handling

## AutoHotkey v2 Migration - COMPLETE ✓

**Status**: Full v2 migration completed (January 2026). All 18 core files converted and deployed.

**Migration Summary:**
- **Helper Functions** (7 files): hexify.ahk, savehotstring.ahk, buildactive.ahk, addtobank.ahk, delfrombank.ahk, getfilelist.ahk, renamehotstring.ahk, getvalfromini.ahk
- **Main Script**: kodex.ahk (563 lines) - Input loop, function-based architecture, global variable management
- **GUI Files** (8 files): management_GUI.ahk, newkey_GUI.ahk, preferences_GUI.ahk, help_GUI.ahk, about_GUI.ahk, traymenu_GUI.ahk, textprompt_GUI.ahk, disablechecks.ahk
- **Utility Scripts** (3 files): export.ahk, import.ahk, printable.ahk
- **Installer**: KodexInstaller.ahk
- **Testing**: smoke_test.ahk (8 test suites)

**Key v2 Conversions Applied:**
- Variable syntax: `%var%` → `var`
- Command syntax: `Gui,N:` → `GuiCreate()` objects; `SetKeyDelay,-1` → `SetKeyDelay(-1)`
- Event handlers: g-labels → `OnEvent()` callbacks
- File I/O: `FileRead` → `FileRead()` function; `IfExist` → `FileExist()`
- Control flow: `Gosub` → function calls; `Input` command → `Input()` return-value style
- Error handling: added `try/catch` for `IniRead`/`FileRead` operations
- Loops: `Loop Files` → `LoopFiles()` with object properties (`.Name`, `.FullPath`)
- String operations: `StrReplace`, `InStr` preferred over v1's "in" operator

**Testing & Validation:**
- Created `smoke_test.ahk` with 8 test suites (directory structure, Active directory, Hexify/DeHexify, hotstring lifecycle, CSV banks, INI file)
- Covers core workflows: create hotstring → trigger → delete → rebuild
- Validates CSV trigger mappings and Active directory compilation
- Test log output: `test_results.log`

**Migration Checklist Examples for Future Enhancements:**
- `IniRead, val, file, section, key`  →  `val := IniRead(file, section, key)`
- `Gosub, SomeLabel` / `SomeLabel:`  →  `SomeFunction()` / `SomeFunction() { ... }`
- `Input, out, T3000`  →  `out := Input(, 3000)` with `try/catch` for interruptions
- `Loop Files, pattern`  →  `for file in LoopFiles(pattern)` with `file.Name`, `file.FullPath`
- `GuiControl,,ControlID,NewValue`  →  `MyGui[ControlID].Value := NewValue`

**Known Differences from v1:**
- `IniRead()` throws exceptions instead of setting ErrorLevel
- `FileExist()` / `DirExist()` return true/false directly
- `LoopFiles()` returns file objects, not string concatenation
- GUI controls accessed via `MyGui[name].Value` property (simpler than GuiControlGet)
- Shift key state management logic preserved from v1 (no changes needed)
