# Quick Start: Build & Release Kodex

**Time to Complete**: ~10 minutes

## 1️⃣ Build the Executable (2 min)

```powershell
cd d:\Code\kodex
.\build.ps1
```

**Output**:
- `dist/kodex.exe` - Standalone executable
- `dist/kodex-v2.0.0.zip` - Release package with docs

## 2️⃣ Test the Build (3 min)

```powershell
# Run the executable
.\dist\kodex.exe

# Run smoke tests
AutoHotkey.exe smoke_test.ahk
```

**Verify**:
- GUI opens without errors
- Hotkeys respond correctly
- No console messages

## 3️⃣ Create Release Tag (1 min)

```bash
git tag -a v2.0.0 -m "Release version 2.0.0 - AutoHotkey v2 Migration"
git push origin v2.0.0
```

## 4️⃣ Create GitHub Release (3 min)

1. Go to: https://github.com/SilverSix311/kodex/releases/new
2. **Tag**: Select `v2.0.0`
3. **Title**: `Kodex v2.0.0 - AutoHotkey v2 Migration`
4. **Description**: Use template from RELEASE_GUIDE.md
5. **Attach Files**:
   - Drag `dist/kodex.exe`
   - Drag `dist/kodex-v2.0.0.zip`
6. Click **Publish release**

## 5️⃣ Announce Release (Optional)

- Post on GitHub Discussions
- Update documentation links
- Share with users

---

## ✅ Done!

Your release is now live. Users can download from:
- https://github.com/SilverSix311/kodex/releases

---

## 🔍 Troubleshooting

### Build fails?
- Ensure AutoHotkey v2 is installed
- Run: `.\build.ps1` with error details
- See RELEASE_GUIDE.md for solutions

### Test fails?
- Check kodex.ahk syntax
- Run smoke_test.ahk for diagnostic
- Review error messages

### Upload fails?
- Verify git credentials: `git config --list`
- Check tag exists: `git tag`
- Ensure internet connection

---

## 📚 More Info

See **RELEASE_GUIDE.md** for:
- Manual build instructions
- Detailed release process
- Automation with GitHub Actions
- Distribution methods
- Security considerations
