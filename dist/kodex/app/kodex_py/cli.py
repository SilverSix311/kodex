"""Kodex CLI — manage hotstrings, bundles, and run the engine from the terminal.

Usage examples::

    kodex run                         # Start the engine + tray
    kodex list                        # List all hotstrings
    kodex add btw "by the way" -b Default -t space enter
    kodex remove btw -b Default
    kodex bundles                     # List bundles
    kodex bundle-create WorkStuff
    kodex bundle-toggle WorkStuff
    kodex migrate /path/to/legacy-kodex
    kodex import-bundle file.kodex
    kodex export-bundle Default out.kodex
    kodex stats
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from kodex_py import __version__
from kodex_py.config import get_db_path
from kodex_py.storage.database import Database
from kodex_py.storage.models import Hotstring, TriggerType

_TRIGGER_MAP = {
    "enter": TriggerType.ENTER,
    "tab": TriggerType.TAB,
    "space": TriggerType.SPACE,
    "instant": TriggerType.INSTANT,
}


def _open_db(db_path: str | None = None) -> Database:
    path = Path(db_path) if db_path else get_db_path()
    db = Database(path)
    db.open()
    return db


@click.group()
@click.version_option(__version__)
@click.option("--db", default=None, help="Path to kodex.db (default: ~/.kodex/kodex.db)")
@click.pass_context
def cli(ctx, db):
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db


# ── run ─────────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def run(ctx):
    """Start the Kodex engine with system tray."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from kodex_py.app import KodexApp
    app = KodexApp(db_path=ctx.obj["db_path"])
    try:
        app.start()
    except KeyboardInterrupt:
        app.stop()


# ── list ────────────────────────────────────────────────────────────

@cli.command("list")
@click.option("-b", "--bundle", default=None, help="Filter by bundle name")
@click.option("--enabled/--all", default=False, help="Only enabled bundles")
@click.pass_context
def list_hotstrings(ctx, bundle, enabled):
    """List all hotstrings."""
    db = _open_db(ctx.obj["db_path"])
    try:
        bundle_id = None
        if bundle:
            b = db.get_bundle_by_name(bundle)
            if b is None:
                click.echo(f"Bundle '{bundle}' not found", err=True)
                sys.exit(1)
            bundle_id = b.id

        items = db.get_hotstrings(bundle_id=bundle_id, enabled_only=enabled)
        if not items:
            click.echo("No hotstrings found.")
            return

        click.echo(f"{'Name':<25} {'Bundle':<15} {'Triggers':<20} {'Script':>6}")
        click.echo("─" * 70)
        for hs in items:
            trigs = ", ".join(sorted(t.value for t in hs.triggers))
            click.echo(f"{hs.name:<25} {hs.bundle_name:<15} {trigs:<20} {'yes' if hs.is_script else '':>6}")
        click.echo(f"\nTotal: {len(items)}")
    finally:
        db.close()


# ── add ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("name")
@click.argument("replacement")
@click.option("-b", "--bundle", default="Default", help="Bundle name")
@click.option("-t", "--trigger", multiple=True, type=click.Choice(list(_TRIGGER_MAP)), default=["space"])
@click.option("--script", is_flag=True, help="Script mode")
@click.pass_context
def add(ctx, name, replacement, bundle, trigger, script):
    """Add a new hotstring."""
    db = _open_db(ctx.obj["db_path"])
    try:
        b = db.get_bundle_by_name(bundle)
        if b is None:
            b = db.create_bundle(bundle)

        triggers = {_TRIGGER_MAP[t] for t in trigger}
        hs = Hotstring(
            name=name,
            replacement=replacement.replace("\\n", "\n"),
            is_script=script,
            bundle_id=b.id,
            triggers=triggers,
        )
        db.save_hotstring(hs)
        click.echo(f"✓ Added '{name}' → {len(replacement)} chars [{', '.join(t.value for t in triggers)}]")
    finally:
        db.close()


# ── remove ──────────────────────────────────────────────────────────

@cli.command()
@click.argument("name")
@click.option("-b", "--bundle", default="Default", help="Bundle name")
@click.pass_context
def remove(ctx, name, bundle):
    """Remove a hotstring."""
    db = _open_db(ctx.obj["db_path"])
    try:
        b = db.get_bundle_by_name(bundle)
        if b is None:
            click.echo(f"Bundle '{bundle}' not found", err=True)
            sys.exit(1)
        hs = db.get_hotstring_by_name(name, b.id)
        if hs is None:
            click.echo(f"Hotstring '{name}' not found in bundle '{bundle}'", err=True)
            sys.exit(1)
        db.delete_hotstring(hs.id)
        click.echo(f"✓ Removed '{name}' from '{bundle}'")
    finally:
        db.close()


# ── bundles ─────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def bundles(ctx):
    """List all bundles."""
    db = _open_db(ctx.obj["db_path"])
    try:
        for b in db.get_bundles():
            status = "✓" if b.enabled else "✗"
            count = len(db.get_hotstrings(bundle_id=b.id))
            click.echo(f"  {status} {b.name:<20} ({count} hotstrings)")
    finally:
        db.close()


@cli.command("bundle-create")
@click.argument("name")
@click.pass_context
def bundle_create(ctx, name):
    """Create a new bundle."""
    db = _open_db(ctx.obj["db_path"])
    try:
        db.create_bundle(name, enabled=True)
        click.echo(f"✓ Created bundle '{name}'")
    finally:
        db.close()


