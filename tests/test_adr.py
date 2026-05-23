from datetime import date

from teambrain.adr import ADR, delete_adr, list_adrs, load_adr, next_id, save_adr, search_adrs, slugify


def make_adr(
    id=1,
    titre="Choix PostgreSQL",
    modules=None,
    statut="accepte",
    contexte="On avait besoin de types JSON avancés et ltree pour les hiérarchies.",
    decision="PostgreSQL 16 avec ltree et jsonb.",
    consequences="Migration depuis MySQL requise. Pas de retour arrière facile.",
):
    return ADR(
        id=id, titre=titre, date=date(2026, 5, 9), statut=statut,
        modules=modules or ["api", "bdd"], decideurs=["alice"],
        contexte=contexte, decision=decision, consequences=consequences,
    )


def test_slugify_basique():
    assert slugify("JWT vs Sessions") == "jwt-vs-sessions"


def test_slugify_accents():
    assert slugify("Choix PostgreSQL pour l'API") == "choix-postgresql-pour-l-api"


def test_save_load_roundtrip(tmp_path):
    adr = make_adr()
    path = save_adr(adr, tmp_path)
    assert path.exists()
    loaded = load_adr(path)
    assert loaded.id == adr.id
    assert loaded.titre == adr.titre
    assert loaded.statut == adr.statut
    assert loaded.modules == adr.modules
    assert loaded.contexte == adr.contexte
    assert loaded.decision == adr.decision
    assert loaded.consequences == adr.consequences


def test_list_adrs_ordre(tmp_path):
    save_adr(make_adr(1, "Premier choix"), tmp_path)
    save_adr(make_adr(2, "Deuxième choix"), tmp_path)
    adrs = list_adrs(tmp_path)
    assert len(adrs) == 2
    assert adrs[0].id == 1
    assert adrs[1].id == 2


def test_list_adrs_vide(tmp_path):
    assert list_adrs(tmp_path) == []


def test_next_id_repo_vide(tmp_path):
    assert next_id(tmp_path) == 1


def test_next_id_suite(tmp_path):
    save_adr(make_adr(1), tmp_path)
    save_adr(make_adr(2), tmp_path)
    assert next_id(tmp_path) == 3


def test_search_match_titre(tmp_path):
    save_adr(make_adr(1, "Choix PostgreSQL"), tmp_path)
    save_adr(make_adr(2, "Choix JWT", modules=["auth"],
                      contexte="Contrainte RGPD.", decision="JWT signé.", consequences="Pas de révocation."), tmp_path)
    results = search_adrs("PostgreSQL", tmp_path)
    assert len(results) >= 1
    assert results[0][0].id == 1


def test_search_match_contenu(tmp_path):
    save_adr(make_adr(1, decision="Utiliser Redis pour le cache distribué.",
                      contexte="Besoin de TTL automatique.", consequences="Dépendance externe."), tmp_path)
    results = search_adrs("cache Redis", tmp_path)
    assert len(results) == 1
    assert results[0][1] == 1.0


def test_search_sans_resultat(tmp_path):
    save_adr(make_adr(1), tmp_path)
    results = search_adrs("kubernetes microservices", tmp_path)
    assert len(results) == 0


def test_search_score_partiel(tmp_path):
    save_adr(make_adr(1, modules=["bdd"]), tmp_path)
    results = search_adrs("bdd inconnu", tmp_path)
    assert len(results) == 1
    assert results[0][1] == 0.5


def test_delete_adr_existant(tmp_path):
    save_adr(make_adr(1), tmp_path)
    assert delete_adr(1, tmp_path) is True
    assert list_adrs(tmp_path) == []


def test_delete_adr_inexistant(tmp_path):
    assert delete_adr(999, tmp_path) is False


def test_delete_adr_laisse_les_autres(tmp_path):
    save_adr(make_adr(1, "Premier"), tmp_path)
    save_adr(make_adr(2, "Deuxième"), tmp_path)
    delete_adr(1, tmp_path)
    restants = list_adrs(tmp_path)
    assert len(restants) == 1
    assert restants[0].id == 2
