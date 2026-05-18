"""Tests — Module 4 : scanner.py (git/code mining)."""
from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from teambrain.scanner import (
    _depuis_vers_git,
    score_candidat,
    scanner_commits,
    scanner_code,
    scanner_commits_semantique,
)


# ──────────────────────────────────────────────────────────────
# _depuis_vers_git
# ──────────────────────────────────────────────────────────────

def test_depuis_semaine():
    assert _depuis_vers_git("1w") == "1 week ago"


def test_depuis_semaines_pluriel():
    assert _depuis_vers_git("2w") == "2 weeks ago"


def test_depuis_mois_singulier():
    assert _depuis_vers_git("1m") == "1 month ago"


def test_depuis_mois_pluriel():
    assert _depuis_vers_git("3m") == "3 months ago"


def test_depuis_six_mois():
    assert _depuis_vers_git("6m") == "6 months ago"


def test_depuis_annee_singulier():
    assert _depuis_vers_git("1y") == "1 year ago"


def test_depuis_annee_pluriel():
    assert _depuis_vers_git("2y") == "2 years ago"


def test_depuis_date_directe():
    """Une date ISO est retournée telle quelle."""
    assert _depuis_vers_git("2026-01-01") == "2026-01-01"


def test_depuis_valeur_inconnue():
    """Une valeur non reconnue est retournée sans modification."""
    assert _depuis_vers_git("yesterday") == "yesterday"


# ──────────────────────────────────────────────────────────────
# score_candidat
# ──────────────────────────────────────────────────────────────

def _mock_ollama_response(contenu: str) -> MagicMock:
    """Crée un faux objet réponse Ollama."""
    response = MagicMock()
    response.message.content = contenu
    return response


def test_score_json_propre():
    """JSON propre retourné directement par Ollama → parsing correct."""
    contenu_json = '{"est_decision": true, "confiance": 0.9, "resume": "Choix de PostgreSQL"}'
    with patch("teambrain.scanner.ollama.chat", return_value=_mock_ollama_response(contenu_json)):
        resultat = score_candidat("On a décidé d'utiliser PostgreSQL", "qwen3:1.7b")

    assert resultat["est_decision"] is True
    assert resultat["confiance"] == pytest.approx(0.9)
    assert resultat["resume"] == "Choix de PostgreSQL"


def test_score_json_enveloppe_markdown():
    """JSON enveloppé dans ```json ... ``` → nettoyage fonctionne."""
    contenu_enveloppe = (
        "```json\n"
        '{"est_decision": true, "confiance": 0.85, "resume": "Migration vers Redis"}\n'
        "```"
    )
    with patch("teambrain.scanner.ollama.chat", return_value=_mock_ollama_response(contenu_enveloppe)):
        resultat = score_candidat("On migre le cache vers Redis", "qwen3:1.7b")

    assert resultat["est_decision"] is True
    assert resultat["confiance"] == pytest.approx(0.85)
    assert resultat["resume"] == "Migration vers Redis"


def test_score_json_malformed_leve_erreur():
    """JSON malformé irrécupérable → ValueError levée."""
    contenu_invalide = "Ceci n'est pas du JSON valide {{"
    with patch("teambrain.scanner.ollama.chat", return_value=_mock_ollama_response(contenu_invalide)):
        with pytest.raises(ValueError, match="malformée"):
            score_candidat("Un texte quelconque", "qwen3:1.7b")


def test_score_retourne_dict_normalise():
    """Les valeurs sont normalisées (bool, float, str) même si le modèle envoie des types inhabituels."""
    contenu_json = '{"est_decision": 1, "confiance": "0.7", "resume": 42}'
    with patch("teambrain.scanner.ollama.chat", return_value=_mock_ollama_response(contenu_json)):
        resultat = score_candidat("Texte test", "qwen3:1.7b")

    assert isinstance(resultat["est_decision"], bool)
    assert isinstance(resultat["confiance"], float)
    assert isinstance(resultat["resume"], str)


# ──────────────────────────────────────────────────────────────
# scanner_commits
# ──────────────────────────────────────────────────────────────

LOG_GIT_SIMULE = (
    "abc12345\t2026-05-01\tAlice Dupont\ton a décidé d'utiliser PostgreSQL pour la persistance\n"
    "def67890\t2026-05-02\tBob Martin\tfix typo dans le README\n"
)


def _mock_score_decision(texte, model, semanticmatch_url=None):
    return {"est_decision": True, "confiance": 0.9, "resume": "Choix de PostgreSQL"}


def _mock_score_pas_decision(texte, model, semanticmatch_url=None):
    return {"est_decision": False, "confiance": 0.2, "resume": ""}