@cli.command("bundle-toggle")
@click.argument("name")
@click.pass_context
def bundle_toggle(ctx, name):
    """Toggle a bundle enabled/disabled."""
    db = _open_db(ctx.obj["db_path"])
    try:
        b = db.get_bundle_by_name(name)
        if b is None:
            click.echo(f"Bundle '{name}' not found", err=True)
            sys.exit(1)
        new_state = not b.enabled
        db.set_bundle_enabled(b.id, new_state)
        click.echo(f"✓ Bundle '{name}' is now {'enabled' if new_state else 'disabled'}")
    finally:
        db.close()


@cli.command("bundle-delete")
@click.argument("name")
@click.pass_context
def bundle_delete(ctx, name):
    """Delete a bundle and all its hotstrings."""
    if name == "Default":
        click.echo("Cannot delete the Default bundle", err=True)
        sys.exit(1)
    db = _open_db(ctx.obj["db_path"])
    try:
        b = db.get_bundle_by_name(name)
        if b is None:
            click.echo(f"Bundle '{name}' not found", err=True)
            sys.exit(1)
        db.delete_bundle(b.id)
        click.echo(f"✓ Deleted bundle '{name}'")
    finally:
        db.close()


# ── migrate ─────────────────────────────────────────────────────────

@cli.command()
@click.argument("legacy_dir", type=click.Path(exists=True))
@click.pass_context
def migrate(ctx, legacy_dir):
    """Migrate a legacy Kodex AHK installation into the database."""
    from kodex_py.storage.migration import migrate_legacy
    db_path = ctx.obj["db_path"] or get_db_path()
    result = migrate_legacy(legacy_dir, db_path)
    click.echo(f"✓ Migrated {result.bundles} bundles, {result.hotstrings} hotstrings, "
               f"{result.autocorrect} autocorrect entries")
    if result.errors:
        click.echo(f"  ⚠ {len(result.errors)} errors:")
        for e in result.errors[:10]:
            click.echo(f"    • {e}")


# ── import / export ─────────────────────────────────────────────────

@cli.command("import-bundle")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("-n", "--name", default=None, help="Override bundle name")
@click.pass_context
def import_bundle(ctx, file_path, name):
    """Import a .kodex bundle file."""
    from kodex_py.storage.bundle_io import import_bundle as do_import
    db = _open_db(ctx.obj["db_path"])
    try:
        count = do_import(db, file_path, bundle_name=name)
        click.echo(f"✓ Imported {count} hotstrings")
    finally:
        db.close()


@cli.command("export-bundle")
@click.argument("bundle_name")
@click.argument("output_path")
@click.pass_context
def export_bundle(ctx, bundle_name, output_path):
    """Export a bundle to a .kodex file."""
    from kodex_py.storage.bundle_io import export_bundle as do_export
    db = _open_db(ctx.obj["db_path"])
    try:
        count = do_export(db, bundle_name, output_path)
        click.echo(f"✓ Exported {count} hotstrings to {output_path}")
    finally:
        db.close()


# ── stats ───────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def stats(ctx):
    """Show expansion statistics."""
    db = _open_db(ctx.obj["db_path"])
    try:
        expanded = db.get_stat("expanded")
        chars = db.get_stat("chars_saved")
        hours = chars / 24_000 if chars else 0
        total_hs = len(db.get_hotstrings())
        total_bundles = len(db.get_bundles())

        click.echo(f"  Hotstrings:       {total_hs}")
        click.echo(f"  Bundles:          {total_bundles}")
        click.echo(f"  Expansions:       {expanded:,}")
        click.echo(f"  Characters saved: {chars:,}")
        click.echo(f"  Hours saved:      {hours:.1f}")
    finally:
        db.close()


# ── time-log ────────────────────────────────────────────────────────

@cli.command("time-log")
@click.option("-d", "--date", default=None, help="Date in YYYY-MM-DD format (default: today)")
@click.pass_context
def time_log(ctx, date):
    """Show today's ticket time log."""
    from datetime import datetime as dt
    from kodex_py.plugins.ticket_tracker import TicketTracker

    tracker = TicketTracker()
    if date:
        target = dt.strptime(date, "%Y-%m-%d")
    else:
        target = dt.now()

    entries = tracker.get_time_log(target)
    if not entries:
        click.echo("No time entries for this date.")
        return

    click.echo(f"{'Ticket':<12} {'Status':<10} {'Timestamp':<22} {'Hours':>8}")
    click.echo("─" * 55)
    for e in entries:
        hours = f"{e['duration_hours']:.2f}" if e.get("duration_hours") else ""
        click.echo(f"{e['ticket_number']:<12} {e['status']:<10} {e['timestamp']:<22} {hours:>8}")


# ── cheatsheet ──────────────────────────────────────────────────────

@cli.command("cheatsheet")
@click.argument("output_path", default="kodex-cheatsheet.html")
@click.pass_context
def cheatsheet(ctx, output_path):
    """Generate a printable HTML cheatsheet of all hotstrings."""
    from kodex_py.gui.cheatsheet import generate_cheatsheet
    db = _open_db(ctx.obj["db_path"])
    try:
        generate_cheatsheet(db, output_path)
        click.echo(f"✓ Cheatsheet saved to {output_path}")
    finally:
        db.close()


if __name__ == "__main__":
    cli()
