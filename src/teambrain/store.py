from __future__ import annotations
import sqlite3
import struct
from pathlib import Path
from typing import Callable

import ollama
import sqlite_vec

from .adr import ADR, list_adrs

_DEFAULT_EMBED_MODEL = "qwen3-embedding:0.6b"
_DB_FILENAME = "teambrain.db"


def _pack(v: list[float]) -> bytes:
    return struct.pack(f"{len(v)}f", *v)


def _default_embed(text: str, model: str) -> list[float]:
    r = ollama.embed(model=model, input=text)
    return r.embeddings[0]


def _open_db(db_path: Path, dim: int) -> sqlite3.Connection:
    db = sqlite3.connect(str(db_path))
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS adr_vecs USING vec0(embedding float[{dim}])")
    db.commit()
    return db


def _adr_text(adr: ADR) -> str:
    return f"{adr.titre}\n{adr.contexte}\n{adr.decision}\n{adr.consequences}"


def reindex(
    decisions_dir: Path,
    config: dict,
    embed_fn: Callable[[str], list[float]] | None = None,
) -> int:
    """Réindexe tous les ADR. Retourne le nombre d'ADR indexés."""
    adrs = list_adrs(decisions_dir)
    if not adrs:
        return 0

    model = config.get("embedding_model", _DEFAULT_EMBED_MODEL)
    embed = embed_fn or (lambda t: _default_embed(t, model))

    vecs = [embed(_adr_text(a)) for a in adrs]
    dim = len(vecs[0])

    db_path = decisions_dir / _DB_FILENAME
    # Recrée le fichier si la dimension a changé ou pour un reindex complet
    if db_path.exists():
        db_path.unlink()

    db = _open_db(db_path, dim)
    try:
        db.executemany(
            "INSERT INTO adr_vecs(rowid, embedding) VALUES (?, ?)",
            [(a.id, _pack(v)) for a, v in zip(adrs, vecs)],
        )
        db.commit()
    finally:
        db.close()
    return len(adrs)


def search_semantic(
    query: str,
    decisions_dir: Path,
    config: dict,
    k: int = 5,
    embed_fn: Callable[[str], list[float]] | None = None,
) -> list[tuple[int, float]]:
    """Retourne [(adr_id, distance), ...] triés par distance croissante. [] si pas d'index."""
    db_path = decisions_dir / _DB_FILENAME
    if not db_path.exists():
        return []

    model = config.get("embedding_model", _DEFAULT_EMBED_MODEL)
    embed = embed_fn or (lambda t: _default_embed(t, model))
    vec = embed(query)

    db = sqlite3.connect(str(db_path))
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    try:
        rows = db.execute(
            "SELECT rowid, distance FROM adr_vecs WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (_pack(vec), k),
        ).fetchall()
    finally:
        db.close()
    return [(int(r[0]), float(r[1])) for r in rows]
