"""Command Line Interface for touring-machine."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from touring_machine.exceptions import AuthenticationError, TouringMachineError
from touring_machine.services.factory import SUPPORTED_SERVICES, get_streaming_service
from touring_machine.services.tidal import TidalService

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
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Details")

    for service_name in sorted(SUPPORTED_SERVICES):
        service = get_streaming_service(service_name)
        is_auth = service.is_authenticated()
        status_text = (
            "[green]Authenticated[/green]" if is_auth else "[yellow]Not logged in[/yellow]"
        )

        details = ""
        if isinstance(service, TidalService):
            details = f"Session file: {service.session_path}"

        table.add_row(service_name, status_text, details)

    console.print(table)


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


def main() -> None:
    """Entrypoint function for CLI execution."""
    app()


if __name__ == "__main__":
    main()
