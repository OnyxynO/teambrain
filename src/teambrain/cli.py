from __future__ import annotations
from datetime import date
from pathlib import Path

import frontmatter as fm
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .adr import ADR, _to_markdown, from_post, list_adrs, next_id, save_adr, search_adrs
from .ai import generate_draft
from .config import find_decisions_dir, load_config, save_config

app = typer.Typer(no_args_is_help=True, help="TeamBrain — mémoire décisionnelle d'équipe, git-native.")
console = Console()
err = Console(stderr=True)

_STATUT_COLORS = {
    "accepte": "green",
    "propose": "yellow",
    "deprecie": "red",
    "remplace": "dim",
}


def _require_dir() -> Path:
    d = find_decisions_dir()
    if d is None:
        err.print("[red]Aucun répertoire .decisions/ trouvé.[/red] Lance [bold]teambrain init[/bold] d'abord.")
        raise typer.Exit(1)
    return d


def _print_adr(adr: ADR) -> None:
    modules_str = ", ".join(adr.modules) if adr.modules else "—"
    decideurs_str = ", ".join(adr.decideurs) if adr.decideurs else "—"
    content = (
        f"[bold]#{adr.id:03d} — {adr.titre}[/bold]\n"
        f"[dim]Date :[/dim] {adr.date.isoformat()}  "
        f"[dim]Statut :[/dim] {adr.statut}  "
        f"[dim]Modules :[/dim] {modules_str}  "
        f"[dim]Décideurs :[/dim] {decideurs_str}\n\n"
        f"[bold]Contexte[/bold]\n{adr.contexte or '[dim](vide)[/dim]'}\n\n"
        f"[bold]Décision[/bold]\n{adr.decision or '[dim](vide)[/dim]'}\n\n"
        f"[bold]Conséquences[/bold]\n{adr.consequences or '[dim](vide)[/dim]'}"
    )
    console.print(Panel(content, border_style="blue"))


@app.command()
def init():
    """Initialise TeamBrain dans le repo courant (.decisions/ + config)."""
    cwd = Path.cwd()
    decisions_dir = cwd / ".decisions"

    if decisions_dir.exists():
        console.print(f"[yellow].decisions/ existe déjà dans {cwd}[/yellow]")
        raise typer.Exit(0)

    decisions_dir.mkdir()
    save_config(decisions_dir, {})

    gitignore = cwd / ".gitignore"
    db_entry = ".decisions/*.db\n"
    if gitignore.exists():
        if db_entry.strip() not in gitignore.read_text():
            with gitignore.open("a") as f:
                f.write("\n" + db_entry)
    else:
        gitignore.write_text(db_entry)

    console.print(f"[green]✓[/green] .decisions/ créé dans {cwd}")
    console.print("[dim]Lance [bold]teambrain add[/bold] pour créer ton premier ADR.[/dim]")


@app.command()
def add(
    description: str = typer.Argument("", help="Description libre de la décision"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Créer un ADR vide sans génération IA"),
):
    """Crée un nouvel ADR avec génération IA du brouillon."""
    decisions_dir = _require_dir()
    config = load_config(decisions_dir)

    if not description:
        description = typer.prompt("Décris la décision")

    adr_id = next_id(decisions_dir)

    if no_ai:
        adr = ADR(
            id=adr_id, titre="Nouvelle décision", date=date.today(),
            statut="propose", modules=[], decideurs=[],
            contexte="", decision=description, consequences="",
        )
    else:
        with console.status(f"[dim]Génération du brouillon via {config['model']}…[/dim]"):
            try:
                draft = generate_draft(description, config["model"])
            except Exception as exc:
                err.print(f"[red]Erreur Ollama :[/red] {exc}")
                err.print("[dim]Utilise --no-ai pour créer un ADR vide.[/dim]")
                raise typer.Exit(1)

        adr = ADR(
            id=adr_id,
            titre=draft.get("titre", description[:60]),
            date=date.today(),
            statut="propose",
            modules=draft.get("modules", []),
            decideurs=draft.get("decideurs", []),
            contexte=draft.get("contexte", ""),
            decision=draft.get("decision", ""),
            consequences=draft.get("consequences", ""),
        )

    _print_adr(adr)
    action = typer.prompt("Action", default="v", prompt_suffix=" [v]alider / [e]diter / [a]nnuler → ")

    if action.lower().startswith("a"):
        console.print("[dim]Annulé.[/dim]")
        raise typer.Exit(0)

    if action.lower().startswith("e"):
        edited = typer.edit(_to_markdown(adr), extension=".md")
        if edited:
            post = fm.loads(edited)
            adr = from_post(post, None)
            adr.id = adr_id

    path = save_adr(adr, decisions_dir)
    console.print(f"[green]✓[/green] ADR #{adr_id:03d} sauvegardé → {path.name}")


@app.command(name="list")
def list_cmd(
    module: str = typer.Option("", "--module", "-m", help="Filtrer par module"),
    statut: str = typer.Option("", "--statut", "-s", help="Filtrer par statut"),
):
    """Liste tous les ADR du repo."""
    decisions_dir = _require_dir()
    adrs = list_adrs(decisions_dir)

    if module:
        adrs = [a for a in adrs if module.lower() in [m.lower() for m in a.modules]]
    if statut:
        adrs = [a for a in adrs if a.statut.lower() == statut.lower()]

    if not adrs:
        console.print("[dim]Aucun ADR trouvé.[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=4)
    table.add_column("Titre")
    table.add_column("Modules", style="cyan")
    table.add_column("Statut", width=10)
    table.add_column("Date", style="dim", width=12)

    for adr in adrs:
        color = _STATUT_COLORS.get(adr.statut, "white")
        table.add_row(
            f"{adr.id:03d}",
            adr.titre,
            ", ".join(adr.modules) or "—",
            f"[{color}]{adr.statut}[/{color}]",
            adr.date.isoformat(),
        )

    console.print(table)


@app.command()
def search(query: str = typer.Argument(..., help="Termes de recherche")):
    """Recherche textuelle dans les ADR."""
    decisions_dir = _require_dir()
    results = search_adrs(query, decisions_dir)

    if not results:
        console.print(f"[dim]Aucun résultat pour « {query} ».[/dim]")
        return

    for adr, score in results:
        console.print(
            f"[bold]ADR #{adr.id:03d}[/bold] — {adr.titre} "
            f"[dim](score : {int(score * 100)}%)[/dim]"
        )
        if adr.decision:
            console.print(f"  [dim]{adr.decision[:120].replace(chr(10), ' ')}…[/dim]")
        console.print()


@app.command()
def show(id: int = typer.Argument(..., help="ID de l'ADR à afficher")):
    """Affiche un ADR complet."""
    decisions_dir = _require_dir()
    adr = next((a for a in list_adrs(decisions_dir) if a.id == id), None)
    if adr is None:
        err.print(f"[red]ADR #{id:03d} introuvable.[/red]")
        raise typer.Exit(1)
    _print_adr(adr)
