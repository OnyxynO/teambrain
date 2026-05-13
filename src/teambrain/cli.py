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


@app.command()
def index():
    """Indexe les ADR dans sqlite-vec pour la recherche sémantique."""
    decisions_dir = _require_dir()
    config = load_config(decisions_dir)
    model = config.get("embedding_model", "qwen3-embedding:0.6b")
    with console.status(f"[dim]Indexation via {model}…[/dim]"):
        try:
            from .store import reindex
            n = reindex(decisions_dir, config)
        except Exception as exc:
            err.print(f"[red]Erreur :[/red] {exc}")
            raise typer.Exit(1)
    if n == 0:
        console.print("[yellow]Aucun ADR à indexer.[/yellow]")
    else:
        console.print(f"[green]✓[/green] {n} ADR indexés.")


@app.command()
def serve():
    """Lance le serveur MCP (stdio) pour Claude Code / Cursor."""
    from .server import mcp_app
    mcp_app.run(transport="stdio")


@app.command()
def setup(
    platform: str = typer.Argument(
        "", help="Plateforme à configurer : 'slack' pour le wizard Slack, vide pour Claude Code/Cursor"
    ),
):
    """Configure TeamBrain : MCP (Claude Code/Cursor) ou wizard Slack."""
    if platform.lower() == "slack":
        _setup_slack()
    elif platform == "":
        _setup_mcp()
    else:
        err.print(f"[red]Plateforme inconnue : '{platform}'.[/red]")
        err.print("[dim]Utilise [bold]teambrain setup[/bold] ou [bold]teambrain setup slack[/bold].[/dim]")
        raise typer.Exit(1)


def _setup_mcp() -> None:
    """Configure le serveur MCP dans Claude Code et Cursor (si détectés)."""
    import json

    entry = {"command": "teambrain", "args": ["serve"]}
    configured: list[str] = []

    # Claude Code — ~/.claude.json
    claude_cfg = Path.home() / ".claude.json"
    if claude_cfg.exists():
        data = json.loads(claude_cfg.read_text(encoding="utf-8"))
        data.setdefault("mcpServers", {})["teambrain"] = entry
        claude_cfg.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        configured.append("Claude Code (~/.claude.json)")

    # Cursor — ~/.cursor/mcp.json
    cursor_cfg = Path.home() / ".cursor" / "mcp.json"
    if cursor_cfg.parent.exists():
        data = json.loads(cursor_cfg.read_text(encoding="utf-8")) if cursor_cfg.exists() else {}
        data.setdefault("mcpServers", {})["teambrain"] = entry
        cursor_cfg.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        configured.append("Cursor (~/.cursor/mcp.json)")

    if configured:
        for c in configured:
            console.print(f"[green]✓[/green] {c}")
        console.print("[dim]Redémarre le client pour activer.[/dim]")
    else:
        console.print("[yellow]Aucun client détecté.[/yellow] Ajoute manuellement :")
        console.print_json(json.dumps({"mcpServers": {"teambrain": entry}}, indent=2))


