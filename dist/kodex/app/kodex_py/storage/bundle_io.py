"""Bundle import / export — reads and writes ``.kodex`` bundle files.

The ``.kodex`` format (from the AHK codebase)::

    Line 1: BundleName
    Line 2: Hotstring1_plaintext
    Line 3: Replacement1  (newlines escaped as %bundlebreak)
    Line 4: Hotstring2_plaintext
    Line 5: Replacement2
    ...
    Line N:   §Triggers§       ← section-sign marker (U+00A7)
    Line N+1: enter bank content  (hex,,hex,,…)
    Line N+2: tab bank content
    Line N+3: space bank content
    Line N+4: notrig bank content
"""

from __future__ import annotations

import logging
from pathlib import Path

from kodex_py.storage.database import Database
from kodex_py.storage.models import Hotstring, TriggerType
from kodex_py.utils.hex_codec import dehexify, hexify

log = logging.getLogger(__name__)

_TRIGGER_MARKER = "§Triggers§"
_BUNDLEBREAK = "%bundlebreak"


# ── Export ──────────────────────────────────────────────────────────

def export_bundle(db: Database, bundle_name: str, output_path: str | Path) -> int:
    """Export a bundle to a ``.kodex`` file.  Returns the number of hotstrings exported."""
    bundle = db.get_bundle_by_name(bundle_name)
    if bundle is None:
        raise ValueError(f"Bundle '{bundle_name}' not found")

    hotstrings = db.get_hotstrings(bundle_id=bundle.id)
    lines: list[str] = [bundle_name]

    # Build per-trigger bank content
    banks: dict[str, list[str]] = {"enter": [], "tab": [], "space": [], "notrig": []}

    for hs in hotstrings:
        lines.append(hs.name)
        replacement = hs.replacement
        if hs.is_script:
            replacement = "::scr::" + replacement
        replacement = replacement.replace("\r\n", _BUNDLEBREAK).replace("\n", _BUNDLEBREAK)
        lines.append(replacement)

        hex_name = hexify(hs.name)
        for t in hs.triggers:
            bank_key = "notrig" if t == TriggerType.INSTANT else t.value
            banks[bank_key].append(hex_name)

    # Trigger section
    lines.append(_TRIGGER_MARKER)
    for key in ("enter", "tab", "space", "notrig"):
        lines.append(",,".join(banks[key]) + ",," if banks[key] else "")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    return len(hotstrings)


# ── Import ──────────────────────────────────────────────────────────

def import_bundle(
    db: Database,
    file_path: str | Path,
    *,
    bundle_name: str | None = None,
    use_file_triggers: bool = True,
) -> int:
    """Import a ``.kodex`` bundle file.  Returns the number of hotstrings imported."""
    content = Path(file_path).read_text(encoding="utf-8")
    raw_lines = content.split("\n")

    if not raw_lines:
        raise ValueError("Empty .kodex file")

    file_bundle_name = raw_lines[0].strip()
    name = bundle_name or file_bundle_name
    bundle = db.create_bundle(name, enabled=True)

    # Parse hotstring pairs until trigger marker
    hotstrings: list[tuple[str, str]] = []
    trigger_section_idx: int | None = None

    i = 1
    while i < len(raw_lines):
        line = raw_lines[i]
        if line.strip() == _TRIGGER_MARKER:
            trigger_section_idx = i
            break
        # Hotstring name
        hs_name = line.strip()
        i += 1
        if i >= len(raw_lines):
            break
        # Replacement text (with %bundlebreak → \r\n)
        replacement = raw_lines[i].replace(_BUNDLEBREAK, "\r\n")
        hotstrings.append((hs_name, replacement))
        i += 1

    # Parse trigger banks from the file
    file_triggers: dict[str, set[TriggerType]] = {}
    if trigger_section_idx is not None and use_file_triggers:
        bank_lines = raw_lines[trigger_section_idx + 1 : trigger_section_idx + 5]
        trigger_order = [TriggerType.ENTER, TriggerType.TAB, TriggerType.SPACE, TriggerType.INSTANT]
        for idx, ttype in enumerate(trigger_order):
            if idx < len(bank_lines):
                hex_names = [h.strip() for h in bank_lines[idx].split(",,") if h.strip()]
                for hex_name in hex_names:
                    try:
                        plain = dehexify(hex_name)
                    except (ValueError, IndexError):
                        continue
                    file_triggers.setdefault(plain, set()).add(ttype)

    count = 0
    for hs_name, replacement in hotstrings:
        if not hs_name:
            continue
        is_script = replacement.startswith("::scr::")
        if is_script:
            replacement = replacement[7:]

        triggers = file_triggers.get(hs_name, {TriggerType.SPACE})

        hs = Hotstring(
            name=hs_name,
            replacement=replacement,
            is_script=is_script,
            bundle_id=bundle.id,
            triggers=triggers,
        )
        try:
            db.save_hotstring(hs)
            count += 1
        except Exception as e:
            log.warning("Failed to import '%s': %s", hs_name, e)

    return count
