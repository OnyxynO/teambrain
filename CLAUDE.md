# TeamBrain — CLAUDE.md

@../../PRINCIPES.md

ADR git-natif + MCP server mémoire décisionnelle d'équipe.
Spec complète : `../../_ideas/TeamBrain/PROPOSITION.md`

## Stack

**Core** :
- Python 3.13 + hatchling
- typer[all] + rich — CLI
- ollama — génération brouillons (qwen3:1.7b) + embeddings (qwen3-embedding:0.6b)
- python-frontmatter — parsing/écriture des fichiers ADR
- sqlite-vec — index vectoriel local pour la recherche sémantique
- mcp — serveur MCP (FastMCP, transport stdio)

**Optionnelles (Module 3)** :
- slack-sdk >= 3.30 — Socket Mode + Block Kit
- PyGithub >= 2.0 — création PR automatique

## Structure

```
src/teambrain/
├── cli.py         # 9 commandes : init, add, list, search, show, index, serve, setup, bot
├── adr.py         # modèle ADR, lecture/écriture/search texte
├── ai.py          # génération brouillon via Ollama
├── store.py       # index sqlite-vec + embeddings Ollama
├── server.py      # FastMCP : search_decisions, get_decision, list_decisions, get_context_for_file
├── config.py      # .decisions/.teambrain.json
└── chat/          # Module 3 — Chat bot (optionnel)
    ├── base.py         # Interface ChatPlatformAdapter + Message dataclass
    ├── bot.py          # DetectionBot : patterns + scoring Ollama + orchestration
    ├── github.py       # GitHubPRCreator : branche + commit + PR
    └── adapters/
        ├── slack.py        # SlackAdapter : Socket Mode + Block Kit
        └── [teams.py]      # TeamsAdapter (à venir)
tests/
├── test_adr.py       # 11 tests
├── test_store.py     # 6 tests (embeddings mockés)
├── test_server.py    # 13 tests (résolution chemin → modules)
└── test_bot.py       # 15 tests (patterns, scoring, orchestration)
```

## Commandes dev

```bash
# Installation
pip install -e ".[dev]"        # core + dev deps
pip install -e ".[bot]"        # core + slack-sdk + PyGithub (pour Module 3)

# Tests
pytest                         # 51 tests

# CLI
teambrain init                 # crée .decisions/ dans le repo courant
teambrain add "..."            # nouvel ADR avec brouillon Ollama
teambrain list                 # liste les ADR
teambrain search "..."         # recherche texte (sans index)
teambrain show 1               # affiche un ADR complet
teambrain index                # indexe dans sqlite-vec (qwen3-embedding:0.6b)
teambrain serve                # lance le serveur MCP stdio
teambrain setup                # configure Claude Code + Cursor
teambrain setup slack          # wizard configuration Slack (2 étapes)
teambrain bot                  # lance le chat bot Slack
teambrain bot --check          # vérifie la config sans lancer le bot
teambrain bot --confidence 0.7 # seuil de confiance personnalisé
```

## État des modules

- **Module 1** : ✅ CLI + format ADR + add (Ollama) + search texte
- **Module 2** : ✅ MCP server + sqlite-vec + mapping chemin→modules
- **Module 3** : ✅ Chat bot — Socket Mode Slack + Block Kit + patterns + scoring Ollama + PR GitHub
- **Module 4** : à venir (optionnel) — Git/Code mining avec filtrage IA

## Module 3 — Chat Bot

### Architecture pluggable

Module 3 utilise `ChatPlatformAdapter` pour supporter plusieurs plateformes :

```python
class ChatPlatformAdapter(ABC):
    def listen(self, channels, on_message, on_action) -> None
    def send_dm(self, user_id, text) -> str
    def send_proposal(self, user_id, adr_draft, context) -> str
    def reply_thread(self, channel, thread_ts, text) -> None
```

Première implémentation : `SlackAdapter` avec Socket Mode (WebSocket local) + Block Kit interactif.

### Flux de détection

1. **Écoute** : Socket Mode capte tous les messages des canaux
2. **Candidature** : regex patterns rapides sur le texte (`"on a décidé"`, `"on va partir sur"`, etc.)
3. **Scoring** : Ollama évalue si c'est vraiment une décision architecturale + confidence
4. **Proposition** : DM au tech lead avec boutons Block Kit (Valider / Éditer / Ignorer)
5. **Validation** : Action → sauvegarde ADR + création PR GitHub (optionnel)

### Configuration

**Tokens requis** (variables d'env) :
- `SLACK_BOT_TOKEN` (xoxb-...)
- `SLACK_APP_TOKEN` (xapp-...)
- `TEAMBRAIN_LEAD` (ID utilisateur cible pour DM)

**Optionnel** (pour PR auto) :
- `GITHUB_TOKEN` (ghp-...)
- `GITHUB_REPO` (owner/repo)

Dans `.decisions/.teambrain.json` :
```json
{
  "chat": {
    "channels": ["#architecture", "#decisions"],
    "confidence_threshold": 0.7
  }
}
```

Extensions futures : Teams, Discord, Mattermost

## Configuration avancée

### Mapping explicite chemin → modules

Par défaut, `get_context_for_file()` détecte les modules via les segments du chemin : `src/auth/service.py` → module `"auth"`.

Pour plus de contrôle, ajouter un champ `module_mappings` dans `.decisions/.teambrain.json` :

```json
{
  "model": "qwen3:1.7b",
  "embedding_model": "qwen3-embedding:0.6b",
  "module_mappings": {
    "src/auth/":    "auth",
    "src/api/":     ["api", "http"],
    "tests/auth/":  "auth",
    "src/models/":  ["core", "data"]
  }
}
```

Logique de matching (ordre de priorité) :
1. Mappings explicites (test de préfixe chemin)
2. Fallback : segments du chemin
3. Recherche sémantique (si aucun match)

## Pièges connus

**Modules 1-2** :
- `ollama.chat()` peut wrapper le JSON dans ```json``` malgré le prompt système → nettoyage dans `ai.py`
- `python-frontmatter` : les dates YAML peuvent être retournées en `date` ou `str` selon le contexte → normalisation dans `from_post()`
- `get_context_for_file()` : utilise `module_mappings` si présent, sinon fallback sur les segments du chemin. Pour les gros projets, configurer les mappings explicites.

**Module 3** :
- Socket Mode : `SocketModeClient.connect()` est non-blocking → `threading.Event().wait()` pour maintenir le process vivant.
- Block Kit payload : le user ID est dans `payload["user"]["id"]`, pas `payload["user_id"]` (piège confirmé en test live).
- `_pending` est en mémoire : perdu au redémarrage. Les propositions en attente deviennent orphelines après un restart.
- Le bot doit être **invité dans chaque canal** via `/invite @BotName` — sans ça, Socket Mode ne livre pas les messages même avec les bons scopes et event subscriptions.
- Scopes OAuth requis : `channels:read channels:history groups:read groups:history im:history chat:write im:write users:read`. Oublier `channels:read` ou `groups:read` empêche la réception des événements.
- Ollama scoring : ~500ms par message. Pour <50 msg/jour c'est OK, au-delà envisager un cache ou batch.
- Token expiration : Slack bot tokens ne se renouvellent pas automatiquement. Relancer le bot en cas de 401.
- `teambrain bot --check` pour diagnostiquer avant de lancer (vérifie token, DM lead, liste les canaux à inviter).