def _setup_slack() -> None:
    """Wizard interactif de configuration Slack pour le Chat Bot."""
    import json

    console.print(
        Panel(
            "[bold]Configuration Slack — TeamBrain Chat Bot[/bold]\n"
            "[dim]Ce wizard te guide pour créer et configurer une app Slack.\n"
            "Appuie sur Ctrl+C à tout moment pour annuler.[/dim]",
            border_style="blue",
        )
    )

    try:
        # ── Étape 1 ────────────────────────────────────────────────────────────
        console.print(
            Panel(
                "[bold]Étape 1 — Créer l'app Slack[/bold]\n\n"
                "Ouvre l'URL suivante dans ton navigateur pour créer une nouvelle app :\n\n"
                "  [cyan]https://api.slack.com/apps?new_app=1[/cyan]\n\n"
                "Sélectionne [bold]« From scratch »[/bold], donne un nom (ex: TeamBrain)\n"
                "et choisis ton workspace.",
                border_style="yellow",
            )
        )
        typer.confirm("Étape 1 terminée ?", abort=True)

        # ── Étape 2 ────────────────────────────────────────────────────────────
        console.print(
            Panel(
                "[bold]Étape 2 — Activer Socket Mode et configurer les permissions[/bold]\n\n"
                "[bold]2a. Socket Mode[/bold]\n"
                "  → Settings > Socket Mode → activer [bold]Enable Socket Mode[/bold]\n"
                "  → Génère un App-Level Token avec le scope [cyan]connections:write[/cyan]\n"
                "     (note le token [bold]xapp-...[/bold])\n\n"
                "[bold]2b. OAuth Scopes (Bot Token)[/bold]\n"
                "  → OAuth & Permissions > Scopes > Bot Token Scopes\n"
                "  → Ajoute les scopes suivants :\n\n"
                "     [cyan]channels:history[/cyan]   lire les messages des canaux publics\n"
                "     [cyan]groups:history[/cyan]     lire les messages des canaux privés\n"
                "     [cyan]im:history[/cyan]         lire les messages directs\n"
                "     [cyan]chat:write[/cyan]         envoyer des messages\n"
                "     [cyan]im:write[/cyan]           ouvrir des DM\n"
                "     [cyan]users:read[/cyan]         lire les infos utilisateurs",
                border_style="yellow",
            )
        )
        typer.confirm("Étape 2 terminée ?", abort=True)

        # ── Étape 3 ────────────────────────────────────────────────────────────
        console.print(
            Panel(
                "[bold]Étape 3 — Activer les Event Subscriptions[/bold]\n\n"
                "  → Event Subscriptions → activer [bold]Enable Events[/bold]\n\n"
                "  → Subscribe to Bot Events → ajoute :\n\n"
                "     [cyan]message.channels[/cyan]   messages dans les canaux publics\n"
                "     [cyan]message.groups[/cyan]     messages dans les canaux privés\n\n"
                "[dim](Pas besoin de Request URL en Socket Mode — Slack utilise le WebSocket.)[/dim]",
                border_style="yellow",
            )
        )
        typer.confirm("Étape 3 terminée ?", abort=True)

        # ── Étape 4 ────────────────────────────────────────────────────────────
        console.print(
            Panel(
                "[bold]Étape 4 — Activer Interactivity & Shortcuts[/bold]\n\n"
                "  → Interactivity & Shortcuts → activer [bold]Interactivity[/bold]\n\n"
                "[dim]En Socket Mode, aucune URL de Request URL n'est nécessaire.\n"
                "Slack transmet les actions (boutons Block Kit) via le WebSocket.[/dim]",
                border_style="yellow",
            )
        )
        typer.confirm("Étape 4 terminée ?", abort=True)

        # ── Étape 5 ────────────────────────────────────────────────────────────
        console.print(
            Panel(
                "[bold]Étape 5 — Installer l'app dans le workspace[/bold]\n\n"
                "  → OAuth & Permissions → [bold]Install to Workspace[/bold]\n"
                "  → Autorise l'app\n"
                "  → Copie le [bold]Bot User OAuth Token[/bold] (commence par [cyan]xoxb-...[/cyan])\n\n"
                "Ton ID utilisateur Slack :\n"
                "  → Clique sur ton avatar > Profil > ⋮ > Copier l'identifiant du membre\n"
                "  → Format : [cyan]U01XXXXXXXX[/cyan]",
                border_style="yellow",
            )
        )
        typer.confirm("Étape 5 terminée ?", abort=True)

        # ── Collecte des tokens ────────────────────────────────────────────────
        console.print()
        console.print("[bold]Collecte des informations de configuration[/bold]")
        console.print()

        bot_token = typer.prompt("SLACK_BOT_TOKEN (xoxb-...)", hide_input=True)
        app_token = typer.prompt("SLACK_APP_TOKEN (xapp-...)", hide_input=True)
        lead_id = typer.prompt("TEAMBRAIN_LEAD (ID utilisateur Slack, ex: U01XXXXXXXX)")
        canaux_str = typer.prompt(
            "Canaux à surveiller (séparés par des virgules)",
            default="#architecture,#decisions",
        )

    except typer.Abort:
        console.print("\n[yellow]Configuration annulée — aucun fichier écrit.[/yellow]")
        raise typer.Exit(0)

    # ── Écriture .env.teambrain ────────────────────────────────────────────────
    env_path = Path.cwd() / ".env.teambrain"
    env_content = (
        f"SLACK_BOT_TOKEN={bot_token}\n"
        f"SLACK_APP_TOKEN={app_token}\n"
        f"TEAMBRAIN_LEAD={lead_id}\n"
    )
    env_path.write_text(env_content, encoding="utf-8")
    console.print(f"\n[green]✓[/green] {env_path} écrit.")

    gitignore = Path.cwd() / ".gitignore"
    env_entry = ".env.teambrain\n"
    if gitignore.exists():
        if env_entry.strip() not in gitignore.read_text():
            with gitignore.open("a") as f:
                f.write("\n" + env_entry)
    else:
        gitignore.write_text(env_entry)
    console.print("[green]✓[/green] .env.teambrain ajouté au .gitignore")

    # ── Mise à jour .decisions/.teambrain.json ─────────────────────────────────
    canaux = [c.strip() for c in canaux_str.split(",") if c.strip()]
    decisions_dir = find_decisions_dir()
    if decisions_dir is not None:
        config = load_config(decisions_dir)
        config.setdefault("chat", {})["channels"] = canaux
        save_config(decisions_dir, config)
        console.print(f"[green]✓[/green] Canaux mis à jour dans .decisions/.teambrain.json : {', '.join(canaux)}")
    else:
        console.print(
            "[yellow]Aucun .decisions/ trouvé.[/yellow] Lance [bold]teambrain init[/bold] "
            "puis reconfig les canaux dans .decisions/.teambrain.json :"
        )
        console.print_json(json.dumps({"chat": {"channels": canaux}}, indent=2, ensure_ascii=False))

    # ── Résumé final ───────────────────────────────────────────────────────────
    console.print(
        Panel(
            "[bold green]Configuration Slack terminée ![/bold green]\n\n"
            "Lance le bot avec :\n\n"
            f"  [cyan]source {env_path.name}[/cyan]\n"
            "  [cyan]teambrain bot --confidence 0.7[/cyan]\n\n"
            "[dim]Le fichier .env.teambrain contient tes tokens — ne le commite pas.[/dim]",
            border_style="green",
        )
    )


