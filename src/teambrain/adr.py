from __future__ import annotations
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import frontmatter

logger = logging.getLogger(__name__)


@dataclass
class ADR:
    id: int
    titre: str
    date: date
    statut: str  # propose | accepte | deprecie | remplace
    modules: list[str]
    decideurs: list[str]
    contexte: str
    decision: str
    consequences: str
    path: Path | None = None


def slugify(text: str) -> str:
    text = text.lower()
    for src, dst in [
        ("àâäÀÂÄ", "a"), ("éèêëÉÈÊË", "e"), ("îïÎÏ", "i"),
        ("ôöÔÖ", "o"), ("ùûüÙÛÜ", "u"), ("çÇ", "c"), ("ñÑ", "n"),
    ]:
        for ch in src:
            text = text.replace(ch, dst)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:50]


def _filename(id: int, titre: str) -> str:
    return f"{id:03d}-{slugify(titre)}.md"


def _to_markdown(adr: ADR) -> str:
    post = frontmatter.Post(
        content=(
            f"## Contexte\n\n{adr.contexte}\n\n"
            f"## Décision\n\n{adr.decision}\n\n"
            f"## Conséquences\n\n{adr.consequences}\n"
        ),
        id=adr.id,
        titre=adr.titre,
        date=adr.date.isoformat(),
        statut=adr.statut,
        modules=adr.modules,
        decideurs=adr.decideurs,
    )
    return frontmatter.dumps(post)


