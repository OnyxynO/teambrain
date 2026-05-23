from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from teambrain.adr import ADR, save_adr
from teambrain.http_api import create_app

NOM = "test"


@pytest.fixture
def decisions_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".decisions"
    d.mkdir()
    return d


@pytest.fixture
def client(decisions_dir: Path) -> TestClient:
    return TestClient(create_app({NOM: decisions_dir}))


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

    def test_liste_projets_dans_health(self, client: TestClient):
        assert NOM in r.json()["projets"] if (r := client.get("/health")) else True
        r = client.get("/health")
        assert NOM in r.json()["projets"]


# ── Projets ───────────────────────────────────────────────────────────────────

class TestProjets:
    def test_liste(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/projects")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["id"] == NOM
        assert data[0]["nb_adrs"] == 1

    def test_multi_projets(self, tmp_path: Path):
        d1, d2 = tmp_path / "p1" / ".decisions", tmp_path / "p2" / ".decisions"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        save_adr(ADR(id=1, titre="A", date=date.today(), statut="propose",
                     modules=[], decideurs=[], contexte="", decision="", consequences=""), d1)
        c = TestClient(create_app({"p1": d1, "p2": d2}))
        r = c.get("/projects")
        assert len(r.json()) == 2
        noms = {p["id"] for p in r.json()}
        assert noms == {"p1", "p2"}


# ── Référentiels ──────────────────────────────────────────────────────────────

class TestReferentiels:
    def test_inclut_projets(self, client: TestClient):
        r = client.get("/referentiels")
        assert r.status_code == 200
        assert NOM in r.json()["projets"]

    def test_filtre_par_projet(self, tmp_path: Path):
        d1, d2 = tmp_path / "a" / ".decisions", tmp_path / "b" / ".decisions"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        save_adr(ADR(id=1, titre="A", date=date.today(), statut="propose",
                     modules=["frontend"], decideurs=[], contexte="", decision="", consequences=""), d1)
        save_adr(ADR(id=1, titre="B", date=date.today(), statut="propose",
                     modules=["backend"], decideurs=[], contexte="", decision="", consequences=""), d2)
        c = TestClient(create_app({"a": d1, "b": d2}))
        r = c.get("/referentiels?projet=a")
        assert "frontend" in r.json()["modules"]
        assert "backend" not in r.json()["modules"]


# ── Liste ADR ─────────────────────────────────────────────────────────────────

class TestListeADR:
    def test_vide(self, client: TestClient):
        r = client.get("/adr")
        assert r.status_code == 200
        assert r.json() == []

    def test_champ_projet_present(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr")
        assert r.json()[0]["projet"] == NOM

    def test_filtre_statut_match(self, client: TestClient, adr_exemple: ADR):
        assert len(client.get("/adr?statut=accepte").json()) == 1
        assert client.get("/adr?statut=propose").json() == []

    def test_filtre_module(self, client: TestClient, adr_exemple: ADR):
        assert len(client.get("/adr?module=api").json()) == 1
        assert client.get("/adr?module=frontend").json() == []

    def test_filtre_projet(self, client: TestClient, adr_exemple: ADR):
        assert len(client.get(f"/adr?projet={NOM}").json()) == 1
        assert client.get("/adr?projet=inconnu").json() == []

    def test_multi_projets_tous(self, tmp_path: Path):
        d1, d2 = tmp_path / "x" / ".decisions", tmp_path / "y" / ".decisions"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        save_adr(ADR(id=1, titre="X", date=date.today(), statut="propose",
                     modules=[], decideurs=[], contexte="", decision="", consequences=""), d1)
        save_adr(ADR(id=1, titre="Y", date=date.today(), statut="propose",
                     modules=[], decideurs=[], contexte="", decision="", consequences=""), d2)
        c = TestClient(create_app({"x": d1, "y": d2}))
        assert len(c.get("/adr").json()) == 2

    def test_filtre_cumule(self, client: TestClient, decisions_dir: Path):
        save_adr(ADR(id=1, titre="A", date=date.today(), statut="accepte",
                     modules=["api"], decideurs=[], contexte="", decision="", consequences=""),
                 decisions_dir)
        save_adr(ADR(id=2, titre="B", date=date.today(), statut="propose",
                     modules=["api"], decideurs=[], contexte="", decision="", consequences=""),
                 decisions_dir)
        assert len(client.get("/adr?statut=accepte&module=api").json()) == 1


# ── Détail ADR ────────────────────────────────────────────────────────────────

class TestDetailADR:
    def test_existant(self, client: TestClient, adr_exemple: ADR):
        r = client.get(f"/adr/{NOM}/1")
        assert r.status_code == 200
        assert r.json()["id"] == 1
        assert r.json()["projet"] == NOM

    def test_projet_introuvable(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr/inconnu/1")
        assert r.status_code == 404

    def test_id_introuvable(self, client: TestClient):
        r = client.get(f"/adr/{NOM}/999")
        assert r.status_code == 404


# ── Création ADR ──────────────────────────────────────────────────────────────

class TestCreerADR:
    def test_creation_minimale(self, client: TestClient, decisions_dir: Path):
        r = client.post(f"/adr/{NOM}", json={"titre": "Nouvelle décision"})
        assert r.status_code == 201
        data = r.json()
        assert data["id"] == 1
        assert data["projet"] == NOM
        assert len(list(decisions_dir.glob("*.md"))) == 1

    def test_projet_introuvable(self, client: TestClient):
        r = client.post("/adr/inconnu", json={"titre": "X"})
        assert r.status_code == 404

    def test_incremente_id(self, client: TestClient, adr_exemple: ADR):
        r = client.post(f"/adr/{NOM}", json={"titre": "Deuxième"})
        assert r.json()["id"] == 2


# ── Modification ADR ──────────────────────────────────────────────────────────

class TestModifierADR:
    def test_modification_statut(self, client: TestClient, adr_exemple: ADR):
        payload = {
            "titre": "Utiliser FastAPI pour l'API REST",
            "statut": "deprecie",
            "modules": ["api"],
            "decideurs": ["alice"],
            "contexte": "",
            "decision": "",
            "consequences": "",
        }
        r = client.put(f"/adr/{NOM}/1", json=payload)
        assert r.status_code == 200
        assert r.json()["statut"] == "deprecie"

    def test_modification_titre_renomme_fichier(self, client: TestClient, adr_exemple: ADR,
                                                  decisions_dir: Path):
        ancien = list(decisions_dir.glob("*.md"))[0]
        client.put(f"/adr/{NOM}/1", json={"titre": "Titre complètement différent", "statut": "accepte"})
        assert not ancien.exists()
        assert len(list(decisions_dir.glob("*.md"))) == 1

    def test_modification_conserve_date(self, client: TestClient, adr_exemple: ADR):
        r = client.put(f"/adr/{NOM}/1", json={"titre": "T", "statut": "remplace"})
        assert r.json()["date"] == "2026-05-20"

    def test_modification_date(self, client: TestClient, adr_exemple: ADR):
        r = client.put(f"/adr/{NOM}/1", json={"titre": "T", "statut": "accepte", "date": "2025-01-15"})
        assert r.json()["date"] == "2025-01-15"

    def test_modification_date_invalide_conserve_date(self, client: TestClient, adr_exemple: ADR):
        r = client.put(f"/adr/{NOM}/1", json={"titre": "T", "statut": "accepte", "date": "pas-une-date"})
        assert r.status_code == 200
        assert r.json()["date"] == "2026-05-20"

    def test_introuvable(self, client: TestClient):
        r = client.put(f"/adr/{NOM}/999", json={"titre": "X"})
        assert r.status_code == 404


# ── Suppression ADR ───────────────────────────────────────────────────────────

class TestSupprimerADR:
    def test_suppression_ok(self, client: TestClient, adr_exemple: ADR, decisions_dir: Path):
        r = client.delete(f"/adr/{NOM}/1")
        assert r.status_code == 204
        assert len(list(decisions_dir.glob("*.md"))) == 0

    def test_suppression_introuvable(self, client: TestClient):
        r = client.delete(f"/adr/{NOM}/999")
        assert r.status_code == 404

    def test_suppression_projet_inconnu(self, client: TestClient, adr_exemple: ADR):
        r = client.delete("/adr/inconnu/1")
        assert r.status_code == 404

    def test_suppression_laisse_les_autres(self, client: TestClient, decisions_dir: Path):
        save_adr(ADR(id=1, titre="A", date=date.today(), statut="propose",
                     modules=[], decideurs=[], contexte="", decision="", consequences=""), decisions_dir)
        save_adr(ADR(id=2, titre="B", date=date.today(), statut="accepte",
                     modules=[], decideurs=[], contexte="", decision="", consequences=""), decisions_dir)
        client.delete(f"/adr/{NOM}/1")
        assert len(list(decisions_dir.glob("*.md"))) == 1


# ── Recherche ─────────────────────────────────────────────────────────────────

class TestSearch:
    def test_texte_match(self, client: TestClient, adr_exemple: ADR):
        r = client.get("/adr/search?q=FastAPI")
        assert r.status_code == 200
        assert len(r.json()["resultats"]) == 1
        assert r.json()["resultats"][0]["adr"]["projet"] == NOM

    def test_texte_multi_projets(self, tmp_path: Path):
        d1, d2 = tmp_path / "x" / ".decisions", tmp_path / "y" / ".decisions"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        for d, titre in [(d1, "Utiliser FastAPI"), (d2, "Utiliser FastAPI aussi")]:
            save_adr(ADR(id=1, titre=titre, date=date.today(), statut="propose",
                         modules=[], decideurs=[], contexte="", decision="", consequences=""), d)
        c = TestClient(create_app({"x": d1, "y": d2}))
        r = c.get("/adr/search?q=FastAPI")
        assert len(r.json()["resultats"]) == 2

    def test_filtre_projet_dans_search(self, tmp_path: Path):
        d1, d2 = tmp_path / "x" / ".decisions", tmp_path / "y" / ".decisions"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        save_adr(ADR(id=1, titre="Utiliser FastAPI", date=date.today(), statut="propose",
                     modules=[], decideurs=[], contexte="", decision="", consequences=""), d1)
        c = TestClient(create_app({"x": d1, "y": d2}))
        r = c.get("/adr/search?q=FastAPI&projet=y")
        assert r.json()["resultats"] == []

    def test_semantique_sans_projet_leve_400(self, client: TestClient):
        r = client.get("/adr/search?q=FastAPI&semantic=true")
        assert r.status_code == 400

    def test_semantique_sans_index(self, client: TestClient, adr_exemple: ADR):
        r = client.get(f"/adr/search?q=API&semantic=true&projet={NOM}")
        assert r.status_code == 200
        assert r.json()["index_disponible"] is False

    def test_q_obligatoire(self, client: TestClient):
        assert client.get("/adr/search").status_code == 422
