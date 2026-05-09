from datetime import date

from teambrain.adr import ADR, save_adr
from teambrain.store import reindex, search_semantic


def make_adr(id, titre, decision, modules=None):
    return ADR(
        id=id, titre=titre, date=date(2026, 5, 9), statut="accepte",
        modules=modules or [], decideurs=[],
        contexte="", decision=decision, consequences="",
    )


def fake_embed(text: str) -> list[float]:
    """Vecteur déterministe de dimension 4 pour les tests, sans Ollama."""
    h = abs(hash(text)) % 1000
    return [h / 1000, (h * 7 % 1000) / 1000, (h * 13 % 1000) / 1000, (h * 17 % 1000) / 1000]


def test_reindex_repo_vide(tmp_path):
    assert reindex(tmp_path, {}, embed_fn=fake_embed) == 0


def test_reindex_compte_adrs(tmp_path):
    save_adr(make_adr(1, "Choix PostgreSQL", "PostgreSQL 16"), tmp_path)
    save_adr(make_adr(2, "Choix JWT", "JWT signé"), tmp_path)
    assert reindex(tmp_path, {}, embed_fn=fake_embed) == 2


def test_search_retourne_resultats(tmp_path):
    save_adr(make_adr(1, "Choix PostgreSQL", "PostgreSQL pour ltree et jsonb"), tmp_path)
    save_adr(make_adr(2, "Choix JWT", "JWT signé pour l'auth"), tmp_path)
    reindex(tmp_path, {}, embed_fn=fake_embed)

    results = search_semantic("base de données", tmp_path, {}, embed_fn=fake_embed)
    assert len(results) > 0
    assert all(isinstance(r[0], int) and isinstance(r[1], float) for r in results)


def test_search_sans_index(tmp_path):
    assert search_semantic("PostgreSQL", tmp_path, {}, embed_fn=fake_embed) == []


def test_reindex_idempotent(tmp_path):
    save_adr(make_adr(1, "Choix PostgreSQL", "PostgreSQL 16"), tmp_path)
    reindex(tmp_path, {}, embed_fn=fake_embed)
    reindex(tmp_path, {}, embed_fn=fake_embed)  # deuxième appel ne doit pas planter

    results = search_semantic("test", tmp_path, {}, embed_fn=fake_embed)
    assert len(results) == 1


def test_reindex_nouvelle_dimension(tmp_path):
    save_adr(make_adr(1, "Choix PostgreSQL", "PostgreSQL 16"), tmp_path)
    reindex(tmp_path, {}, embed_fn=lambda t: [0.1, 0.2, 0.3, 0.4])
    # Changement de dimension → doit recréer sans planter
    reindex(tmp_path, {}, embed_fn=lambda t: [0.1, 0.2])
    results = search_semantic("test", tmp_path, {}, embed_fn=lambda t: [0.1, 0.2])
    assert len(results) == 1
