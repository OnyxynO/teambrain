from __future__ import annotations
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .adr import ADR, list_adrs
from .adr import search_adrs as text_search
from .config import find_decisions_dir, load_config
from .store import search_semantic

mcp_app = FastMCP("TeamBrain — mémoire décisionnelle d'équipe")


def _get_ctx() -> tuple[Path, dict, dict[int, ADR]]:
    d = find_decisions_dir()
    if d is None:
        raise RuntimeError("Aucun .decisions/ trouvé. Lance teambrain init dans le repo.")
    config = load_config(d)
    adrs = {a.id: a for a in list_adrs(d)}
    return d, config, adrs


def _fmt(adr: ADR) -> str:
    modules = ", ".join(adr.modules) if adr.modules else "—"
    return (
        f"**ADR #{adr.id:03d} — {adr.titre}**\n"
        f"Modules : {modules} | Statut : {adr.statut} | Date : {adr.date.isoformat()}\n\n"
        f"**Contexte**\n{adr.contexte or '(vide)'}\n\n"
        f"**Décision**\n{adr.decision or '(vide)'}\n\n"
        f"**Conséquences**\n{adr.consequences or '(vide)'}\n"
    )


def _resolve_hits(hits: list[tuple[int, float]], adrs: dict[int, ADR]) -> list[ADR]:
    return [adrs[adr_id] for adr_id, _ in hits if adr_id in adrs]


@mcp_app.tool()
def search_decisions(query: str, module: str = "") -> str:
    """Recherche sémantique dans les ADR de l'équipe."""
    d, config, adrs = _get_ctx()
    hits = search_semantic(query, d, config)
    found = _resolve_hits(hits, adrs) if hits else [a for a, _ in text_search(query, d)[:5]]

    if module:
        found = [a for a in found if module.lower() in [m.lower() for m in a.modules]]

    return "\n---\n".join(_fmt(a) for a in found) if found else "Aucun ADR pertinent trouvé."


@mcp_app.tool()
def get_decision(id: int) -> str:
    """Récupère le contenu complet d'un ADR par son ID."""
    _, _, adrs = _get_ctx()
    adr = adrs.get(id)
    return _fmt(adr) if adr else f"ADR #{id:03d} introuvable."


@mcp_app.tool()
def list_decisions(module: str = "", statut: str = "") -> str:
    """Liste les ADR, optionnellement filtrés par module ou statut."""
    _, _, adrs = _get_ctx()
    items = list(adrs.values())
    if module:
        items = [a for a in items if module.lower() in [m.lower() for m in a.modules]]
    if statut:
        items = [a for a in items if a.statut.lower() == statut.lower()]
    if not items:
        return "Aucun ADR trouvé."
    return "\n".join(
        f"#{a.id:03d} — {a.titre} [{a.statut}] modules: {', '.join(a.modules) or '—'}"
        for a in items
    )


@mcp_app.tool()
def get_context_for_file(filepath: str) -> str:
    """Retourne les ADR pertinents pour un fichier ou chemin donné."""
    d, config, adrs = _get_ctx()

    # Correspondance par nom de module dans le chemin
    parts = {p.lower() for p in Path(filepath).parts}
    by_module = [
        a for a in adrs.values()
        if any(m.lower() in parts for m in a.modules)
    ]

    # Recherche sémantique sur le chemin
    hits = search_semantic(filepath, d, config, k=3)
    by_semantic = _resolve_hits(hits, adrs)

    # Fusion sans doublons (module > sémantique)
    seen: set[int] = set()
    merged: list[ADR] = []
    for a in by_module + by_semantic:
        if a.id not in seen:
            seen.add(a.id)
            merged.append(a)

    if not merged:
        return f"Aucun ADR lié à `{filepath}`."

    return f"ADR pertinents pour `{filepath}` :\n\n" + "\n---\n".join(_fmt(a) for a in merged[:3])
