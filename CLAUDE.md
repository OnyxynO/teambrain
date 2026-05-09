# TeamBrain — CLAUDE.md

@../../PRINCIPES.md

ADR git-natif + MCP server mémoire décisionnelle d'équipe.
Spec complète : `../../_ideas/TeamBrain/PROPOSITION.md`

## Stack

- Python 3.13 + hatchling
- typer[all] + rich — CLI
- ollama — génération brouillons ADR (défaut : qwen3:1.7b)
- python-frontmatter — parsing/écriture des fichiers ADR
- Module 2 (à venir) : MCP SDK Anthropic + sqlite-vec

## Structure

```
src/teambrain/
├── cli.py      # commandes typer : init, add, list, search, show
├── adr.py      # modèle ADR, lecture/écriture/recherche texte
├── ai.py       # intégration Ollama (génération brouillon)
└── config.py   # .decisions/.teambrain.json
tests/
└── test_adr.py
```

## Commandes dev

```bash
# Installer en mode éditable
pip install -e ".[dev]"

# Tests
pytest

# CLI depuis le repo
teambrain --help
teambrain init
teambrain add "description de la décision"
teambrain list
teambrain search "mot-clé"
teambrain show 1
```

## État des modules

- **Module 1** : en cours — CLI + format ADR + add (Ollama) + search texte
- **Module 2** : à venir — MCP server + sqlite-vec (recherche vectorielle)
- **Module 3** : à venir — Slack bot (capture automatique)

## Pièges connus

- `ollama.chat()` peut wrapper le JSON dans ```json``` malgré le prompt système → nettoyage dans `ai.py`
- `python-frontmatter` : les dates YAML peuvent être retournées en `date` ou `str` selon le contexte → normalisation dans `from_post()`
