"""Module 4 — Git/Code Mining avec filtrage IA.

Scanne les commits git et les commentaires de code pour détecter
des décisions architecturales non documentées.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Literal

import ollama

from . import semanticmatch as sm
from .store import search_semantic

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Modèle de données
# ──────────────────────────────────────────────────────────────

@dataclass
class Candidat:
    """Un candidat de décision détecté dans les commits ou le code."""
    source: Literal["commit", "code"]
    ref: str                        # hash de commit ou "fichier:ligne"
    texte: str
    resume: str = ""
    confiance: float = 0.0
    date_commit: date | None = None
    auteur: str | None = None
    adr_lie: int | None = None      # ID de l'ADR le plus proche (mode sémantique)


# ──────────────────────────────────────────────────────────────
# Patterns par défaut
# ──────────────────────────────────────────────────────────────

PATTERNS_COMMIT = [
    "on a décidé",
    "on va partir sur",
    "on abandonne",
    "décision :",
    "DECISION:",
    "ADR:",
    "on choisit",
    "we decided",
    "decided to",
]

PATTERNS_CODE = [
    "DECISION:",
    "ADR:",
    "# decision",
    "// decision",
]

# Dossiers à ignorer lors du scan de code
DOSSIERS_IGNORES = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", "dist", "build"}

# ──────────────────────────────────────────────────────────────
# Conversion de la durée en format git
# ──────────────────────────────────────────────────────────────

def _match_patterns(texte: str, patterns: list[str]) -> bool:
    """Retourne True si au moins un pattern matche le texte (regex ou sous-chaîne)."""
    texte_lower = texte.lower()
    for p in patterns:
        try:
            if re.search(p, texte_lower, re.IGNORECASE):
                return True
        except re.error:
            if p.lower() in texte_lower:
                return True
    return False


def _depuis_vers_git(depuis: str) -> str:
    """Convertit un raccourci de durée vers le format git --since.

    Exemples :
        "1w" → "1 week ago"
        "3m" → "3 months ago"
        "1y" → "1 year ago"
        "2026-01-01" → "2026-01-01"  (retourné tel quel)
    """
    correspondance = re.fullmatch(r"(\d+)([wmy])", depuis)
    if not correspondance:
        # date directe ou valeur non reconnue → on laisse git gérer
        return depuis
    n, unite = correspondance.group(1), correspondance.group(2)
    noms = {"w": ("week", "weeks"), "m": ("month", "months"), "y": ("year", "years")}
    singulier, pluriel = noms[unite]
    mot = singulier if n == "1" else pluriel
    return f"{n} {mot} ago"


# ──────────────────────────────────────────────────────────────
# Scoring IA
# ──────────────────────────────────────────────────────────────

_SYSTEM_SCORE = """Tu es un expert en Architecture Decision Records (ADR).
Analyse le texte suivant et détermine s'il décrit une décision architecturale.
Réponds uniquement avec un objet JSON valide, sans markdown ni explication."""

_USER_SCORE_SUFFIX = """

