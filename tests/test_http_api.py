from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from teambrain.adr import ADR, save_adr
from teambrain.http_api import create_app


@pytest.fixture
def decisions_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".decisions"
    d.mkdir()
    return d


@pytest.fixture
def client(decisions_dir: Path) -> TestClient:
    return TestClient(create_app(decisions_dir))


@pytest.fixture
def adr_exemple(decisions_dir: Path) -> ADR:
    adr = ADR(
        id=1,
        titre="Utiliser FastAPI pour l'API REST",
        date=date(2026, 5, 20),
        statut="accepte",
        modules=["api"],
        decideurs=["alice"],
        contexte="Besoin d'une API HTTP pour le frontend.",
        decision="On utilise FastAPI + uvicorn.",
        consequences="Dépendance fastapi. Nécessite Python 3.13.",
    )
    save_adr(adr, decisions_dir)
    return adr


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_ok(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_contient_decisions_dir(self, client: TestClient, decisions_dir: Path):
        r = client.get("/health")
        assert str(decisions_dir) in r.json()["decisions_dir"]


# ── Référentiels ──────────────────────────────────────────────────────────────

class TestReferentiels:
    def test_sans_adrs(self, client: TestClient):
        r = client.get("/referentiels")
        assert r.status_code == 200
        data = r.json()
        assert data["modules"] == []
        assert "accepte" in data["statuts"]

    def test_avec_adrs(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/referentiels")
        assert r.status_code == 200
        assert "api" in r.json()["modules"]

    def test_modules_tries(self, client: TestClient, decisions_dir: Path):
        for i, module in enumerate(["zz", "aa", "mm"], start=1):
            save_adr(ADR(id=i, titre=f"ADR {i}", date=date.today(), statut="propose",
                         modules=[module], decideurs=[], contexte="", decision="", consequences=""),
                     decisions_dir)
        r = client.get("/referentiels")
        modules = r.json()["modules"]
        assert modules == sorted(modules)


# ── Liste ADR ─────────────────────────────────────────────────────────────────

class TestListeADR:
    def test_vide(self, client: TestClient):
        r = client.get("/adr")
        assert r.status_code == 200
        assert r.json() == []

    def test_retourne_adr(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["titre"] == "Utiliser FastAPI pour l'API REST"
        assert data[0]["statut"] == "accepte"
        assert data[0]["modules"] == ["api"]

    def test_filtre_statut_match(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr?statut=accepte")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_filtre_statut_sans_resultat(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr?statut=propose")
        assert r.status_code == 200
        assert r.json() == []

    def test_filtre_module_match(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr?module=api")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_filtre_module_sans_resultat(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr?module=frontend")
        assert r.status_code == 200
        assert r.json() == []

    def test_filtre_cumule(self, client: TestClient, decisions_dir: Path):
        save_adr(ADR(id=1, titre="A", date=date.today(), statut="accepte",
                     modules=["api"], decideurs=[], contexte="", decision="", consequences=""),
                 decisions_dir)
        save_adr(ADR(id=2, titre="B", date=date.today(), statut="propose",
                     modules=["api"], decideurs=[], contexte="", decision="", consequences=""),
                 decisions_dir)
        r = client.get("/adr?statut=accepte&module=api")
        assert len(r.json()) == 1
        assert r.json()[0]["titre"] == "A"


# ── Détail ADR ────────────────────────────────────────────────────────────────

class TestDetailADR:
    def test_existant(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr/1")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 1
        assert data["contexte"] == "Besoin d'une API HTTP pour le frontend."

    def test_introuvable(self, client: TestClient):
        r = client.get("/adr/999")
        assert r.status_code == 404


# ── Création ADR ──────────────────────────────────────────────────────────────

class TestCreerADR:
    def test_creation_minimale(self, client: TestClient, decisions_dir: Path):
        r = client.post("/adr", json={"titre": "Nouvelle décision"})
        assert r.status_code == 201
        data = r.json()
        assert data["id"] == 1
        assert data["titre"] == "Nouvelle décision"
        assert data["statut"] == "propose"
        assert len(list(decisions_dir.glob("*.md"))) == 1

    def test_creation_complete(self, client: TestClient):
        payload = {
            "titre": "Choisir SQLite",
            "statut": "accepte",
            "modules": ["data", "core"],
            "decideurs": ["alice", "bob"],
            "contexte": "On a besoin d'une BDD légère.",
            "decision": "SQLite via sqlite-vec.",
            "consequences": "Pas de serveur à gérer.",
        }
        r = client.post("/adr", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["modules"] == ["data", "core"]
        assert data["decideurs"] == ["alice", "bob"]

    def test_incremente_id(self, client: TestClient, adr_exemple: ADR):
        r = client.post("/adr", json={"titre": "Deuxième décision"})
        assert r.status_code == 201
        assert r.json()["id"] == 2


# ── Modification ADR ──────────────────────────────────────────────────────────

class TestModifierADR:
    def test_modification_statut(self, client: TestClient, adr_exemple: ADR):
        payload = {
            "titre": "Utiliser FastAPI pour l'API REST",
            "statut": "deprecie",
            "modules": ["api"],
            "decideurs": ["alice"],
            "contexte": "Besoin d'une API HTTP pour le frontend.",
            "decision": "On utilise FastAPI + uvicorn.",
            "consequences": "Remplacé par gRPC.",
        }
        r = client.put("/adr/1", json=payload)
        assert r.status_code == 200
        assert r.json()["statut"] == "deprecie"

    def test_modification_titre_renomme_fichier(self, client: TestClient, adr_exemple: ADR,
                                                 decisions_dir: Path):
        ancien = list(decisions_dir.glob("*.md"))[0]
        payload = {
            "titre": "Nouveau titre complètement différent",
            "statut": "accepte",
            "modules": [],
            "decideurs": [],
            "contexte": "",
            "decision": "",
            "consequences": "",
        }
        client.put("/adr/1", json=payload)
        # L'ancien fichier ne doit plus exister, le nouveau oui
        assert not ancien.exists()
        assert len(list(decisions_dir.glob("*.md"))) == 1

    def test_modification_conserve_date(self, client: TestClient, adr_exemple: ADR):
        payload = {
            "titre": "Utiliser FastAPI pour l'API REST",
            "statut": "remplace",
            "modules": [],
            "decideurs": [],
            "contexte": "",
            "decision": "",
            "consequences": "",
        }
        r = client.put("/adr/1", json=payload)
        assert r.json()["date"] == "2026-05-20"

    def test_introuvable(self, client: TestClient):
        r = client.put("/adr/999", json={"titre": "X"})
        assert r.status_code == 404


# ── Recherche ─────────────────────────────────────────────────────────────────

class TestSearch:
    def test_recherche_texte_match(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr/search?q=FastAPI")
        assert r.status_code == 200
        data = r.json()
        assert len(data["resultats"]) == 1
        assert data["resultats"][0]["adr"]["id"] == 1

    def test_recherche_texte_sans_resultat(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr/search?q=kubernetes")
        assert r.status_code == 200
        assert r.json()["resultats"] == []

    def test_recherche_semantique_sans_index(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr/search?q=API&semantic=true")
        assert r.status_code == 200
        data = r.json()
        assert data["index_disponible"] is False
        assert data["resultats"] == []

    def test_q_obligatoire(self, client: TestClient):
        r = client.get("/adr/search")
        assert r.status_code == 422
