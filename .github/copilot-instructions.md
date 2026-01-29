# Kodex AI Copilot Instructions

Kodex is a **text replacement/substitution application for Windows** written in AutoHotkey v1. It monitors keyboard input and replaces typed hotstrings with predefined replacements.

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
- `Hexify(string)` / `DeHexify(hex)` → Convert strings to/from hex for filenames
- `SaveHotstring()` → Validates input, writes file, updates CSV banks, triggers `BuildActive`
- `DeleteHotstring()` → Removes file and removes from all CSV banks
- `BuildActive()` → Compiles enabled bundles into Active/ directory (called after any hotstring change)
- `AddToBank()` / `DelFromBank()` → Manage CSV trigger mappings

### Configuration
- **kodex.ini**: INI file with sections: `[Bundles]` (enable/disable bundles), `[Triggers]` (Space/Tab/Enter/NoTrig defaults)
- **CurrentVersion.txt**: Version number (currently 0.1)
- Settings read on startup via `IniRead` commands in initialization subroutines

### GUI Structure
- GUIs use numbered windows (Gui,2: for management, etc.)
- Menu bars built dynamically in `management_GUI.ahk` (Tools, Bundles, Help menus)
- ListBox controls populated from file lists; right-click context menus for editing

## Workflow Commands

**Building/Running:**
- Script must be run with AutoHotkey interpreter (`AutoHotkey.exe kodex.ahk`)
- Initialization happens in `kodex.ahk` top-level via `Gosub` calls: ASSIGNVARS → RESOURCES → READINI → TRAYMENU → BuildActive
- KodexInstaller.ahk packages the application for distribution

**Supplementary Tools:**
- `export.ahk` / `import.ahk` → Export selected hotstrings or import from zip bundles
- `printable.ahk` → Generate printable reference list of hotstrings

## Key Development Constraints

1. **No Delay Keystrokes**: `SetKeyDelay,-1` is set for performance (replacements fire immediately)
2. **Case-Sensitive Strings**: `StringCaseSense On` → hotstrings are case-sensitive by default
3. **AutoTrim Off**: Leading/trailing spaces in replacements are preserved
4. **Special Keys State**: Code manages Shift key state to prevent it from "sticking" after rapid replacement firing
5. **AutoCorrect / AutoClose**: Currently disabled (commented in main loop) but infrastructure exists in `includes/functions/`

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

- This is **AutoHotkey v1 syntax** (not v2)—variable references use `%varname%`, no `var1.var2` dot notation
- The `Input` command is the core of hotstring detection; understand its `EndKey` behavior
- Hex encoding is non-negotiable for filenames; any new hotstring storage must use `Hexify()`
- `BuildActive` is the critical rebuild step—any data structure change requires rebuilding
- GUIs are stateful; destroying and recreating is the pattern (e.g., `Gui,2: Destroy`)
- Test changes with actual keyboard input; the app relies on Windows Input API timing

## Migration to AutoHotkey v2 (planned)

- Status: migration to AHK v2 approved; core research completed and migration TODOs tracked in project TODOs.
- Why migrate: modern syntax, improved object model, and a chance to refactor `Gosub` labels into functions for clearer control flow.
- High-impact changes to expect:
	- Replace `%var%` references with direct variables (`var`) and update all string concatenations.
	- Convert label-based `Gosub`/`Return` flow into proper functions (e.g., `BuildActive()` instead of `BuildActive:`).
	- Update `Input` uses to v2 return-style (`result := Input(...)`).
	- Replace `IniRead`/`IniWrite` calls with function form (`IniRead(file, section, key, default)`).
	- Rework all `Gui, N:` usages to `GuiCreate()` objects and callbacks.

- Recommended migration order (minimal risk):
	1. Convert standalone helper functions in `includes/functions/` (`hexify.ahk`, `savehotstring.ahk`, `buildactive.ahk`).
	2. Migrate `kodex.ahk` main initialization and input loop.
	3. Migrate GUI files in `includes/GUI/` (management, newkey, preferences, help, about).
	4. Migrate supplemental scripts (`export.ahk`, `import.ahk`, `printable.ahk`, `KodexInstaller.ahk`).
	5. Run full end-to-end tests with real keyboard input and bundle switching.

- Quick migration checklist examples:
	- `IniRead, val, file, section, key`  →  `val := IniRead(file, section, key)`
	- `Gosub, SomeLabel` / `SomeLabel:`  →  `SomeFunction()` / `SomeFunction() { ... }`
	- `Input, out, T3000`  →  `out := Input(, 3000)` with `try/catch` for interruptions

- Tests to perform after each phase:
	- Verify `Active\bank\*.csv` contains expected entries after `SaveHotstring()`.
	- Confirm hotstrings trigger correctly for `Space`, `Tab`, `Enter`, and `NoTrig` modes.
	- Validate `::scr::` script execution paths.

If you'd like, I can start converting `includes/functions/hexify.ahk` → v2 now and show a minimal working example.