def _extract_section(content: str, name: str) -> str:
    m = re.search(rf"## {name}\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    return m.group(1).strip() if m else ""


def from_post(post: frontmatter.Post, path: Path | None) -> ADR:
    raw_date = post.get("date", date.today().isoformat())
    parsed_date = date.fromisoformat(str(raw_date)) if isinstance(raw_date, str) else raw_date
    return ADR(
        id=int(post.get("id", 0)),
        titre=str(post.get("titre", "")),
        date=parsed_date,
        statut=str(post.get("statut", "propose")),
        modules=list(post.get("modules", [])),
        decideurs=list(post.get("decideurs", [])),
        contexte=_extract_section(post.content, "Contexte"),
        decision=_extract_section(post.content, "Décision"),
        consequences=_extract_section(post.content, "Conséquences"),
        path=path,
    )


def load_adr(path: Path) -> ADR:
    return from_post(frontmatter.load(str(path)), path)


def save_adr(adr: ADR, decisions_dir: Path) -> Path:
    decisions_dir.mkdir(exist_ok=True)
    path = decisions_dir / _filename(adr.id, adr.titre)
    path.write_text(_to_markdown(adr), encoding="utf-8")
    adr.path = path
    return path


def list_adrs(decisions_dir: Path) -> list[ADR]:
    if not decisions_dir.exists():
        return []
    adrs = []
    for p in sorted(decisions_dir.glob("[0-9]*.md")):
        try:
            adrs.append(load_adr(p))
        except Exception as exc:
            logger.warning("ADR ignoré (lecture échouée) : %s — %s", p, exc)
            continue
    return adrs


def delete_adr(adr_id: int, decisions_dir: Path) -> bool:
    for p in decisions_dir.glob(f"{adr_id:03d}-*.md"):
        p.unlink()
        return True
    return False


def next_id(decisions_dir: Path) -> int:
    existing = list_adrs(decisions_dir)
    return max((a.id for a in existing), default=0) + 1


@dataclass
class RequeteParsee:
    """Résultat du parsing d'une requête style GitHub."""
    statuts: list[str]
    modules: list[str]
    decideurs: list[str]
    projets: list[str]       # pour http_api.py : projet:X dans la query
    champs: list[str]        # in:titre / in:decision / in:contexte / in:consequences
    phrases: list[str]       # "phrase exacte"
    regexps: list[str]       # /pattern/
    termes: list[str]        # termes full-text positifs
    exclusions: list[str]    # -terme (exclusions)


def parse_query(query: str) -> RequeteParsee:
    """
    Parse une requête de recherche style GitHub Code Search.

    Syntaxe supportée :
      statut:accepte    — filtre par statut
      module:auth       — filtre par module
      decideur:alice    — filtre par décideur
      projet:teambrain  — filtre par projet
      in:titre          — restreindre full-text à un champ (titre|decision|contexte|consequences)
      "phrase exacte"   — correspondance de phrase
      /regex/           — expression régulière
      -terme            — exclure un terme
      terme             — recherche full-text
    """
    statuts: list[str] = []
    modules: list[str] = []
    decideurs: list[str] = []
    projets: list[str] = []
    champs: list[str] = []
    phrases: list[str] = []
    regexps: list[str] = []
    termes: list[str] = []
    exclusions: list[str] = []

    # 1. Extraire les phrases exactes ("...")
    for m in re.finditer(r'"([^"]+)"', query):
        phrases.append(m.group(1).lower())
    query = re.sub(r'"[^"]+"', " ", query)

    # 2. Extraire les expressions régulières (/.../)
    for m in re.finditer(r"/([^/]+)/", query):
        regexps.append(m.group(1))
    query = re.sub(r"/[^/]+/", " ", query)

    # 3. Extraire les qualificatifs field:value
    QUALS: dict[str, list[str]] = {
        "statut": statuts,
        "module": modules,
        "decideur": decideurs,
        "projet": projets,
        "in": champs,
    }
    for qual, lst in QUALS.items():
        for m in re.finditer(rf"\b{qual}:(\S+)", query, re.IGNORECASE):
            lst.append(m.group(1).lower())
        query = re.sub(rf"\b{qual}:\S+", " ", query, flags=re.IGNORECASE)

    # 4. Termes restants (ignorer AND/OR comme opérateurs)
    for token in query.split():
        if token.upper() in ("AND", "OR"):
            continue
        if token.startswith("-") and len(token) > 1:
            exclusions.append(token[1:].lower())
        else:
            termes.append(token.lower())

    return RequeteParsee(
        statuts=statuts,
        modules=modules,
        decideurs=decideurs,
        projets=projets,
        champs=champs,
        phrases=phrases,
        regexps=regexps,
        termes=termes,
        exclusions=exclusions,
    )


# Champs disponibles pour in:
_CHAMPS_DISPONIBLES = {"titre", "decision", "contexte", "consequences"}
_CHAMPS_ALIASES: dict[str, str] = {
    "décision": "decision",
    "conséquences": "consequences",
    "consequence": "consequences",
}


def _get_champs(adr: ADR, champs: list[str]) -> list[str]:
    """Retourne les valeurs des champs demandés par in:. Défaut : tous."""
    if not champs:
        return [adr.titre, adr.contexte, adr.decision, adr.consequences,
                " ".join(adr.modules), " ".join(adr.decideurs)]
    parts = []
    for c in champs:
        c = _CHAMPS_ALIASES.get(c, c)
        if c == "titre":
            parts.append(adr.titre)
        elif c == "decision":
            parts.append(adr.decision)
        elif c == "contexte":
            parts.append(adr.contexte)
        elif c == "consequences":
            parts.append(adr.consequences)
    return parts


def search_adrs(
    query: str, decisions_dir: Path, req: RequeteParsee | None = None
) -> list[tuple[ADR, float]]:
    """
    Recherche avec syntaxe GitHub-style.
    Si `req` est fourni (déjà parsé par http_api pour extraire projet:),
    on l'utilise directement sans re-parser.
    """
    if req is None:
        req = parse_query(query)

    results: list[tuple[ADR, float]] = []

    for adr in list_adrs(decisions_dir):

        # ── Filtres stricts (éliminatoires) ──────────────────────────────────

        if req.statuts and adr.statut.lower() not in req.statuts:
            continue

        if req.modules:
            adr_modules_lower = [m.lower() for m in adr.modules]
            if not any(m in adr_modules_lower for m in req.modules):
                continue

        if req.decideurs:
            adr_decideurs_lower = [d.lower() for d in adr.decideurs]
            if not any(d in " ".join(adr_decideurs_lower) for d in req.decideurs):
                continue

        # ── Score full-text ───────────────────────────────────────────────────

        haystack_parts = _get_champs(adr, req.champs)
        haystack = " ".join(haystack_parts).lower()

        # Exclusions : si un terme exclu est présent → éliminé
        if any(ex in haystack for ex in req.exclusions):
            continue

        score = 0.0
        total_criteres = len(req.termes) + len(req.phrases) + len(req.regexps)

        if total_criteres == 0:
            # Requête purement à qualificatifs : score 1.0 si les filtres passent
            score = 1.0
        else:
            # Termes simples
            for terme in req.termes:
                if terme in haystack:
                    # Bonus si dans le titre
                    if terme in adr.titre.lower():
                        score += 1.5
                    else:
                        score += 1.0

            # Phrases exactes
            for phrase in req.phrases:
                if phrase in haystack:
                    score += 2.0

            # Expressions régulières
            for pattern in req.regexps:
                try:
                    if re.search(pattern, haystack, re.IGNORECASE):
                        score += 2.0
                except re.error:
                    if pattern in haystack:
                        score += 1.0

            if score == 0:
                continue
            # Normaliser sur le nombre de critères (bonus titre pouvant dépasser 1.0)
            score = min(score / total_criteres, 1.0)

        results.append((adr, round(score, 3)))

    return sorted(results, key=lambda x: x[1], reverse=True)
