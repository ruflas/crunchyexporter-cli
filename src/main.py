#!/usr/bin/env python3
import sys
import os
import yaml
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crunchyroll.auth import CRAuth, CRAuthError, DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET
from src.crunchyroll.history import CRHistory
from src.storage.history_store import HistoryStore
from src.exporters.anilist import AniListExporter
from src.exporters.mal import MALExporter, get_auth_url as mal_auth_url, exchange_code as mal_exchange
from src.exporters.mal_xml import MALXMLExporter

console = Console()


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@click.group()
@click.option("--config", "-c", default="config.yaml", show_default=True, help="Path to config file.")
@click.pass_context
def cli(ctx, config):
    ctx.ensure_object(dict)
    if Path(config).exists():
        ctx.obj["config"] = load_config(config)
    else:
        ctx.obj["config"] = {}
    ctx.obj["config_path"] = config


@cli.command()
@click.option("--etp-rt", default=None, help="Value of the etp_rt cookie from your browser session.")
@click.option("--replace", is_flag=True, default=False, help="Replace existing history instead of merging.")
@click.pass_context
def fetch(ctx, etp_rt, replace):
    """Fetch watch history from Crunchyroll and save locally.

    Requires the etp_rt cookie from your browser:
      1. Log into crunchyroll.com
      2. DevTools → Application → Cookies → https://www.crunchyroll.com
      3. Copy the value of 'etp_rt' and pass it via --etp-rt or config.yaml
    """
    cfg = ctx.obj["config"]
    store_path = cfg.get("storage", {}).get("path", "data/history.json")

    cr_cfg = cfg.get("crunchyroll", {})
    etp_rt = etp_rt or cr_cfg.get("etp_rt") or ""
    if not etp_rt:
        etp_rt = click.prompt("etp_rt cookie value", hide_input=True)

    auth = CRAuth(
        client_id=cr_cfg.get("client_id") or DEFAULT_CLIENT_ID,
        client_secret=cr_cfg.get("client_secret") or DEFAULT_CLIENT_SECRET,
    )

    with console.status("[bold green]Logging in to Crunchyroll..."):
        try:
            token = auth.login_with_etp_rt(etp_rt)
        except CRAuthError as e:
            console.print(f"[red]Authentication failed:[/red] {e}")
            raise SystemExit(1)

    console.print(f"[green]Logged in.[/green] Account ID: {token.account_id}")

    with console.status("[bold green]Fetching watch history..."):
        history = CRHistory(token)
        episodes = history.fetch_all(locale=cfg.get("locale", "en-US"))

    store = HistoryStore(Path(store_path))
    if replace:
        store.replace(episodes)
        console.print(f"[green]Saved {len(episodes)} episodes[/green] to {store_path} (replaced).")
    else:
        added = store.update(episodes)
        console.print(
            f"[green]Sync complete.[/green] {added} new episodes added. "
            f"Total: {len(store)} episodes across {len(store.series_summaries())} series."
        )


@cli.command()
@click.pass_context
def status(ctx):
    """Show a summary of the locally stored watch history."""
    cfg = ctx.obj["config"]
    store_path = cfg.get("storage", {}).get("path", "data/history.json")
    store = HistoryStore(Path(store_path))

    if len(store) == 0:
        console.print("[yellow]No history found. Run [bold]fetch[/bold] first.[/yellow]")
        return

    table = Table(title="Watch History Summary", show_lines=True)
    table.add_column("Series", style="cyan", no_wrap=False)
    table.add_column("Episodes watched", justify="right")
    table.add_column("Max episode", justify="right")

    for s in sorted(store.series_summaries(), key=lambda x: x.series_title):
        table.add_row(s.series_title, str(s.total_watched), str(s.max_episode))

    console.print(table)
    console.print(f"\nLast sync: {store.last_sync or 'never'}")


@cli.command()
@click.option("--target", "-t",
              type=click.Choice(["anilist", "mal", "xml", "all"]),
              default="all", show_default=True,
              help="Export destination.")
@click.pass_context
def export(ctx, target):
    """Export watch history to anime tracking sites."""
    cfg = ctx.obj["config"]
    store_path = cfg.get("storage", {}).get("path", "data/history.json")
    store = HistoryStore(Path(store_path))

    if len(store) == 0:
        console.print("[yellow]No history to export. Run [bold]fetch[/bold] first.[/yellow]")
        return

    summaries = store.series_summaries()
    console.print(f"Exporting {len(summaries)} series...")

    if target in ("xml", "all"):
        _export_xml(cfg, summaries)

    if target in ("anilist", "all"):
        _export_anilist(cfg, summaries)

    if target in ("mal", "all"):
        _export_mal(cfg, summaries)


def _export_xml(cfg: dict, summaries):
    xml_path = cfg.get("exporters", {}).get("mal_xml", {}).get("path", "data/animelist.xml")
    with console.status("[bold]Generating MAL XML..."):
        result = MALXMLExporter(xml_path).export(summaries)
    console.print(f"[green]XML exported:[/green] {xml_path} ({len(result.updated)} series)")


def _export_anilist(cfg: dict, summaries):
    al_cfg = cfg.get("exporters", {}).get("anilist", {})
    token = al_cfg.get("access_token")
    if not token:
        client_id = al_cfg.get("client_id", "")
        url = AniListExporter.get_auth_url(client_id)
        console.print(f"\n[yellow]AniList:[/yellow] No access token found.")
        console.print(f"1. Open this URL to get your token:\n   [link]{url}[/link]")
        console.print("2. After authorizing, copy the [bold]access_token[/bold] from the redirect URL.")
        console.print("3. Add it to config.yaml under [bold]exporters.anilist.access_token[/bold].")
        return

    with console.status("[bold]Exporting to AniList..."):
        result = AniListExporter(token).export(summaries)
    _print_result("AniList", result)


def _export_mal(cfg: dict, summaries):
    mal_cfg = cfg.get("exporters", {}).get("mal", {})
    token = mal_cfg.get("access_token")
    if not token:
        client_id = mal_cfg.get("client_id", "")
        if not client_id:
            console.print("[yellow]MAL:[/yellow] Set [bold]exporters.mal.client_id[/bold] in config.yaml first.")
            return
        url, verifier = mal_auth_url(client_id)
        console.print(f"\n[yellow]MAL OAuth:[/yellow] Open this URL to authorize:\n  [link]{url}[/link]")
        code = click.prompt("Paste the authorization code from the redirect URL")
        with console.status("Exchanging code for token..."):
            token = mal_exchange(client_id, code, verifier)
        console.print(f"[green]Token obtained.[/green] Add to config: exporters.mal.access_token: {token[:20]}...")

    with console.status("[bold]Exporting to MyAnimeList..."):
        result = MALExporter(token).export(summaries)
    _print_result("MyAnimeList", result)


def _print_result(name: str, result):
    console.print(f"\n[bold]{name}[/bold] — {len(result.updated)} updated, "
                  f"{len(result.skipped)} skipped, {len(result.failed)} failed")
    for title, reason in result.failed:
        console.print(f"  [red]FAIL[/red] {title}: {reason}")


if __name__ == "__main__":
    cli()
