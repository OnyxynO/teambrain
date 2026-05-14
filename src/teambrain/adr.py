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


def next_id(decisions_dir: Path) -> int:
    existing = list_adrs(decisions_dir)
    return max((a.id for a in existing), default=0) + 1


def search_adrs(query: str, decisions_dir: Path) -> list[tuple[ADR, float]]:
    """Recherche texte simple — Module 1. Module 2 apportera sqlite-vec."""
    words = query.lower().split()
    if not words:
        return []
    results = []
    for adr in list_adrs(decisions_dir):
        haystack = " ".join([
            adr.titre, adr.contexte, adr.decision, adr.consequences,
            " ".join(adr.modules),
        ]).lower()
        score = sum(1 for w in words if w in haystack) / len(words)
        if score > 0:
            results.append((adr, score))
    return sorted(results, key=lambda x: x[1], reverse=True)
