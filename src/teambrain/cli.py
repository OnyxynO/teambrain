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
from .scanner import Candidat, scanner_commits, scanner_code, scanner_commits_semantique

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
    gitignore_entries = [".decisions/*.db", ".decisions/.teambrain_pending.json"]
    if gitignore.exists():
        content = gitignore.read_text()
        additions = [e for e in gitignore_entries if e not in content]
        if additions:
            with gitignore.open("a") as f:
                f.write("\n" + "\n".join(additions) + "\n")
    else:
        gitignore.write_text("\n".join(gitignore_entries) + "\n")

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


def _slack_app_manifest(app_name: str = "TeamBrain") -> dict:
    """Génère le manifest Slack pour création automatique de l'app."""
    return {
        "display_information": {"name": app_name},
        "features": {
            "bot_user": {"display_name": app_name, "always_online": False}
        },
        "oauth_config": {
            "scopes": {
                "bot": [
                    "channels:read", "channels:history",
                    "groups:read", "groups:history",
                    "im:history", "chat:write", "im:write", "users:read",
                ]
            }
        },
        "settings": {
            "event_subscriptions": {
                "bot_events": ["message.channels", "message.groups"]
            },
            "interactivity": {"is_enabled": True},
            "socket_mode_enabled": True,
            "token_rotation_enabled": False,
        },
    }


