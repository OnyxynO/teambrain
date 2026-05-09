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
├── test_adr.py   # 11 tests
└── test_store.py # 6 tests (embeddings mockés)
```

## Commandes dev

```bash
pip install -e ".[dev]"   # dans le venv
pytest                     # 17 tests

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
- **Module 2** : ✅ MCP server + sqlite-vec + auto-config clients
- **Module 3** : à venir — Slack bot (capture automatique)

## Pièges connus

- `ollama.chat()` peut wrapper le JSON dans ```json``` malgré le prompt système → nettoyage dans `ai.py`
- `python-frontmatter` : les dates YAML peuvent être retournées en `date` ou `str` selon le contexte → normalisation dans `from_post()`