Réponds avec exactement ce JSON :
{
  "est_decision": true ou false,
  "confiance": nombre entre 0.0 et 1.0,
  "resume": "résumé de la décision en une phrase, ou chaîne vide si pas une décision"
}"""


def score_candidat(texte: str, model: str, semanticmatch_url: str | None = None) -> dict:
    """Évalue si le texte contient une décision architecturale.

    Utilise SemanticMatch (Haiku) si `semanticmatch_url` est fourni, sinon Ollama.

    Retourne un dict avec les clés : est_decision (bool), confiance (float), resume (str).
    Lève ValueError ou ConnectionError en cas d'erreur irrécupérable.
    """
    if semanticmatch_url:
        return sm.classifier(texte[:500], semanticmatch_url)

    texte_tronque = texte[:500]
    user_content = f"Texte à analyser (limité à 500 caractères) :\n{texte_tronque}" + _USER_SCORE_SUFFIX
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_SCORE},
            {"role": "user", "content": user_content},
        ],
        options={"temperature": 0.1},
    )
    content = response.message.content.strip()

    # Gestion du wrapping ```json que certains modèles ajoutent malgré le prompt
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    try:
        resultat = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Réponse JSON malformée : {exc}\nContenu : {content!r}") from exc

    return {
        "est_decision": bool(resultat.get("est_decision", False)),
        "confiance": float(resultat.get("confiance", 0.0)),
        "resume": str(resultat.get("resume", "")),
    }


# ──────────────────────────────────────────────────────────────
# Scanner de commits
# ──────────────────────────────────────────────────────────────

def scanner_commits(
    chemin_repo: Path,
    depuis: str = "1w",
    model: str = "qwen3:1.7b",
    confiance_min: float = 0.7,
    score_ia: bool = True,
    patterns_extra: list[str] | None = None,
    semanticmatch_url: str | None = None,
) -> list[Candidat]:
    """Scanne les commits git depuis `depuis` et retourne les candidats décisionnels.

    Args:
        chemin_repo: Racine du dépôt git.
        depuis: Durée ou date ("1w", "3m", "1y", "2026-01-01"…).
        model: Modèle Ollama pour le scoring.
        confiance_min: Seuil de confiance minimum (0-1).
        score_ia: Si False, retourne les candidats bruts sans appeler Ollama.
        patterns_extra: Patterns supplémentaires (s'ajoutent aux défauts).

    Returns:
        Liste de Candidat filtrés au-dessus du seuil.
    """
    patterns = PATTERNS_COMMIT + (patterns_extra or [])
    since = _depuis_vers_git(depuis)
    # Format : hash<TAB>date ISO<TAB>auteur<TAB>sujet
    git_format = "%H\t%as\t%an\t%s"
    resultat = subprocess.run(
        ["git", "log", f"--since={since}", f"--format={git_format}"],
        cwd=chemin_repo,
        capture_output=True,
        text=True,
    )
    if resultat.returncode != 0:
        raise RuntimeError(f"Erreur git log : {resultat.stderr.strip()}")

    lignes = [ligne for ligne in resultat.stdout.splitlines() if ligne.strip()]
    candidats: list[Candidat] = []

    for ligne in lignes:
        parties = ligne.split("\t", 3)
        if len(parties) < 4:
            continue
        hash_commit, date_str, auteur, sujet = parties

        # Filtrage rapide par patterns (regex ou sous-chaîne)
        if not _match_patterns(sujet, patterns):
            continue

        try:
            date_obj = date.fromisoformat(date_str)
        except ValueError:
            date_obj = None

        # Mode brut : pas de scoring IA
        if not score_ia:
            candidats.append(Candidat(
                source="commit",
                ref=hash_commit[:8],
                texte=sujet,
                resume="",
                confiance=1.0,
                date_commit=date_obj,
                auteur=auteur or None,
            ))
            continue

        # Scoring IA
        ref = hash_commit[:8]
        try:
            score = score_candidat(sujet, model, semanticmatch_url)
        except (ValueError, ollama.ResponseError, ConnectionError) as exc:
            logger.warning(f"Score ignoré pour '{ref}' : {exc}")
            continue

        if not score["est_decision"] or score["confiance"] < confiance_min:
            continue

        candidats.append(Candidat(
            source="commit",
            ref=ref,
            texte=sujet,
            resume=score["resume"],
            confiance=score["confiance"],
            date_commit=date_obj,
            auteur=auteur or None,
        ))

    return candidats


# ──────────────────────────────────────────────────────────────
# Scanner de code
# ──────────────────────────────────────────────────────────────

def _est_binaire(chemin: Path) -> bool:
    """Détecte les fichiers binaires en lisant les 8 premiers Ko."""
    try:
        contenu = chemin.read_bytes()[:8192]
        return b"\x00" in contenu
    except OSError:
        return True


def scanner_code(
    chemin_repo: Path,
    patterns_extra: list[str] | None = None,
    model: str = "qwen3:1.7b",
    confiance_min: float = 0.8,
    score_ia: bool = True,
    max_candidats: int = 200,
    semanticmatch_url: str | None = None,
) -> list[Candidat]:
    """Scanne les fichiers texte du repo à la recherche de marqueurs décisionnels.

    Args:
        chemin_repo: Racine du dépôt.
        patterns_extra: Patterns supplémentaires à chercher (s'ajoutent aux défauts).
        model: Modèle Ollama pour le scoring.
        confiance_min: Seuil de confiance minimum (0-1).
        score_ia: Si False, retourne les candidats bruts sans appeler Ollama.

    Returns:
        Liste de Candidat filtrés au-dessus du seuil.
    """
    patterns = PATTERNS_CODE + (patterns_extra or [])
    candidats: list[Candidat] = []

    for fichier in chemin_repo.rglob("*"):
        if max_candidats and len(candidats) >= max_candidats:
            logger.warning("Limite de %d candidats atteinte — scan arrêté.", max_candidats)
            break
        # Ignorer les dossiers et les chemins à exclure
        if not fichier.is_file():
            continue
        parties_chemin = set(fichier.relative_to(chemin_repo).parts)
        if parties_chemin & DOSSIERS_IGNORES:
            continue
        if _est_binaire(fichier):
            continue

        try:
            lignes = fichier.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for num_ligne, ligne in enumerate(lignes, start=1):
            if max_candidats and len(candidats) >= max_candidats:
                break
            if not _match_patterns(ligne, patterns):
                continue

            ref = f"{fichier.relative_to(chemin_repo)}:{num_ligne}"
            texte = ligne.strip()

            # Mode brut : pas de scoring IA
            if not score_ia:
                candidats.append(Candidat(
                    source="code",
                    ref=ref,
                    texte=texte,
                    resume="",
                    confiance=1.0,
                    date_commit=None,
                    auteur=None,
                ))
                continue

            # Scoring IA
            try:
                score = score_candidat(texte, model, semanticmatch_url)
            except (ValueError, ollama.ResponseError, ConnectionError) as exc:
                logger.warning(f"Score ignoré pour '{ref}' : {exc}")
                continue

            if not score["est_decision"] or score["confiance"] < confiance_min:
                continue

            candidats.append(Candidat(
                source="code",
                ref=ref,
                texte=texte,
                resume=score["resume"],
                confiance=score["confiance"],
                date_commit=None,
                auteur=None,
            ))

    return candidats


# ──────────────────────────────────────────────────────────────
# Scanner sémantique (Module 5)
# ──────────────────────────────────────────────────────────────

def scanner_commits_semantique(
    chemin_repo: Path,
    decisions_dir: Path,
    config: dict,
    depuis: str = "1w",
    seuil_distance: float = 0.3,
    embed_fn: Callable[[str], list[float]] | None = None,
) -> list[Candidat]:
    """Scanne les commits git par similarité sémantique avec l'index ADR existant.

    Au lieu de comparer sur des patterns regex, chaque commit est comparé
    directement à l'index sqlite-vec via les embeddings Ollama.

    Args:
        chemin_repo: Racine du dépôt git.
        decisions_dir: Répertoire .decisions/ contenant l'index vectoriel.
        config: Configuration du repo (embedding_model, etc.).
        depuis: Durée ou date de début ("1w", "3m", "2026-01-01"…).
        seuil_distance: Distance cosinus maximale (métrique configurée dans store.py)
            pour retenir un candidat (0-1). Une distance faible signifie une forte
            similarité. Défaut : 0.3 (calibrage cosine — 0=identique, 1=orthogonal).
        embed_fn: Fonction d'embedding personnalisée (utile pour les tests).

    Returns:
        Liste de Candidat dont la distance avec un ADR est <= seuil_distance.

    Raises:
        RuntimeError: Si git log échoue ou si l'index ADR est absent.
    """
    since = _depuis_vers_git(depuis)
    # Format identique à scanner_commits : hash<TAB>date ISO<TAB>auteur<TAB>sujet
    git_format = "%H\t%as\t%an\t%s"
    resultat_git = subprocess.run(
        ["git", "log", f"--since={since}", f"--format={git_format}"],
        cwd=chemin_repo,
        capture_output=True,
        text=True,
    )
    if resultat_git.returncode != 0:
        raise RuntimeError(f"Erreur git log : {resultat_git.stderr.strip()}")

    lignes = [ligne for ligne in resultat_git.stdout.splitlines() if ligne.strip()]
    candidats: list[Candidat] = []

    # Vérification explicite de la présence du fichier DB avant de démarrer la boucle
    db_path = decisions_dir / "teambrain.db"
    if not db_path.exists():
        raise RuntimeError("Index absent — lancer 'teambrain index' d'abord")

    for ligne in lignes:
        parties = ligne.split("\t", 3)
        if len(parties) < 4:
            continue
        hash_commit, date_str, auteur, sujet = parties

        # Recherche sémantique dans l'index ADR
        voisins = search_semantic(sujet, decisions_dir, config, k=1, embed_fn=embed_fn)

        # L'index peut ne retourner aucun voisin pour ce commit en particulier — ce n'est pas une erreur
        if not voisins:
            continue

        adr_id, distance = voisins[0]

        # Filtrage par seuil de distance : distance faible = commits proches sémantiquement
        if distance > seuil_distance:
            continue

        try:
            date_obj = date.fromisoformat(date_str)
        except ValueError:
            date_obj = None

        # La confiance est l'inverse de la distance, normalisée entre 0 et 1
        confiance = max(0.0, min(1.0, 1.0 - distance))

        candidats.append(Candidat(
            source="commit",
            ref=hash_commit[:8],
            texte=sujet,
            resume=f"Proche de l'ADR #{adr_id} (distance : {distance:.3f})",
            confiance=confiance,
            date_commit=date_obj,
            auteur=auteur or None,
            adr_lie=adr_id,
        ))

    return candidats