def test_scanner_commits_retient_decisionnels():
    """Un commit décisionnel est retenu, un non-décisionnel est exclu."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = LOG_GIT_SIMULE

    with patch("teambrain.scanner.subprocess.run", return_value=mock_run), \
         patch("teambrain.scanner.score_candidat", side_effect=_mock_score_decision):
        candidats = scanner_commits(Path("/fake/repo"), "1w", "qwen3:1.7b", 0.7)

    # Seul le commit "on a décidé" matche le pattern, l'autre est filtré avant scoring
    assert len(candidats) == 1
    assert candidats[0].source == "commit"
    assert candidats[0].ref == "abc12345"
    assert candidats[0].auteur == "Alice Dupont"
    assert candidats[0].date_commit == date(2026, 5, 1)


def test_scanner_commits_exclut_sous_seuil():
    """Un commit qui passe le pattern mais a une confiance insuffisante est exclu."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "abc12345\t2026-05-01\tAlice\ton a décidé quelque chose\n"

    score_bas = {"est_decision": True, "confiance": 0.4, "resume": "Faible confiance"}
    with patch("teambrain.scanner.subprocess.run", return_value=mock_run), \
         patch("teambrain.scanner.score_candidat", return_value=score_bas):
        candidats = scanner_commits(Path("/fake/repo"), "1w", "qwen3:1.7b", 0.7)

    assert candidats == []


def test_scanner_commits_exclut_si_pas_decision():
    """Un commit qui passe le pattern mais que l'IA juge non-décisionnel est exclu."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "abc12345\t2026-05-01\tAlice\ton a décidé quelque chose\n"
    with patch("teambrain.scanner.subprocess.run", return_value=mock_run), \
         patch("teambrain.scanner.score_candidat", side_effect=_mock_score_pas_decision):
        candidats = scanner_commits(Path("/fake/repo"), "1w", "qwen3:1.7b", 0.7)
    assert candidats == []


def test_scanner_commits_patterns_extra():
    """Un pattern supplémentaire détecte des commits qui ne matchent pas les patterns par défaut."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "abc12345\t2026-05-01\tAlice\tmigrer arborescence vers ltree PostgreSQL\n"

    with patch("teambrain.scanner.subprocess.run", return_value=mock_run), \
         patch("teambrain.scanner.score_candidat", side_effect=_mock_score_decision):
        # Sans pattern extra → aucun match (les patterns par défaut ne contiennent pas "migrer")
        sans_extra = scanner_commits(Path("/fake/repo"), "1w", "qwen3:1.7b", 0.7)
        # Avec pattern extra → match
        avec_extra = scanner_commits(Path("/fake/repo"), "1w", "qwen3:1.7b", 0.7, patterns_extra=["migrer"])

    assert sans_extra == []
    assert len(avec_extra) == 1
    assert avec_extra[0].ref == "abc12345"


def test_scanner_commits_erreur_git_leve_runtime():
    """Si git log échoue (returncode != 0), RuntimeError est levée."""
    mock_run = MagicMock()
    mock_run.returncode = 128
    mock_run.stderr = "fatal: not a git repository"

    with patch("teambrain.scanner.subprocess.run", return_value=mock_run):
        with pytest.raises(RuntimeError, match="git log"):
            scanner_commits(Path("/fake/repo"), "1w", "qwen3:1.7b", 0.7)


# ──────────────────────────────────────────────────────────────
# scanner_code
# ──────────────────────────────────────────────────────────────

def test_scanner_code_retient_marqueur_decision():
    """Un fichier contenant 'DECISION:' est détecté, un fichier sans marqueur est ignoré."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "service.py").write_text(
            "# DECISION: utiliser SQLite pour le stockage local\ndef connect(): pass\n",
            encoding="utf-8",
        )
        (repo / "utils.py").write_text(
            "def helper():\n    return 42\n",
            encoding="utf-8",
        )

        score_ok = {"est_decision": True, "confiance": 0.9, "resume": "SQLite pour stockage local"}
        with patch("teambrain.scanner.score_candidat", return_value=score_ok):
            candidats = scanner_code(repo, confiance_min=0.8)

    assert len(candidats) == 1
    assert "service.py" in candidats[0].ref
    assert candidats[0].source == "code"


def test_scanner_code_ignore_dossier_git():
    """Les fichiers dans .git/ sont ignorés."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git_dir = repo / ".git"
        git_dir.mkdir()
        (git_dir / "COMMIT_EDITMSG").write_text("DECISION: test interne git\n", encoding="utf-8")

        score_ok = {"est_decision": True, "confiance": 0.95, "resume": "Test"}
        with patch("teambrain.scanner.score_candidat", return_value=score_ok):
            candidats = scanner_code(repo, confiance_min=0.8)

    assert candidats == []


