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


def _modules_for_file(filepath: str, module_mappings: dict) -> set[str]:
    """Résout un chemin en ensemble de modules selon les mappings configurés.

    Stratégie (du plus précis au plus générique) :
    1. Mappings explicites (pattern de préfixe chemin -> module(s))
    2. Fallback : segments du chemin qui matchent un nom de module
    3. Vide si aucun match
    """
    modules: set[str] = set()

    # Normaliser le chemin (convertir séparateurs Windows)
    normalized = filepath.replace("\\", "/")

    # Niveau 1 : mappings explicites
    for pattern, mapped in module_mappings.items():
        pattern_norm = pattern.replace("\\", "/").rstrip("/")
        # Test : le chemin commence par le pattern (ex: "src/auth/" matche "src/auth/service.py")
        # OU le pattern est contenu comme segment complet (ex: "auth" dans "src/auth/utils")
        if normalized.startswith(pattern_norm + "/") or normalized.startswith(pattern_norm):
            if isinstance(mapped, list):
                modules.update(mapped)
            else:
                modules.add(str(mapped))

    # Niveau 2 : fallback par segments du chemin (fichiers exclus)
    if not modules:
        modules = {p.lower() for p in Path(filepath).parts if "." not in p}

    return modules


@mcp_app.tool()
def get_context_for_file(filepath: str) -> str:
    """Retourne les ADR pertinents pour un fichier ou chemin donné."""
    d, config, adrs = _get_ctx()

    # Résoudre le chemin en modules via config
    resolved_modules = _modules_for_file(filepath, config.get("module_mappings", {}))

    # Recherche par modules
    by_module = [
        a for a in adrs.values()
        if any(m.lower() in resolved_modules for m in a.modules)
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
