# TeamBrain — Exemple de Configuration

## Configuration complète `.decisions/.teambrain.json`

```json
{
  "model": "qwen3:1.7b",
  "embedding_model": "qwen3-embedding:0.6b",
  "module_mappings": {
    "src/auth/":              "auth",
    "src/api/":               ["api", "http"],
    "src/models/":            "core",
    "src/domain/":            "business",
    "tests/auth/":            "auth",
    "tests/api/":             "api",
    "packages/shared/":       ["auth", "api", "core"],
    "infrastructure/deploy/": "devops"
  }
}
```

## Qu'est-ce que `module_mappings` ?

Mappe les **chemins de fichiers** aux **modules ADR**.

### Exemple concret

**Structure du projet :**
```
monorepo/
├── src/
│   ├── auth/
│   │   ├── middleware.py
│   │   └── jwt.py
│   ├── api/
│   │   ├── endpoints.py
│   │   └── validation.py
│   └── models/
│       └── user.py
├── tests/
│   ├── auth/
│   │   └── test_jwt.py
│   └── api/
│       └── test_endpoints.py
└── .decisions/
    ├── 001-jwt-auth.md        (module: "auth")
    ├── 002-api-design.md      (module: "api")
    └── .teambrain.json        (config avec mappings)
```

**Configuration :**
```json
{
  "module_mappings": {
    "src/auth/":  "auth",
    "src/api/":   "api",
    "tests/":     "test"
  }
}
```

### Résolution — cas par cas

| Fichier | Config | Modules résolus | Expliqué |
|---------|--------|---|---|
| `src/auth/jwt.py` | `"src/auth/": "auth"` | `{"auth"}` | Match exact du pattern |
| `src/api/endpoints.py` | `"src/api/": "api"` | `{"api"}` | Match exact |
| `tests/auth/test_jwt.py` | `"tests/": "test"` | `{"test"}` | Parent matche |
| `src/models/user.py` | (pas de mapping) | `{"src", "models", "user.py"}` | **Fallback** : segments du chemin |

## Cas avancés

### Multi-modules pour un chemin

Un fichier partagé peut appartenir à plusieurs modules :

```json
{
  "module_mappings": {
    "packages/shared/utils/":    ["auth", "api", "core"],
    "middleware/logging/":        ["all"]
  }
}
```

`packages/shared/utils/validation.py` → modules `["auth", "api", "core"]`
→ l'IA verra tous les ADRs associés à auth, api, et core.

### Mappings et fallback

L'ordre d'évaluation :

```
fichier: src/auth/utils/hash.py
config:  "src/auth/": "auth"

1. Test mapping explicite : "src/auth/" match le chemin ? OUI
   → Résultat : {"auth"}
   
2. Pas de fallback (mapping a matché)
```

vs sans mapping :

```
fichier: src/auth/utils/hash.py
config:  {} (vide)

1. Pas de mapping
2. Fallback segment : segments du chemin
   → Résultat : {"src", "auth", "utils", "hash.py"}
```

## Bonnes pratiques

1. **Aligner les chemins avec les modules**
   ```json
   {
     "src/payment/":    "payment",    // ✓ Clair
     "src/foo/":        "bar"          // ✗ Confus
   }
   ```

2. **Couvrir tests aussi**
   ```json
   {
     "src/auth/":       "auth",
     "tests/auth/":     "auth",        // ← Important
     "integration/auth/": "auth"
   }
   ```

3. **Partager quand approprié**
   ```json
   {
     "packages/shared/":  ["auth", "api"],
     "middleware/":       ["auth", "api"]
   }
   ```

4. **Documenter les modules dans l'équipe**
   ```
   Modules utilisés :
   - auth    : JWT, sessions, RBAC
   - api     : REST endpoints, versioning
   - core    : data models, business logic
   - devops  : CI/CD, infrastructure
   ```

## Tests

Pour vérifier que le mapping fonctionne :

```bash
# Créer un ADR avec un module
teambrain add "Choix JWT"
# → Edit → ajouter "modules": ["auth"]

# Lancer l'index
teambrain index

# Vérifier via le MCP (depuis le code du dev)
# get_context_for_file("src/auth/service.py")
# → devrait retourner l'ADR "Choix JWT"
```
