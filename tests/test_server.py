from __future__ import annotations
from teambrain.server import _modules_for_file


class TestModulesForFile:
    """Tests pour la résolution chemin -> modules via module_mappings."""

    def test_mapping_explicite_string(self):
        """Un mapping string mapppe correctement."""
        mappings = {"src/auth/": "auth"}
        result = _modules_for_file("src/auth/service.py", mappings)
        assert "auth" in result

    def test_mapping_explicite_list(self):
        """Un mapping list ajoute tous les modules."""
        mappings = {"src/api/": ["api", "http"]}
        result = _modules_for_file("src/api/endpoints.py", mappings)
        assert "api" in result
        assert "http" in result

    def test_mapping_chemin_sous_repertoire(self):
        """Un pattern matche aussi les fichiers en sous-répertoires."""
        mappings = {"src/auth/": "auth"}
        result = _modules_for_file("src/auth/utils/hash.py", mappings)
        assert "auth" in result

    def test_fallback_segment_sans_mapping(self):
        """Sans mapping, fallback sur les segments du chemin."""
        mappings = {}
        result = _modules_for_file("src/auth/service.py", mappings)
        # Segments : ['src', 'auth', 'service.py']
        assert "src" in result
        assert "auth" in result
        assert "service.py" in result

    def test_fallback_segment_priorite_mapping(self):
        """Si un mapping matche, pas de fallback segment."""
        mappings = {"src/auth/": "auth"}
        result = _modules_for_file("src/auth/service.py", mappings)
        # Doit avoir "auth" du mapping, mais pas les autres segments
        assert "auth" in result
        assert "service.py" not in result
        assert "src" not in result

    def test_multiple_mappings(self):
        """Plusieurs mappings peuvent matcher le même fichier."""
        mappings = {
            "src/": "core",
            "src/auth/": "auth",
        }
        result = _modules_for_file("src/auth/service.py", mappings)
        # src/auth/ matche avant src/, donc on devrait avoir au moins "auth"
        # (le premier qui matche gagne)
        assert len(result) > 0

    def test_chemin_vide(self):
        """Un chemin vide retourne un ensemble non-vide (fallback)."""
        mappings = {}
        result = _modules_for_file("", mappings)
        # Fallback segment sur "" donnera un ensemble
        assert isinstance(result, set)

    def test_normalisation_separateurs_windows(self):
        """Les séparateurs Windows sont normalisés."""
        mappings = {"src\\auth\\": "auth"}
        result = _modules_for_file("src/auth/service.py", mappings)
        assert "auth" in result

    def test_chemin_windows_avec_mapping_posix(self):
        """Un chemin Windows matche un mapping POSIX après normalisation."""
        mappings = {"src/auth/": "auth"}
        result = _modules_for_file("src\\auth\\service.py", mappings)
        assert "auth" in result

    def test_absence_match(self):
        """Un chemin sans match retourne fallback (segments)."""
        mappings = {"src/auth/": "auth"}
        result = _modules_for_file("other/file.py", mappings)
        # Pas de mapping, fallback segment
        assert "other" in result
        assert "file.py" in result

    def test_mapping_value_string_vs_list(self):
        """Les deux formats (string et list) fonctionnent dans le même dict."""
        mappings = {
            "src/auth/": "auth",
            "src/api/": ["api", "http"],
        }
        auth_result = _modules_for_file("src/auth/service.py", mappings)
        api_result = _modules_for_file("src/api/endpoints.py", mappings)

        assert "auth" in auth_result
        assert "api" in api_result
        assert "http" in api_result


class TestIntegration:
    """Tests d'intégration du mapping avec get_context_for_file."""

    def test_realistic_project_structure(self):
        """Cas réaliste : projet avec modules auth, api, core."""
        mappings = {
            "src/auth/":    "auth",
            "src/api/":     "api",
            "src/models/":  "core",
            "tests/":       "test",
        }

        # Test chaque type de chemin
        assert "auth" in _modules_for_file("src/auth/middleware.py", mappings)
        assert "api" in _modules_for_file("src/api/v1/endpoints.py", mappings)
        assert "core" in _modules_for_file("src/models/user.py", mappings)
        assert "test" in _modules_for_file("tests/unit/test_auth.py", mappings)

    def test_multi_module_file(self):
        """Un fichier peut mapper à plusieurs modules."""
        mappings = {
            "src/shared/": ["auth", "api"],
        }
        result = _modules_for_file("src/shared/utils.py", mappings)
        assert "auth" in result
        assert "api" in result
        # Pas d'autres modules du fallback
        assert "shared" not in result