def test_scanner_code_ignore_binaire():
    """Un fichier binaire est ignoré sans lever d'erreur."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        # Fichier binaire (contient des octets nuls)
        (repo / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00DECISION:\x00data")
        (repo / "normal.py").write_text("# Aucun marqueur ici\n", encoding="utf-8")

        with patch("teambrain.scanner.score_candidat") as mock_score:
            candidats = scanner_code(repo, confiance_min=0.8)

        # score_candidat ne doit jamais être appelé pour le fichier binaire
        mock_score.assert_not_called()
        assert candidats == []


def test_scanner_code_seuil_confiance():
    """Un marqueur détecté mais avec confiance insuffisante est exclu."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "app.py").write_text("# ADR: choisir le framework\n", encoding="utf-8")

        score_bas = {"est_decision": True, "confiance": 0.5, "resume": "Framework"}
        with patch("teambrain.scanner.score_candidat", return_value=score_bas):
            candidats = scanner_code(repo, confiance_min=0.8)

    assert candidats == []


def test_scanner_code_patterns_extra():
    """Les patterns supplémentaires s'ajoutent aux patterns par défaut."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "config.py").write_text(
            "# CHOIX_ARCHI: microservices plutôt que monolithe\n",
            encoding="utf-8",
        )

        score_ok = {"est_decision": True, "confiance": 0.88, "resume": "Microservices"}
        with patch("teambrain.scanner.score_candidat", return_value=score_ok):
            candidats = scanner_code(repo, patterns_extra=["CHOIX_ARCHI:"], confiance_min=0.8)

    assert len(candidats) == 1
    assert "config.py" in candidats[0].ref


# ──────────────────────────────────────────────────────────────
# scanner_commits_semantique (Module 5)
# ──────────────────────────────────────────────────────────────

LOG_GIT_SEMANTIQUE = (
    "aaa11111\t2026-05-10\tAlice Dupont\tchoisir sqlite-vec pour l'index vectoriel local\n"
    "bbb22222\t2026-05-11\tBob Martin\tfix: corriger le padding du bouton principal\n"
)


def test_scanner_semantique_retient_proche():
    """Un commit dont la distance à un ADR est <= seuil est retenu avec adr_lie et confiance corrects."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = LOG_GIT_SEMANTIQUE

    # search_semantic retourne [(adr_id=3, distance=0.2)] pour le premier commit,
    # puis [(adr_id=3, distance=0.2)] pour le second — les deux sont proches
    # mais on vérifie surtout les valeurs calculées
    with patch("teambrain.scanner.subprocess.run", return_value=mock_run), \
         patch("teambrain.scanner.search_semantic", return_value=[(3, 0.2)]), \
         patch("teambrain.scanner.Path.exists", return_value=True):
        candidats = scanner_commits_semantique(
            Path("/fake/repo"),
            Path("/fake/repo/.decisions"),
            {},
            depuis="1w",
            seuil_distance=0.3,
        )

    # Les deux commits passent le seuil 0.3 (distance 0.2 <= 0.3)
    assert len(candidats) == 2
    assert candidats[0].adr_lie == 3
    assert candidats[0].confiance == pytest.approx(0.8)
    assert candidats[0].ref == "aaa11111"
    assert candidats[0].source == "commit"
    assert "ADR #3" in candidats[0].resume
    assert "0.200" in candidats[0].resume


def test_scanner_semantique_exclut_distant():
    """Un commit dont la distance dépasse le seuil est exclu."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "aaa11111\t2026-05-10\tAlice\tchoisir sqlite-vec\n"

    with patch("teambrain.scanner.subprocess.run", return_value=mock_run), \
         patch("teambrain.scanner.search_semantic", return_value=[(3, 0.8)]), \
         patch("teambrain.scanner.Path.exists", return_value=True):
        candidats = scanner_commits_semantique(
            Path("/fake/repo"),
            Path("/fake/repo/.decisions"),
            {},
            depuis="1w",
            seuil_distance=0.3,
        )

    assert candidats == []


def test_scanner_semantique_index_absent(tmp_path):
    """Si le fichier teambrain.db est absent, RuntimeError est levée avant la boucle."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "aaa11111\t2026-05-10\tAlice\tchoisir sqlite-vec\n"

    # tmp_path est un répertoire vide — pas de teambrain.db dedans
    with patch("teambrain.scanner.subprocess.run", return_value=mock_run):
        with pytest.raises(RuntimeError, match="Index absent"):
            scanner_commits_semantique(
                tmp_path,
                tmp_path,  # decisions_dir sans teambrain.db
                {},
            )


def test_scanner_semantique_no_commits():
    """Si git log ne retourne aucune ligne non vide, la liste est vide sans erreur."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "\n   \n"  # lignes vides uniquement

    with patch("teambrain.scanner.subprocess.run", return_value=mock_run), \
         patch("teambrain.scanner.search_semantic") as mock_search, \
         patch("teambrain.scanner.Path.exists", return_value=True):
        candidats = scanner_commits_semantique(
            Path("/fake/repo"),
            Path("/fake/repo/.decisions"),
            {},
        )

    # Aucun commit → search_semantic jamais appelé, liste vide, pas d'erreur
    mock_search.assert_not_called()
    assert candidats == []
