from datetime import date

from teambrain.adr import ADR, delete_adr, list_adrs, load_adr, next_id, parse_query, save_adr, search_adrs, slugify


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


# ── Tests parse_query ────────────────────────────────────────────────────────

def test_parse_query_termes_simples():
    r = parse_query("postgres redis")
    assert r.termes == ["postgres", "redis"]
    assert r.statuts == []
    assert r.modules == []

def test_parse_query_qualificatif_statut():
    r = parse_query("statut:accepte migration")
    assert r.statuts == ["accepte"]
    assert r.termes == ["migration"]

def test_parse_query_qualificatif_module():
    r = parse_query("module:auth securite")
    assert r.modules == ["auth"]
    assert r.termes == ["securite"]

def test_parse_query_qualificatif_decideur():
    r = parse_query("decideur:alice jwt")
    assert r.decideurs == ["alice"]
    assert r.termes == ["jwt"]

def test_parse_query_qualificatif_projet():
    r = parse_query("projet:teambrain securite")
    assert r.projets == ["teambrain"]
    assert r.termes == ["securite"]

def test_parse_query_phrase_exacte():
    r = parse_query('"base de données" migration')
    assert r.phrases == ["base de données"]
    assert r.termes == ["migration"]

def test_parse_query_regex():
    r = parse_query("/postgres|mysql/ migration")
    assert r.regexps == ["postgres|mysql"]
    assert r.termes == ["migration"]

def test_parse_query_exclusion():
    r = parse_query("postgres -mysql")
    assert r.termes == ["postgres"]
    assert r.exclusions == ["mysql"]

def test_parse_query_multiple_qualificatifs():
    r = parse_query("statut:accepte module:bdd postgres")
    assert r.statuts == ["accepte"]
    assert r.modules == ["bdd"]
    assert r.termes == ["postgres"]

def test_parse_query_in_champ():
    r = parse_query("in:titre postgres")
    assert r.champs == ["titre"]
    assert r.termes == ["postgres"]

def test_parse_query_operateurs_booleens_ignores():
    r = parse_query("postgres AND redis OR mysql")
    assert "and" not in r.termes
    assert "or" not in r.termes
    assert set(r.termes) == {"postgres", "redis", "mysql"}


# ── Tests search_adrs avec qualificatifs ────────────────────────────────────

def make_adr_complet(id, titre, statut="accepte", modules=None, decideurs=None,
                     contexte="", decision="", consequences=""):
    return ADR(
        id=id, titre=titre, date=date(2026, 1, 1), statut=statut,
        modules=modules or [], decideurs=decideurs or [],
        contexte=contexte, decision=decision, consequences=consequences,
    )

def test_search_qualificatif_statut(tmp_path):
    save_adr(make_adr_complet(1, "Auth JWT", statut="accepte", contexte="securite"), tmp_path)
    save_adr(make_adr_complet(2, "Cache Redis", statut="propose", contexte="performance"), tmp_path)
    results = search_adrs("statut:accepte", tmp_path)
    assert len(results) == 1
    assert results[0][0].id == 1

def test_search_qualificatif_module(tmp_path):
    save_adr(make_adr_complet(1, "Auth JWT", modules=["auth", "api"]), tmp_path)
    save_adr(make_adr_complet(2, "Cache Redis", modules=["cache"]), tmp_path)
    results = search_adrs("module:auth", tmp_path)
    assert len(results) == 1
    assert results[0][0].id == 1

def test_search_qualificatif_decideur(tmp_path):
    save_adr(make_adr_complet(1, "Auth JWT", decideurs=["alice", "bob"]), tmp_path)
    save_adr(make_adr_complet(2, "Cache Redis", decideurs=["charlie"]), tmp_path)
    results = search_adrs("decideur:alice", tmp_path)
    assert len(results) == 1
    assert results[0][0].id == 1

def test_search_phrase_exacte(tmp_path):
    save_adr(make_adr_complet(1, "Choix BDD", decision="Utiliser base de données relationnelle."), tmp_path)
    save_adr(make_adr_complet(2, "Cache", decision="Utiliser Redis en mémoire."), tmp_path)
    results = search_adrs('"base de données"', tmp_path)
    assert len(results) == 1
    assert results[0][0].id == 1

def test_search_regex(tmp_path):
    save_adr(make_adr_complet(1, "BDD", decision="PostgreSQL pour le stockage."), tmp_path)
    save_adr(make_adr_complet(2, "Cache", decision="Redis pour le cache."), tmp_path)
    results = search_adrs("/postgres|mysql/", tmp_path)
    assert len(results) == 1
    assert results[0][0].id == 1

def test_search_exclusion(tmp_path):
    save_adr(make_adr_complet(1, "BDD", decision="PostgreSQL"), tmp_path)
    save_adr(make_adr_complet(2, "Cache", decision="Redis"), tmp_path)
    results = search_adrs("bdd -redis", tmp_path)
    ids = [r[0].id for r in results]
    assert 1 in ids
    assert 2 not in ids

def test_search_in_titre_only(tmp_path):
    save_adr(make_adr_complet(1, "Migration PostgreSQL", decision="Rien"), tmp_path)
    save_adr(make_adr_complet(2, "Cache Redis", decision="Utiliser PostgreSQL pour les logs"), tmp_path)
    # in:titre restreint au titre seulement
    results = search_adrs("in:titre PostgreSQL", tmp_path)
    ids = [r[0].id for r in results]
    assert 1 in ids
    assert 2 not in ids

def test_search_qualificatifs_plus_fulltext(tmp_path):
    save_adr(make_adr_complet(1, "Auth JWT", statut="accepte", modules=["auth"],
                              decision="JWT pour l'authentification."), tmp_path)
    save_adr(make_adr_complet(2, "Auth Sessions", statut="deprecie", modules=["auth"],
                              decision="Sessions serveur."), tmp_path)
    results = search_adrs("statut:accepte module:auth jwt", tmp_path)
    assert len(results) == 1
    assert results[0][0].id == 1