@app.command()
def bot(
    platform: str = typer.Option("slack", "--platform", "-p", help="Plateforme de chat"),
    confidence: float = typer.Option(0.7, "--confidence", "-c", help="Seuil de confiance IA (0-1)"),
):
    """Lance le Chat Bot pour détecter les décisions dans les canaux.

    Variables d'env requises pour Slack :
    - SLACK_BOT_TOKEN (xoxb-...)
    - SLACK_APP_TOKEN (xapp-...)
    - TEAMBRAIN_LEAD (ID utilisateur pour les DM)

    Pour GitHub (création PR optionnelle) :
    - GITHUB_TOKEN (ghp-...)
    - GITHUB_REPO (owner/repo)
    """
    import os
    from .chat import DecisionBot
    from .chat.adapters import SlackAdapter

    decisions_dir = _require_dir()
    config = load_config(decisions_dir)
    config["confidence_threshold"] = confidence

    if platform.lower() != "slack":
        err.print(f"[red]Plateforme '{platform}' non supportée.[/red]")
        err.print("[dim]Plateforme supportée : slack[/dim]")
        raise typer.Exit(1)

    bot_token = os.getenv(config["chat"].get("bot_token_env", "SLACK_BOT_TOKEN"))
    app_token = os.getenv(config["chat"].get("app_token_env", "SLACK_APP_TOKEN"))
    lead_id = os.getenv(config["chat"].get("lead_user_id_env", "TEAMBRAIN_LEAD"))
    channels = config["chat"].get("channels", [])

    if not bot_token or not app_token:
        err.print("[red]Tokens Slack manquants.[/red]")
        err.print(f"[dim]Définis {config['chat'].get('bot_token_env')} et {config['chat'].get('app_token_env')}[/dim]")
        raise typer.Exit(1)

    if not channels:
        err.print("[yellow]Aucun canal configuré.[/yellow]")
        err.print("[dim]Ajoute des canaux dans .decisions/.teambrain.json → chat.channels[/dim]")
        raise typer.Exit(1)

    config["lead_user_id"] = lead_id

    adapter = SlackAdapter(bot_token, app_token)

    github_creator = None
    github_token = os.getenv(config["github"].get("token_env"))
    github_repo = os.getenv(config["github"].get("repo_env"))
    if github_token and github_repo:
        try:
            from .chat.github import GitHubPRCreator
            github_creator = GitHubPRCreator(github_token, github_repo)
        except ImportError:
            err.print("[yellow]PyGithub non installé. Installe avec : pip install -e '.[bot]'[/yellow]")

    try:
        console.print(f"[green]▶[/green] TeamBrain bot démarré sur Slack (confiance : {confidence})")
        console.print(f"[dim]Canaux : {', '.join(channels)}[/dim]")
        bot_instance = DecisionBot(adapter, decisions_dir, config, github_creator)
        bot_instance.run(channels)
    except KeyboardInterrupt:
        console.print("[yellow]Bot arrêté.[/yellow]")
    except Exception as exc:
        err.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1)
