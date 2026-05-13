# TeamBrain — CLAUDE.md

@../../PRINCIPES.md

ADR git-natif + MCP server mémoire décisionnelle d'équipe.
Spec complète : `../../_ideas/TeamBrain/PROPOSITION.md`

## Stack

- Python 3.13 + hatchling
- typer[all] + rich — CLI
- ollama — génération brouillons (qwen3:1.7b) + embeddings (qwen3-embedding:0.6b)
- python-frontmatter — parsing/écriture des fichiers ADR
- sqlite-vec — index vectoriel local pour la recherche sémantique
- mcp — serveur MCP (FastMCP, transport stdio)

## Structure

```
src/teambrain/
├── cli.py      # 8 commandes typer : init, add, list, search, show, index, serve, setup
├── adr.py      # modèle ADR, lecture/écriture/search texte
├── ai.py       # génération brouillon via Ollama
├── store.py    # index sqlite-vec + embeddings Ollama
├── server.py   # FastMCP : search_decisions, get_decision, list_decisions, get_context_for_file
└── config.py   # .decisions/.teambrain.json
tests/
├── test_adr.py     # 11 tests
├── test_store.py   # 6 tests (embeddings mockés)
└── test_server.py  # 11 tests (résolution chemin → modules)
```

## Commandes dev

```bash
pip install -e ".[dev]"   # dans le venv
pytest                     # 30 tests

teambrain init             # crée .decisions/ dans le repo courant
teambrain add "..."        # nouvel ADR avec brouillon Ollama
teambrain list             # liste les ADR
teambrain search "..."     # recherche texte (sans index)
teambrain show 1           # affiche un ADR complet
teambrain index            # indexe dans sqlite-vec (qwen3-embedding:0.6b)
teambrain serve            # lance le serveur MCP stdio
teambrain setup            # configure Claude Code + Cursor
```

## État des modules

- **Module 1** : ✅ CLI + format ADR + add (Ollama) + search texte
- **Module 2** : ✅ MCP server + sqlite-vec + mapping chemin→modules
- **Module 3** : à venir — Chat bot multi-plateforme (Slack, Teams, Discord, Mattermost)
- **Module 4** : à venir (optionnel) — Git/Code mining avec filtrage IA

## Architecture Module 3 (à venir)

### ChatPlatformAdapter — Architecture pluggable

Module 3 utilise une abstraction `ChatPlatformAdapter` pour supporter plusieurs plateformes de chat :

```
src/teambrain/chat/
├── base.py              # Interface ChatPlatformAdapter
├── adapters/
│   ├── slack.py         # SlackAdapter (livré avec Module 3)
│   ├── teams.py         # TeamsAdapter (extension optionnelle)
│   ├── discord.py       # DiscordAdapter (extension optionnelle)
│   └── mattermost.py    # MattermostAdapter (extension optionnelle)
└── bot.py               # Logique commune (detection, generation, validation)
```

**Config** dans `.decisions/.teambrain.json` :
```json
{
  "chat": {
    "platform": "slack",
    "channels": ["#architecture", "#decisions"],
    "token_env": "SLACK_BOT_TOKEN"
  }
}
```

Premiers supports : `"slack"` (défaut)
Extensions futures : `"teams"`, `"discord"`, `"mattermost"`

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

- `ollama.chat()` peut wrapper le JSON dans ```json``` malgré le prompt système → nettoyage dans `ai.py`
- `python-frontmatter` : les dates YAML peuvent être retournées en `date` ou `str` selon le contexte → normalisation dans `from_post()`
- `get_context_for_file()` : utilise `module_mappings` si présent, sinon fallback sur les segments du chemin. Pour les gros projets avec noms de modules qui ne correspondent pas au dossier, configurer les mappings explicites.
