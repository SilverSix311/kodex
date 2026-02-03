"""Printable cheatsheet generator — creates an HTML reference of all hotstrings.

Mirrors the AHK printable.ahk / printablelist.ahk.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kodex_py.storage.database import Database

log = logging.getLogger(__name__)


def generate_cheatsheet(db: "Database", output_path: str | Path) -> None:
    """Generate an HTML cheatsheet of all hotstrings grouped by bundle."""
    bundles = db.get_bundles()
    lines = [
        "<!DOCTYPE html>",
        "<html><head>",
        "<meta charset='utf-8'>",
        "<title>Kodex Cheatsheet</title>",
        "<style>",
        "  body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }",
        "  h1 { color: #228B22; border-bottom: 2px solid #228B22; padding-bottom: 8px; }",
        "  h2 { color: #333; margin-top: 24px; }",
        "  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }",
        "  th { background: #228B22; color: white; text-align: left; padding: 8px; }",
        "  td { padding: 6px 8px; border-bottom: 1px solid #ddd; }",
        "  tr:hover { background: #f5f5f5; }",
        "  .triggers { color: #666; font-size: 0.9em; }",
        "  .script { color: #c00; font-weight: bold; }",
        "  .replacement { white-space: pre-wrap; max-width: 400px; word-break: break-word; font-family: Consolas, monospace; font-size: 0.9em; }",
        "  @media print { body { font-size: 10pt; } }",
        "</style>",
        "</head><body>",
        "<h1>Kodex Cheatsheet</h1>",
    ]

    total = 0
    for bundle in bundles:
        hotstrings = db.get_hotstrings(bundle_id=bundle.id)
        if not hotstrings:
            continue
        total += len(hotstrings)
        status = "" if bundle.enabled else " (disabled)"
        lines.append(f"<h2>{html.escape(bundle.name)}{status}</h2>")
        lines.append("<table>")
        lines.append("<tr><th>Hotstring</th><th>Replacement</th><th>Triggers</th><th>Type</th></tr>")

        for hs in sorted(hotstrings, key=lambda h: h.name.lower()):
            triggers = ", ".join(sorted(t.value for t in hs.triggers))
            mode = '<span class="script">Script</span>' if hs.is_script else "Text"
            # Truncate long replacements for display
            repl = hs.replacement
            if len(repl) > 200:
                repl = repl[:200] + "…"
            lines.append(
                f"<tr>"
                f"<td><code>{html.escape(hs.name)}</code></td>"
                f'<td class="replacement">{html.escape(repl)}</td>'
                f'<td class="triggers">{html.escape(triggers)}</td>'
                f"<td>{mode}</td>"
                f"</tr>"
            )
        lines.append("</table>")

    lines.append(f"<p><em>Total: {total} hotstrings across {len(bundles)} bundles</em></p>")
    lines.append("</body></html>")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    log.info("Cheatsheet generated: %s (%d hotstrings)", output_path, total)
