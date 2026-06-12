# TeamBrain

[![PyPI](https://img.shields.io/pypi/v/teambrain.svg)](https://pypi.org/project/teambrain/)
[![Python](https://img.shields.io/pypi/pyversions/teambrain.svg)](https://pypi.org/project/teambrain/)
[![Downloads](https://static.pepy.tech/badge/teambrain)](https://pepy.tech/project/teambrain)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Mémoire décisionnelle d'équipe, git-native.**

TeamBrain capture et retrouve les décisions d'architecture (ADR) directement dans ton repo git — avec une interface web, un serveur MCP pour les agents IA, et un bot Slack optionnel.

```
pip install "teambrain[desktop]"
teambrain init
teambrain ui
```

---

## Pourquoi TeamBrain ?

Les décisions d'architecture se perdent dans Slack, les PR, les réunions. Six mois plus tard, personne ne sait pourquoi on a choisi telle bibliothèque ou abandonnée telle approche.

TeamBrain stocke ces décisions en Markdown versionné dans `.decisions/` — dans le repo git lui-même. Pas de service externe, pas de base de données à maintenir.

---

## Ce que ça fait

- **CLI** — créer, lister, rechercher, afficher les ADR depuis le terminal
- **Interface web** — lire et créer des ADR sans passer par le terminal (pour les chefs de projet, designers, PO)
- **Brouillons IA** — génération automatique via Ollama (facultatif)
- **Serveur MCP** — expose les ADR aux agents IA (Claude, Cursor, Cline…)
- **Scanner git/code** — détecte les décisions implicites dans les commits et commentaires
- **Bot Slack** — capture les décisions prises en réunion Slack, propose un ADR à valider (optionnel)

---

## Prérequis

- Python 3.13+
- [Ollama](https://ollama.com) avec `qwen3:1.7b` — *facultatif*, pour la génération de brouillons et la recherche sémantique

Sans Ollama : `teambrain add`, `teambrain search` et `teambrain ui` fonctionnent, mais sans brouillon automatique ni recherche sémantique.

---

## Installation

**Core (CLI + MCP stdio) :**
```bash
pip install teambrain
```
Couvre : `init`, `add`, `list`, `search`, `show`, `index`, `serve` (MCP), `scan-commits`, `scan-code`, `setup`.

**Interface web — fenêtre native PyWebView (recommandé) :**
```bash
pip install "teambrain[desktop]"
```
Ajoute FastAPI + PyWebView. Active `teambrain ui` (fenêtre native WebKit) et `teambrain serve --http`.

**Interface web — navigateur seulement :**
```bash
pip install "teambrain[http]"
```
Ajoute FastAPI. Active `teambrain ui --browser` et `teambrain serve --http`. Pas de fenêtre native.

**Avec le bot Slack :**
```bash
pip install "teambrain[bot]"
```

Les extras se cumulent : `pip install "teambrain[desktop,bot]"`.

---

## Démarrage rapide

```bash
# 1. Initialise TeamBrain dans le repo courant
teambrain init

# 2. Lance l'interface web (fenêtre native PyWebView ou navigateur avec --browser)
teambrain ui

# 3. Ou crée un ADR depuis le terminal
teambrain add "Choix de SQLite plutôt que PostgreSQL"
```

`teambrain init` crée `.decisions/` et met à jour `.gitignore` automatiquement.

---

## CLI — Commandes

### Gestion des ADR

```bash
teambrain add "Titre de la décision"   # nouvel ADR (brouillon Ollama si disponible)
teambrain list                          # liste tous les ADR
teambrain show 3                        # affiche l'ADR #003
teambrain search "JWT"                  # recherche texte
```

### Recherche sémantique

```bash
teambrain index                         # indexe les ADR dans sqlite-vec
teambrain search "authentification"     # recherche plein texte
```

### Interface web

```bash
teambrain ui                            # fenêtre native PyWebView (port 8003)
teambrain ui --browser                  # ouverture dans le navigateur système
teambrain ui --repo /chemin/vers/repo   # repo spécifique
teambrain ui --repo /repo1 --repo /repo2  # multi-projets
teambrain ui --base /dossier/projets    # tous les repos du dossier
```

### Serveur MCP (agents IA)

```bash
teambrain serve                         # serveur MCP stdio
teambrain setup                         # configure Claude Code et Cursor automatiquement
```

### Scanner git/code

```bash
teambrain scan-commits                  # scanne les commits récents (7 derniers jours)
teambrain scan-commits --depuis 1m      # 1 mois d'historique
teambrain scan-commits --semantic       # comparaison sémantique avec l'index ADR
teambrain scan-commits --no-ai          # sans scoring Ollama (plus rapide)
teambrain scan-code                     # scanne les marqueurs DECISION:, ADR: dans le code
```

### Bot Slack

```bash
teambrain setup slack                   # assistant de configuration (génère l'app manifest)
teambrain bot                           # lance le bot
teambrain bot --check                   # vérifie les tokens et la présence dans les canaux
```

---

## Interface web

`teambrain ui` ouvre une fenêtre native PyWebView (WebKit sur macOS) pointée sur `http://localhost:8003`. Avec `--browser`, retombe sur le navigateur système.

**Fonctionnalités :**
- Liste paginée des ADR avec filtres (statut, module)
- Vue détail en Markdown rendu
- Création guidée : titre → contexte → décision → conséquences (brouillon Ollama si disponible)
- Recherche plein texte

**Accès équipe :** le tech lead lance `teambrain ui`, les collègues accèdent via l'IP locale ou un SSH forward. Aucune authentification — réseau local de confiance.

> ⚠️ **Note sécurité** — Par défaut, l'API HTTP écoute uniquement sur `127.0.0.1` et CORS est ouvert (`*`) pour faciliter le développement local. Exposer le service via `--host 0.0.0.0` rend l'API joignable par tout client du réseau, sans authentification ni restriction d'origine. À réserver à un réseau de confiance, ou à placer derrière un reverse proxy (auth + TLS).

---

## Sans Ollama

TeamBrain fonctionne sans Ollama. Dans ce cas :

- `teambrain add` crée un ADR vide à remplir manuellement (fichier Markdown dans `.decisions/`)
- `teambrain ui` affiche la page de création sans le champ "Générer un brouillon"
- `teambrain search` effectue une recherche texte brute
- `teambrain scan-commits --no-ai` retourne les candidats bruts sans scoring

**Pour installer Ollama et les modèles requis :**
```bash
# macOS
brew install ollama
ollama pull qwen3:1.7b             # génération de brouillons
ollama pull qwen3-embedding:0.6b   # recherche sémantique (teambrain index)
```

---

## Multi-projets

Surveiller plusieurs repos depuis une seule interface :

```bash
# Deux repos explicites
teambrain ui --repo /projets/backend --repo /projets/frontend

# Tous les repos d'un dossier (auto-détection des .decisions/)
teambrain ui --base /projets/
```

L'interface web affiche un sélecteur de projet en haut à gauche.

---

## Configuration

TeamBrain se configure via `.decisions/.teambrain.json` :

```json
{
  "model": "qwen3:1.7b",
  "embedding_model": "qwen3-embedding:0.6b",
  "module_mappings": {
    "src/auth/":   "auth",
    "src/api/":    ["api", "http"],
    "src/models/": "core"
  },
  "commit_patterns": [
    "migrer",
    "remplacer .+ par",
    "architecture"
  ],
  "code_patterns": [
    "CHOIX_ARCHI:"
  ],
  "chat": {
    "channels": ["#architecture", "#decisions"],
    "confidence_threshold": 0.7
  }
}
```

| Clé | Défaut | Description |
|-----|--------|-------------|
| `model` | `qwen3:1.7b` | Modèle Ollama pour la génération de brouillons |
| `embedding_model` | `qwen3-embedding:0.6b` | Modèle Ollama pour les embeddings |
| `module_mappings` | `{}` | Mapping chemin → modules ADR (voir `EXAMPLE_CONFIG.md`) |
| `commit_patterns` | `[]` | Patterns regex supplémentaires pour `scan-commits` |
| `code_patterns` | `[]` | Patterns regex supplémentaires pour `scan-code` |
| `chat.channels` | `[]` | Canaux Slack à surveiller |
| `chat.confidence_threshold` | `0.7` | Seuil de confiance pour la détection (0-1) |

Voir `EXAMPLE_CONFIG.md` pour les cas avancés (multi-modules, patterns regex, fallback).

---

## Intégration MCP (agents IA)

TeamBrain expose les ADR via le [Model Context Protocol](https://modelcontextprotocol.io) — les agents IA peuvent interroger la mémoire décisionnelle du repo.

**Configuration automatique :**
```bash
teambrain setup   # configure Claude Code (~/.claude.json) et Cursor (.cursor/mcp.json)
```

**Configuration manuelle (Claude Code) — dans `~/.claude.json` :**
```json
{
  "mcpServers": {
    "teambrain": {
      "command": "teambrain",
      "args": ["serve"],
      "cwd": "/chemin/vers/ton/repo"
    }
  }
}
```

**Outils MCP disponibles :**
- `search_decisions` — recherche dans les ADR
- `get_decision` — récupère un ADR par ID
- `list_decisions` — liste tous les ADR
- `get_context_for_file` — ADR liés à un fichier (via `module_mappings`)

---

## Bot Slack (optionnel)

Le bot écoute les canaux Slack, détecte les messages qui ressemblent à des décisions d'architecture, et propose au tech lead de créer un ADR via un DM avec boutons Block Kit.

**Prérequis :** `pip install "teambrain[bot]"` + un workspace Slack avec permissions admin.

**Configuration en 3 étapes :**
```bash
# 1. Génère l'app manifest Slack
teambrain setup slack

# 2. Colle le manifest sur api.slack.com → Create New App → From an app manifest
# 3. Récupère les tokens et configure les variables d'env

export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
export TEAMBRAIN_LEAD="U0XXXXXXX"   # ton ID utilisateur Slack

# 4. Vérifie la configuration
teambrain bot --check

# 5. Lance le bot
teambrain bot
```

**Variables optionnelles (création de PR automatique) :**
```bash
export GITHUB_TOKEN="ghp-..."
export GITHUB_REPO="organisation/repo"
```

---

## Format ADR

Les ADR sont des fichiers Markdown avec frontmatter YAML dans `.decisions/` :

```markdown
---
id: 1
titre: Choix de SQLite plutôt que PostgreSQL
date: 2026-05-20
statut: accepte       # accepte | propose | deprecie | remplace
modules: [core, data]
decideurs: [alice, bob]
---

## Contexte

Application desktop mono-utilisateur, zéro infrastructure à maintenir.

## Décision

On utilise SQLite. Zéro service, fichier unique, suffisant pour <100k lignes.

## Conséquences

- Pas de requêtes concurrentes multi-process
- Migration vers PostgreSQL possible si besoin multi-utilisateurs
```

Les fichiers sont versionnés avec git — l'historique et les `git blame` sont disponibles naturellement.

---

## Développement

```bash
git clone https://github.com/OnyxynO/teambrain
cd teambrain

pip install -e ".[dev,http,bot,desktop]"
pytest                    # 116 tests Python (+ 19 Playwright e2e dans teambrain-web/)

# Interface web (développement)
cd teambrain-web
bun install
bun run dev               # http://localhost:3003

# Rebuilder le frontend statique (avant pip install en prod)
bash scripts/build_frontend.sh
```

---

## Licence

MIT
