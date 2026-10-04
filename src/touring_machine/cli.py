"""Command Line Interface for touring-machine."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from touring_machine.config import get_api_key, save_api_key
from touring_machine.exceptions import (
    AuthenticationError,
    MissingApiKeyError,
    TouringMachineError,
)
from touring_machine.generator import PlaylistGenerator
from touring_machine.providers.setlistfm import SetlistFmProvider
from touring_machine.services.factory import SUPPORTED_SERVICES, get_streaming_service
from touring_machine.services.tidal import TidalService
from touring_machine.strategies.factory import get_strategy

app = typer.Typer(
    name="touring-machine",
    help="Concert playlist generator for music streaming services.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
error_console = Console(stderr=True)


@app.command("status")
def status_command() -> None:
    """Check authentication and configuration status for supported services."""
    table = Table(title="Touring Machine - Service Status", header_style="bold magenta")
    table.add_column("Type", style="dim", no_wrap=True)
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Details")

    # Streaming services
    for service_name in sorted(SUPPORTED_SERVICES):
        service = get_streaming_service(service_name)
        is_auth = service.is_authenticated()
        status_text = (
            "[green]Authenticated[/green]" if is_auth else "[yellow]Not logged in[/yellow]"
        )
        details = ""
        if isinstance(service, TidalService):
            details = f"Session: {service.session_path}"
        table.add_row("Streaming", service_name, status_text, details)

    # Concert providers
    setlist_key = get_api_key("setlistfm")
    setlist_status = (
        "[green]Configured[/green]" if setlist_key else "[yellow]Missing API key[/yellow]"
    )
    table.add_row(
        "Concerts",
        "setlistfm",
        setlist_status,
        "Get key at: https://www.setlist.fm/settings/api",
    )

    console.print(table)


@app.command("set-key")
def set_key_command(
    provider: Annotated[
        str,
        typer.Argument(help="Provider to set key for (e.g. 'setlistfm')."),
    ],
    api_key: Annotated[str, typer.Argument(help="The API key token.")],
) -> None:
    """Save an API key to the touring-machine configuration file."""
    save_api_key(api_key=api_key, provider=provider)
    console.print(f"[bold green]Successfully saved API key for '{provider.lower()}'![/bold green]")


@app.command("login")
def login_command(
    service_name: Annotated[
        str,
        typer.Option(
            "--service",
            "-s",
            help=f"Streaming service to authenticate with ({', '.join(SUPPORTED_SERVICES)}).",
        ),
    ] = "tidal",
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force re-authentication even if already logged in."),
    ] = False,
) -> None:
    """Log in to a streaming service using OAuth."""
    try:
        service = get_streaming_service(service_name)
    except ValueError as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    service_title = service.name.capitalize()
    if not force and service.is_authenticated():
        console.print(
            f"[green]Already authenticated with {service_title}![/green]\n"
            "Use [bold]--force[/bold] to re-authenticate."
        )
        return

    console.print(f"[bold cyan]Starting {service_title} login...[/bold cyan]")

    def prompt_url(url: str) -> None:
        console.print(
            Panel.fit(
                f"Please open the following URL in your browser to authorize Touring Machine:\n\n"
                f"[bold underline cyan]{url}[/bold underline cyan]\n\n"
                f"[dim]Waiting for authorization...[/dim]",
                title=f"{service_title} Authorization",
                border_style="cyan",
            )
        )

    try:
        success = service.authenticate(interactive=True, prompt_callback=prompt_url)
        if success:
            console.print(
                f"[bold green]Successfully authenticated with {service_title}![/bold green]"
            )
        else:
            error_console.print(f"[bold red]Authentication failed with {service_title}.[/bold red]")
            raise typer.Exit(code=1)
    except TouringMachineError as exc:
        error_console.print(f"[bold red]Authentication error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command("create-playlist")
def create_playlist_command(
    name: Annotated[str, typer.Argument(help="Name of the playlist to create.")],
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Description for the new playlist."),
    ] = "",
    service_name: Annotated[
        str,
        typer.Option(
            "--service",
            "-s",
            help=f"Streaming service provider ({', '.join(SUPPORTED_SERVICES)}).",
        ),
    ] = "tidal",
) -> None:
    """Create a new empty playlist on the chosen streaming platform."""
    try:
        service = get_streaming_service(service_name)
    except ValueError as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    service_title = service.name.capitalize()
    if not service.is_authenticated():
        error_console.print(
            f"[bold red]Not authenticated with {service_title}.[/bold red]\n"
            f"Please run [bold cyan]touring-machine login -s {service.name}[/bold cyan] first."
        )
        raise typer.Exit(code=1)

    with console.status(f"[cyan]Creating playlist '{name}' on {service_title}...[/cyan]"):
        try:
            playlist = service.create_playlist(name=name, description=description)
        except AuthenticationError as exc:
            error_console.print(f"[bold red]Authentication error:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc
        except TouringMachineError as exc:
            error_console.print(f"[bold red]Failed to create playlist:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc

    url_line = (
        f"[bold]URL:[/bold] [underline cyan]{playlist.url}[/underline cyan]\n"
        if playlist.url
        else ""
    )
    desc_line = f"[bold]Description:[/bold] {playlist.description}" if playlist.description else ""

    console.print(
        Panel(
            f"[bold]Name:[/bold] {playlist.name}\n"
            f"[bold]ID:[/bold] [dim]{playlist.id}[/dim]\n"
            f"{url_line}{desc_line}".rstrip(),
            title="[bold green]Playlist Created Successfully![/bold green]",
            border_style="green",
        )
    )


@app.command("generate")
def generate_command(
    artist: Annotated[str, typer.Argument(help="Name of the artist or band.")],
    shows: Annotated[
        int,
        typer.Option("--shows", "-n", help="Number of recent shows to analyze."),
    ] = 5,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum songs to include in the playlist."),
    ] = 25,
    strategy_name: Annotated[
        str,
        typer.Option(
            "--strategy",
            "-strat",
            help="Playlist strategy: 'most-played' or 'latest'.",
        ),
    ] = "most-played",
    name: Annotated[
        str | None,
        typer.Option(
            "--name", help="Custom playlist title (defaults to '<Artist> - Tour Setlist')."
        ),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Custom playlist description."),
    ] = None,
    service_name: Annotated[
        str,
        typer.Option(
            "--service",
            "-s",
            help=f"Target streaming service ({', '.join(SUPPORTED_SERVICES)}).",
        ),
    ] = "tidal",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview setlists and song matches without creating the playlist.",
        ),
    ] = False,
) -> None:
    """Generate a concert playlist from recent setlists on Setlist.fm."""
    # 1. Validate streaming service
    try:
        service = get_streaming_service(service_name)
    except ValueError as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if not dry_run and not service.is_authenticated():
        error_console.print(
            f"[bold red]Not authenticated with {service.name.capitalize()}.[/bold red]\n"
            f"Please run [bold cyan]touring-machine login -s {service.name}[/bold cyan] first."
        )
        raise typer.Exit(code=1)

    # 2. Validate concert provider
    try:
        provider = SetlistFmProvider()
        _ = provider.api_key  # check for key existence early
    except MissingApiKeyError as exc:
        error_console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    # 3. Validate strategy
    try:
        strategy = get_strategy(strategy_name)
    except ValueError as exc:
        error_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold cyan]Analyzing up to {shows} recent concerts for '{artist}'...[/bold cyan]"
    )

    generator = PlaylistGenerator(streaming_service=service, concert_provider=provider)

    try:
        if dry_run:
            setlists = provider.get_recent_setlists(artist, limit=shows)
            if not setlists:
                error_console.print(f"[bold red]No setlists found for '{artist}'.[/bold red]")
                raise typer.Exit(code=1)

            target_artist = setlists[0].artist
            song_titles = strategy.generate_tracklist(setlists, limit=limit)
            match_results = generator.matcher.match_songs(song_titles, target_artist.name)

            _render_match_table(match_results, target_artist.name, len(setlists))
            console.print("[dim]Dry run complete. No playlist was created.[/dim]")
            return

        with console.status("[cyan]Fetching setlists and matching songs...[/cyan]"):
            result = generator.generate(
                artist_name=artist,
                shows=shows,
                limit=limit,
                strategy_name=strategy_name,
                playlist_name=name,
                description=description,
            )
    except TouringMachineError as exc:
        error_console.print(f"[bold red]Generation error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    _render_match_table(result.match_results, result.artist.name, len(result.setlists))

    url_str = (
        f"\n[bold]URL:[/bold] [underline cyan]{result.playlist.url}[/underline cyan]"
        if result.playlist.url
        else ""
    )
    console.print(
        Panel(
            f"[bold]Playlist:[/bold] {result.playlist.name}\n"
            f"[bold]ID:[/bold] [dim]{result.playlist.id}[/dim]\n"
            f"[bold]Tracks Added:[/bold] {len(result.matched_tracks)} / {len(result.match_results)}"
            f"{url_str}",
            title="[bold green]Concert Playlist Generated Successfully![/bold green]",
            border_style="green",
        )
    )


def _render_match_table(
    match_results: list,
    artist_name: str,
    shows_count: int,
) -> None:
    """Render a pretty summary table of resolved tracks."""
    table = Table(
        title=f"Setlist Songs Resolved for {artist_name} ({shows_count} shows analyzed)",
        header_style="bold magenta",
    )
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Setlist Song", style="cyan")
    table.add_column("Streaming Match", style="white")
    table.add_column("Confidence", justify="right")
    table.add_column("Status", justify="center")

    for idx, item in enumerate(match_results, 1):
        if item.matched and item.track:
            match_title = f"{item.track.title} [dim]({item.track.artist})[/dim]"
            conf = f"{item.score:.0f}%"
            status = "[green]✓ Matched[/green]"
        else:
            match_title = "[dim]-[/dim]"
            conf = "[dim]-[/dim]"
            status = "[yellow]✗ Not found[/yellow]"

        table.add_row(str(idx), item.query_song, match_title, conf, status)

    console.print(table)


def main() -> None:
    """Entrypoint function for CLI execution."""
    app()


if __name__ == "__main__":
    main()