def _setup_slack() -> None:
    """Wizard de configuration Slack — manifest + tokens."""
    import json

    console.print(
        Panel(
            "[bold]Configuration Slack — TeamBrain Chat Bot[/bold]\n"
            "[dim]Ctrl+C à tout moment pour annuler.[/dim]",
            border_style="blue",
        )
    )

    try:
        app_name = typer.prompt("Nom de l'app Slack", default="TeamBrain")
        manifest = _slack_app_manifest(app_name)
        manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)

        # ── Étape 1 : manifest ─────────────────────────────────────────────────
        console.print(
            Panel(
                "[bold]Étape 1 — Créer l'app depuis le manifest[/bold]\n\n"
                "1. Ouvrir : [cyan]https://api.slack.com/apps?new_app=1[/cyan]\n"
                "   → Choisir [bold]« From an app manifest »[/bold]\n"
                "   → Sélectionner ton workspace\n"
                "   → Coller le manifest ci-dessous → Suivant → Créer\n\n"
                "2. [bold]App-Level Token[/bold]  Settings > Socket Mode → Activer\n"
                "   → « Generate an app-level token » · scope [cyan]connections:write[/cyan]\n"
                "   → Copier le token ([cyan]xapp-...[/cyan])\n\n"
                "3. [bold]Bot Token[/bold]  OAuth & Permissions > Install to Workspace\n"
                "   → Autoriser → copier le Bot User OAuth Token ([cyan]xoxb-...[/cyan])\n\n"
                "4. [bold]Inviter le bot[/bold] dans chaque canal à surveiller\n"
                "   → [cyan]/invite @" + app_name + "[/cyan]",
                border_style="yellow",
            )
        )
        console.print(Panel(manifest_json, title="[bold]Manifest — à coller sur api.slack.com[/bold]", border_style="cyan"))
        typer.confirm("App créée et installée ?", abort=True)

        # ── Étape 2 : collecte des tokens ─────────────────────────────────────
        console.print("\n[bold]Étape 2 — Tokens et canaux[/bold]\n")

        while True:
            app_token = typer.prompt("App-Level Token (xapp-...)", hide_input=True)
            if app_token.startswith("xapp-"):
                break
            console.print("[red]  Format invalide[/red] — doit commencer par [cyan]xapp-[/cyan]")

        while True:
            bot_token = typer.prompt("Bot User OAuth Token (xoxb-...)", hide_input=True)
            if bot_token.startswith("xoxb-"):
                break
            console.print("[red]  Format invalide[/red] — doit commencer par [cyan]xoxb-[/cyan]")

        lead_id = typer.prompt(
            "Ton ID utilisateur Slack\n"
            "  (Profil > ⋮ > Copier l'identifiant du membre, ex: U01XXXXXXXX)\n  ",
        )

        canaux_str = typer.prompt(
            "Canaux à surveiller (séparés par des virgules, avec #)\n  ",
            default="#general",
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
    import os as _os
    _os.chmod(env_path, 0o600)
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
        config["chat"]["channels"] = canaux
        save_config(decisions_dir, config)
        console.print(f"[green]✓[/green] Canaux sauvegardés : {', '.join(canaux)}")
    else:
        console.print(
            "[yellow]Aucun .decisions/ trouvé.[/yellow] Lance [bold]teambrain init[/bold] "
            "puis reconfig les canaux dans .decisions/.teambrain.json :"
        )
        console.print_json(json.dumps({"chat": {"channels": canaux}}, indent=2, ensure_ascii=False))

    # ── Résumé final ───────────────────────────────────────────────────────────
    console.print(
        Panel(
            "[bold green]Configuration terminée ![/bold green]\n\n"
            "Lance le bot avec :\n\n"
            "  [cyan]teambrain bot[/cyan]\n\n"
            "[dim]Tokens stockés dans .env.teambrain (chargé automatiquement au démarrage).[/dim]",
            border_style="green",
        )
    )


def _check_slack(bot_token: str, lead_id: str | None, channels: list[str]) -> None:
    """Vérifie la configuration Slack sans lancer le bot."""
    try:
        from slack_sdk import WebClient
    except ImportError:
        err.print("[red]slack-sdk non installé.[/red] Lance : pip install -e '.[bot]'")
        raise typer.Exit(1)

    client = WebClient(token=bot_token)
    ok = True

    # 1. Authentification
    try:
        auth = client.auth_test()
        console.print(f"[green]✓[/green] Token valide — bot [bold]{auth['bot_id']}[/bold] sur workspace [bold]{auth['team']}[/bold]")
    except Exception as e:
        console.print(f"[red]✗[/red] Token invalide : {e}")
        raise typer.Exit(1)

    # 2. Présence du bot dans chaque canal (vérification réelle)
    bot_name = auth.get("user", "TeamBrain")
    if not channels:
        console.print("[red]✗[/red] Aucun canal configuré dans .decisions/.teambrain.json")
        ok = False
    else:
        # Récupérer les canaux où le bot est membre
        try:
            resp = client.conversations_list(exclude_archived=True, limit=500)
            joined = {ch["name"] for ch in resp.get("channels", []) if ch.get("is_member")}
        except Exception:
            joined = set()

        for canal in channels:
            name = canal.lstrip("#")
            if joined and name in joined:
                console.print(f"[green]✓[/green] Bot présent dans {canal}")
            elif not joined:
                console.print(f"[yellow]![/yellow] Impossible de vérifier {canal} (scope conversations:list requis)")
            else:
                console.print(f"[red]✗[/red] Bot absent de {canal} — tape [cyan]/invite @{bot_name}[/cyan] dans ce canal")
                ok = False

    # 3. DM test au lead
    if lead_id:
        try:
            client.chat_postMessage(
                channel=lead_id,
                text="[TeamBrain] Vérification de configuration — tout est opérationnel. ✓",
            )
            console.print(f"[green]✓[/green] DM envoyé à {lead_id} — la messagerie fonctionne")
        except Exception as e:
            console.print(f"[red]✗[/red] Impossible d'envoyer un DM à {lead_id} : {e}")
            ok = False
    else:
        console.print("[yellow]![/yellow] TEAMBRAIN_LEAD non défini — le bot ne pourra pas envoyer de DM")
        ok = False

    if ok:
        console.print("\n[green]Configuration OK.[/green] Lance [bold]teambrain bot[/bold] pour démarrer.")
    else:
        console.print("\n[yellow]Problèmes détectés.[/yellow] Corrige-les avant de lancer le bot.")


@app.command()
def bot(
    platform: str = typer.Option("slack", "--platform", "-p", help="Plateforme de chat"),
    confidence: float = typer.Option(0.7, "--confidence", "-c", help="Seuil de confiance IA (0-1)"),
    check: bool = typer.Option(False, "--check", help="Vérifier la configuration sans lancer le bot"),
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

    # Charger .env.teambrain automatiquement s'il existe
    env_file = Path.cwd() / ".env.teambrain"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

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

    if check:
        _check_slack(bot_token, lead_id, channels)
        return

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

    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

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


# ──────────────────────────────────────────────────────────────
# Module 4 — Git/Code Mining
# ──────────────────────────────────────────────────────────────

def _afficher_candidat(candidat: Candidat) -> None:
    """Affiche un candidat dans un Panel rich."""
    date_str = candidat.date_commit.isoformat() if candidat.date_commit else "—"
    auteur_str = candidat.auteur or "—"
    pourcent = int(candidat.confiance * 100)
    couleur_conf = "green" if candidat.confiance >= 0.8 else "yellow"

    content = (
        f"[bold]{candidat.source.upper()}[/bold] · [dim]{candidat.ref}[/dim]"
        + (f" · {date_str}" if date_str != "—" else "")
        + (f" · {auteur_str}" if auteur_str != "—" else "")
        + (f" · [cyan][ADR #{candidat.adr_lie}][/cyan]" if candidat.adr_lie is not None else "")
        + f"\n\n[italic]{candidat.texte[:300]}[/italic]"
        + (f"\n\n[bold]Résumé :[/bold] {candidat.resume}" if candidat.resume else "")
        + f"\n\n[{couleur_conf}]Confiance : {pourcent}%[/{couleur_conf}]"
    )
    console.print(Panel(content, border_style="cyan"))


def _traiter_candidats(
    candidats: list[Candidat],
    decisions_dir: "Path",
    config: dict,
) -> int:
    """Boucle interactive sur les candidats. Retourne le nombre d'ADR créés."""
    nb_crees = 0

    for i, candidat in enumerate(candidats, start=1):
        console.print(f"\n[bold]Candidat {i}/{len(candidats)}[/bold]")
        _afficher_candidat(candidat)

        action = typer.prompt(
            "Action",
            default="i",
            prompt_suffix=" [v]alider / [i]gnorer / [a]rrêter → ",
        )

        if action.lower().startswith("a"):
            break

        if not action.lower().startswith("v"):
            console.print("[dim]Ignoré.[/dim]")
            continue

        # Valider → générer un ADR complet
        adr_id = next_id(decisions_dir)
        with console.status(f"[dim]Génération du brouillon via {config['model']}…[/dim]"):
            try:
                draft = generate_draft(candidat.texte, config["model"])
            except (ValueError, ConnectionError, OSError) as exc:
                err.print(f"[red]Erreur Ollama :[/red] {exc}")
                console.print("[dim]ADR ignoré (erreur de génération).[/dim]")
                continue

        adr = ADR(
            id=adr_id,
            titre=draft.get("titre", candidat.texte[:60]),
            date=candidat.date_commit or date.today(),
            statut="propose",
            modules=draft.get("modules", []),
            decideurs=draft.get("decideurs", []),
            contexte=draft.get("contexte", ""),
            decision=draft.get("decision", ""),
            consequences=draft.get("consequences", ""),
        )

        path = save_adr(adr, decisions_dir)
        console.print(f"[green]✓[/green] ADR #{adr_id:03d} sauvegardé → {path.name}")
        nb_crees += 1

    return nb_crees


@app.command(name="scan-commits")
def scan_commits(
    depuis: str = typer.Option("1w", "--depuis", help="Période à scanner : '1w', '3m', '6m', '1y' ou date ISO"),
    confiance: float = typer.Option(0.7, "--confiance", help="Seuil de confiance IA (0-1)"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Retourner tous les matchs bruts sans scoring IA"),
    pattern: list[str] = typer.Option([], "--pattern", "-p", help="Pattern supplémentaire (répétable)"),
    semanticmatch: bool = typer.Option(False, "--semanticmatch", help="Utiliser SemanticMatch (Haiku) au lieu d'Ollama"),
    semantic: bool = typer.Option(False, "--semantic", help="Mode sémantique : compare via l'index ADR (sans patterns regex)"),
):
    """Scanne les commits git récents pour détecter des décisions non documentées."""
    decisions_dir = _require_dir()
    config = load_config(decisions_dir)
    chemin_repo = decisions_dir.parent

    # ── Mode sémantique : comparaison directe contre l'index ADR ──────────────
    if semantic:
        if no_ai or pattern or semanticmatch:
            console.print("[yellow]Avertissement : --no-ai, --pattern et --semanticmatch sont ignorés en mode --semantic.[/yellow]")
        console.print("[dim]Mode sémantique — comparaison contre l'index ADR…[/dim]")
        try:
            candidats = scanner_commits_semantique(
                chemin_repo, decisions_dir, config, depuis=depuis,
            )
        except RuntimeError as exc:
            err.print(f"[red]Erreur :[/red] {exc}")
            raise typer.Exit(1)

        if not candidats:
            console.print("[dim]Aucun candidat trouvé.[/dim]")
            return

        console.print(f"[bold]{len(candidats)} candidat(s) détecté(s).[/bold]\n")
        nb_crees = _traiter_candidats(candidats, decisions_dir, config)
        console.print(
            f"\n[bold]{len(candidats)} candidats analysés, {nb_crees} ADR créés.[/bold]"
        )
        return

    # ── Mode classique : patterns regex + scoring IA ───────────────────────────
    sm_url = config.get("semanticmatch_url") if semanticmatch else None

    patterns_extra = list(pattern) + config.get("commit_patterns", [])
    if patterns_extra:
        console.print(f"[dim]Patterns supplémentaires : {', '.join(patterns_extra)}[/dim]")
    backend = f"SemanticMatch ({sm_url})" if sm_url else f"Ollama ({config['model']})"
    console.print(f"[dim]Scan des commits depuis {depuis} (confiance min : {int(confiance * 100)}%, backend : {backend})…[/dim]")

    try:
        candidats = scanner_commits(
            chemin_repo, depuis, config["model"], confiance,
            score_ia=not no_ai,
            patterns_extra=patterns_extra or None,
            semanticmatch_url=sm_url,
        )
    except (RuntimeError, ConnectionError) as exc:
        err.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1)

    if not candidats:
        console.print("[dim]Aucun candidat trouvé.[/dim]")
        return

    console.print(f"[bold]{len(candidats)} candidat(s) détecté(s).[/bold]\n")
    nb_crees = _traiter_candidats(candidats, decisions_dir, config)
    console.print(
        f"\n[bold]{len(candidats)} candidats analysés, {nb_crees} ADR créés.[/bold]"
    )


@app.command(name="scan-code")
def scan_code(
    pattern: list[str] = typer.Option([], "--pattern", "-p", help="Pattern supplémentaire à chercher (répétable)"),
    confiance: float = typer.Option(0.8, "--confiance", help="Seuil de confiance IA (0-1)"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Retourner tous les matchs bruts sans scoring IA"),
    semanticmatch: bool = typer.Option(False, "--semanticmatch", help="Utiliser SemanticMatch (Haiku) au lieu d'Ollama"),
):
    """Scanne les fichiers du repo pour détecter des marqueurs décisionnels dans les commentaires."""
    decisions_dir = _require_dir()
    config = load_config(decisions_dir)
    chemin_repo = decisions_dir.parent
    sm_url = config.get("semanticmatch_url") if semanticmatch else None

    patterns_extra = list(pattern) + config.get("code_patterns", [])
    if patterns_extra:
        console.print(f"[dim]Patterns supplémentaires : {', '.join(patterns_extra)}[/dim]")
    backend = f"SemanticMatch ({sm_url})" if sm_url else f"Ollama ({config['model']})"
    console.print(f"[dim]Scan du code (confiance min : {int(confiance * 100)}%, backend : {backend})…[/dim]")

    try:
        candidats = scanner_code(
            chemin_repo, patterns_extra or None, config["model"], confiance,
            score_ia=not no_ai,
            semanticmatch_url=sm_url,
        )
    except (RuntimeError, ConnectionError) as exc:
        err.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1)

    if not candidats:
        console.print("[dim]Aucun candidat trouvé.[/dim]")
        return

    console.print(f"[bold]{len(candidats)} candidat(s) détecté(s).[/bold]\n")
    nb_crees = _traiter_candidats(candidats, decisions_dir, config)
    console.print(
        f"\n[bold]{len(candidats)} candidats analysés, {nb_crees} ADR créés.[/bold]"
    )
