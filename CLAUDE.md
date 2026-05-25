# TeamBrain — CLAUDE.md

@../../../PRINCIPES.md

ADR git-natif + MCP server mémoire décisionnelle d'équipe.
Spec complète : `../../../_ideas/TeamBrain/PROPOSITION.md`
Roadmap : `ROADMAP.md`

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
├── cli.py         # 12 commandes : init, add, list, search, show, index, serve, ui, setup, bot, scan-commits, scan-code
├── static/        # build Next.js (généré par scripts/build_frontend.sh — gitignored)
├── adr.py         # modèle ADR, lecture/écriture/search texte
├── ai.py          # génération brouillon via Ollama
├── store.py       # index sqlite-vec + embeddings Ollama
├── server.py      # FastMCP : search_decisions, get_decision, list_decisions, get_context_for_file
├── config.py      # .decisions/.teambrain.json
├── scanner.py     # Module 4 — git/code mining : Candidat, score_candidat, scanner_commits, scanner_code
└── chat/          # Module 3 — Chat bot (optionnel)
    ├── base.py         # Interface ChatPlatformAdapter + Message dataclass
    ├── bot.py          # DecisionBot : patterns + scoring Ollama + orchestration + persistance _pending
    ├── github.py       # GitHubPRCreator : branche + commit + PR (utilise repo.default_branch)
    └── adapters/
        ├── slack.py        # SlackAdapter : Socket Mode + Block Kit
        └── [teams.py]      # TeamsAdapter (à venir)

.decisions/
├── .teambrain.json          # config du repo
├── .teambrain_pending.json  # proposals en attente (runtime, gitignored)
└── teambrain.db             # index vectoriel (gitignored)
tests/
├── test_adr.py       # 11 tests
├── test_store.py     # 6 tests (embeddings mockés)
├── test_server.py    # 13 tests (résolution chemin → modules)
├── test_bot.py       # 15 tests (patterns, scoring, orchestration)
└── test_scanner.py   # 27 tests (Module 4 : _depuis_vers_git, score_candidat, scanner_commits, scanner_code, patterns_extra + Module 5 : scanner_commits_semantique)
```

## Commandes dev

```bash
# Installation
pip install -e ".[dev]"        # core + dev deps
pip install -e ".[bot]"        # core + slack-sdk + PyGithub (pour Module 3)

# Tests
pytest                         # 78 tests

# CLI
teambrain init                 # crée .decisions/ dans le repo courant
teambrain add "..."            # nouvel ADR avec brouillon Ollama
teambrain list                 # liste les ADR
teambrain search "..."         # recherche texte (sans index)
teambrain show 1               # affiche un ADR complet
teambrain index                # indexe dans sqlite-vec (qwen3-embedding:0.6b)
teambrain serve                # lance le serveur MCP stdio
teambrain setup                # configure Claude Code + Cursor
teambrain setup slack          # wizard configuration Slack — génère un app manifest à coller sur api.slack.com
teambrain bot                  # lance le chat bot Slack
teambrain bot --check          # vérifie token, DM lead, présence réelle dans chaque canal
teambrain bot --confidence 0.7 # seuil de confiance personnalisé
teambrain scan-commits                          # scanne les commits git récents (défaut : 1 semaine)
teambrain scan-commits --depuis 3m --confiance 0.8  # période et seuil personnalisés
teambrain scan-commits --no-ai                  # matchs bruts sans scoring Ollama
teambrain scan-commits --pattern "migrer"       # pattern supplémentaire (répétable, supporte regex)
teambrain scan-code                             # scanne les commentaires du code (marqueurs DECISION:, ADR:)
teambrain scan-code --pattern "CHOIX_ARCHI:"   # pattern supplémentaire (répétable)
teambrain scan-code --no-ai                     # matchs bruts sans scoring Ollama

# Interface web bundlée (Option B)
bash scripts/build_frontend.sh                 # build Next.js → src/teambrain/static/ (avant pip install)
teambrain ui                                   # API + UI + ouverture navigateur (port 8003)
teambrain ui --repo /path/sand --repo /path/tb # multi-projets
teambrain ui --base /path/to/projets/          # auto-détection
```

## État des modules

- **Module 1** : ✅ CLI + format ADR + add (Ollama) + search texte
- **Module 2** : ✅ MCP server + sqlite-vec + mapping chemin→modules
- **Module 3** : ✅ Chat bot — Socket Mode Slack + Block Kit + patterns + scoring Ollama + PR GitHub
- **Module 4** : ✅ Git/Code mining — scan-commits + scan-code + scoring Ollama + boucle interactive
- **Module 5** : ✅ Scanner sémantique — comparaison embeddings vs index ADR, flag --semantic, distance cosine
- **Audit sécurité/qualité** : ✅ 14 corrections (2026-05-14) — injection format string, permissions tokens, race condition threading, etc.
- **Améliorations Slack** : ✅ wizard manifest + check canaux réel + persistance proposals (2026-05-14)
- **Module 6** : ✅ Interface web (2026-05-20) — API REST FastAPI (`teambrain serve --http`, port 8003) + frontend `teambrain-web/` (Next.js 16, port 3003). Routes : liste, détail, recherche, création guidée (brouillon Ollama). 25 tests API, 103 au total.
- **Corrections UX (2026-05-21)** : template modules vide par défaut, langue forcée en français dans `ai.py`, affichage conséquences structurées (dict Python → listes +/−), `/nouveau` adaptatif selon `ollama_disponible`.
- **Option B packaging (2026-05-21)** : ✅ `teambrain ui` — frontend statique bundlé dans le package Python. 107 tests. Zéro Node.js requis à l'exécution.
- **Audit sécurité (2026-05-22)** : ✅ 7 corrections — path traversal serve_static, starlette 1.0.1, host 127.0.0.1, /health info disclosure, max_length draft, écriture atomique MCP setup, pytest 9.0.3.
- **README v1.0 + version bump (2026-05-22)** : ✅ README complet, version 1.0.0 dans pyproject.toml.
- **Décision UI (2026-05-22)** : `teambrain ui` passera de `webbrowser.open()` → **PyWebView** (fenêtre native WebKit). Séquence : (1) modifs UI sur le frontend Next.js d'abord, (2) intégration PyWebView. Publication v1.0.0 après.
- **Module 7 — Édition/suppression (2026-05-23)** : ✅ Tous les champs d'un ADR sont éditables depuis l'interface web. Suppression avec confirmation en ligne. `DELETE /adr/{projet}/{adr_id}` ajouté à l'API. 116 tests Python (+ 9), 19 tests Playwright e2e (nouveau).
- **Recherche GitHub-style (2026-05-25)** : ✅ Syntaxe qualificatifs (`statut:`, `module:`, `decideur:`, `projet:`, `in:`), phrases exactes, regex, exclusions `-terme`. `parse_query()` + `search_adrs()` côté backend. Badges visuels live + panneau aide syntaxe côté frontend.
- **Recherche sémantique UI (2026-05-25)** : ✅ Checkbox toujours visible (désactivée avec tooltip si Ollama absent ou aucun index). Panneau "Index sémantique" collapsible par projet : statut badge (Indexé/En cours/Erreur), boutons Indexer/Ré-indexer, polling 2s. `POST /index/{projet}` (async thread) + `GET /index/{projet}`. `/projects` expose `index_disponible`. `/health` expose `ollama_disponible`.

## Roadmap — prochaines évolutions

### Orientation réseau (décision 2026-05-14)

TeamBrain est un **outil d'équipe multi-machine** — les composants n'ont pas vocation à tourner sur la même machine. L'architecture cible est :

```
[repo git] ← teambrain CLI  (machine développeur)
                │
                ▼
         [SemanticMatch]     (service HTTP partagé, réseau interne ou cloud)
                │
                ▼
         [teambrain MCP]     (server MCP, peut tourner ailleurs)
                │
                ▼
         [Slack bot]         (machine dédiée ou container)
```

Ollama reste utilisé **localement** pour la génération de brouillons ADR (`teambrain add`) et les embeddings (`teambrain index`). Il n'est plus en chemin critique pour le scanner.

### **Module 5** : ✅ Scanner sémantique — sqlite-vec local, `--semantic` sur `scan-commits`

Le scanner sémantique compare chaque commit directement à l'index ADR via sqlite-vec (embeddings locaux Ollama), sans patterns regex ni SemanticMatch externe.

- `scanner_commits_semantique(chemin_repo, decisions_dir, config, depuis, seuil_distance, embed_fn)` dans `scanner.py`
- Flag CLI : `teambrain scan-commits --semantic`
- Seuil par défaut : `seuil_distance=0.3` (distance cosine — 0=identique, 1=orthogonal)
- Confiance calculée : `1.0 - distance` (normalisée 0-1)

**Architecture** : l'index sqlite-vec est créé localement par `teambrain index`. Pas de dépendance réseau en mode sémantique.

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

### Wizard de configuration

`teambrain setup slack` génère un **app manifest Slack** prêt à coller sur `api.slack.com` (From an app manifest). Scopes OAuth, Event Subscriptions, Socket Mode et Interactivity sont préconfigurés automatiquement — l'utilisateur n'a plus qu'à coller le manifest, générer les tokens et inviter le bot dans ses canaux.

### Flux de détection

1. **Écoute** : Socket Mode capte tous les messages des canaux
2. **Candidature** : regex patterns rapides sur le texte (`"on a décidé"`, `"on va partir sur"`, etc.)
3. **Scoring** : Ollama évalue si c'est vraiment une décision architecturale + confidence
4. **Proposition** : DM au tech lead avec boutons Block Kit (Valider / Éditer / Ignorer)
5. **Validation** : Action → sauvegarde ADR + création PR GitHub (optionnel)

Les propositions en attente sont **persistées** dans `.decisions/.teambrain_pending.json` — elles survivent aux redémarrages du bot.

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

## Module 4 — Git/Code Mining

### Architecture

`scanner.py` expose deux fonctions principales utilisées par les commandes CLI :

- `scanner_commits(chemin_repo, depuis, model, confiance_min, score_ia=True, patterns_extra=None)` : git log via subprocess, filtrage sur les patterns décisionnels, scoring Ollama optionnel
- `scanner_code(chemin_repo, patterns_extra, model, confiance_min, score_ia=True)` : rglob sur tous les fichiers texte, skip binaires + DOSSIERS_IGNORES, scoring Ollama optionnel
- `score_candidat(texte, model)` : appel Ollama, gère le wrapping ```json```, normalise les types
- `_match_patterns(texte, patterns)` : matching regex via `re.search()` avec fallback sous-chaîne si pattern invalide

Le paramètre `score_ia=False` retourne les candidats bruts (confiance=1.0, resume="") sans appeler Ollama — utilisé par `--no-ai`.

### Flux interactif

Pour chaque candidat retenu → Panel rich avec source/ref/date/auteur/résumé/confiance → prompt [v]alider / [i]gnorer / [a]rrêter → si validé : `generate_draft()` → `save_adr()`.

### Patterns par défaut

Commits : `"on a décidé"`, `"on va partir sur"`, `"on abandonne"`, `"décision :"`, `"DECISION:"`, `"ADR:"`, `"on choisit"`, `"we decided"`, `"decided to"`

Code : `"DECISION:"`, `"ADR:"`, `"# decision"`, `"// decision"`

Dossiers ignorés : `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.tox`, `dist`, `build`

### Patterns personnalisés par repo

Les commandes `scan-commits` et `scan-code` fusionnent les patterns par défaut avec :
1. Les options `--pattern` passées en ligne de commande
2. Les champs `commit_patterns` et `code_patterns` dans `.decisions/.teambrain.json`

Les patterns supportent la **regex** (`re.search`, insensible à la casse) — fallback sous-chaîne si le pattern est invalide.

Exemple pour un repo style Conventional Commits français (ex: SAND) :

```json
{
  "commit_patterns": [
    "migrer",
    "remplacer .+ par",
    "upgrade|upgrader",
    "intégrer",
    "architecture",
    "forcer .+ via",
    "postgres|redis|sentry|docker|ltree"
  ],
  "code_patterns": [
    "CHOIX_ARCHI:"
  ]
}
```

## API HTTP — Points clés (Module 6)

- `GET /health` expose `ollama_disponible` (ping `ollama.list()` à chaque appel) — utilisé par le frontend `/nouveau` pour brancher sur le bon flux.
- Le serveur Next.js (`teambrain-web/`) doit être redémarré si l'API n'était pas encore lancée au démarrage — Next.js cache les 404 serveur, même avec `revalidate: 0`.
- Lancer l'API avec `--repo "nom:/chemin"` est invalide — utiliser `--repo "/chemin"` (le nom est déduit du dossier parent).

## Pièges connus

**Modules 1-2** :
- `ollama.chat()` peut wrapper le JSON dans ```json``` malgré le prompt système → nettoyage dans `ai.py`
- `python-frontmatter` : les dates YAML peuvent être retournées en `date` ou `str` selon le contexte → normalisation dans `from_post()`
- `get_context_for_file()` : utilise `module_mappings` si présent, sinon fallback sur les segments du chemin. Pour les gros projets, configurer les mappings explicites.

**Module 3** :
- Socket Mode : `SocketModeClient.connect()` est non-blocking → `threading.Event().wait()` pour maintenir le process vivant.
- Block Kit payload : le user ID est dans `payload["user"]["id"]`, pas `payload["user_id"]` (piège confirmé en test live).
- `_pending` est persisté dans `.decisions/.teambrain_pending.json` — rechargé au démarrage. Les vieux DM Block Kit restent actifs après un restart.
- Le bot doit être **invité dans chaque canal** via `/invite @BotName` — `teambrain bot --check` vérifie maintenant la présence réelle (✓/✗ par canal).
- Scopes OAuth requis : `channels:read channels:history groups:read groups:history im:history chat:write im:write users:read`. Oublier `channels:read` ou `groups:read` empêche la réception des événements. Le wizard `setup slack` les configure automatiquement via le manifest.
- Ollama scoring : ~500ms par message. Pour <50 msg/jour c'est OK, au-delà envisager un cache ou batch.
- Token expiration : Slack bot tokens ne se renouvellent pas automatiquement. Relancer le bot en cas de 401.
- `teambrain bot --check` pour diagnostiquer avant de lancer (vérifie token, présence dans les canaux via `conversations_list`, DM lead).

**Module 4** :
- `_depuis_vers_git` utilise `re.fullmatch(r"(\d+)([wmy])")` — le suffixe `y` de `"yesterday"` ne matche pas car il n'est pas précédé d'un chiffre (piège évité par le fullmatch).
- `scanner_commits` ne scanne que le sujet du commit (`%s`), pas le corps (`%b`). Les décisions dans le corps du message sont manquées. À étendre si besoin.
- `score_candidat` lève `ValueError` sur JSON malformé — absorbé avec `logger.warning` dans les scanners. Surveiller les logs si le nombre de candidats semble anormalement bas.
- `scanner_code` en mode `score_ia=True` peut être lent sur de gros repos (1 appel Ollama par ligne matchant). Utiliser `--no-ai` pour un premier balayage rapide, puis scorer manuellement.
- Les patterns par défaut (`PATTERNS_COMMIT`) sont des sous-chaînes simples ("on a décidé"…) — ils ne matchent pas les styles Conventional Commits ("migrer", "remplacer"). Configurer `commit_patterns` dans `.teambrain.json` selon le style du repo cible.
- Les patterns dans `commit_patterns` et `--pattern` supportent regex (`re.search`) : `"postgres|redis"` fonctionne, pas besoin de deux entrées séparées.
- `qwen3:1.7b` est très conservateur sur des commits courts sans contexte narratif — sur SAND (Conventional Commits), il n'en retient que 2/34 avec seuil 0.7. Préférer `--no-ai` + sélection manuelle pour les repos à messages de commit courts.
- Le template `_USER` dans `ai.py` utilise `["liste", "des", "modules", "concernés"]` comme exemple de modules. qwen3:1.7b le prend parfois au pied de la lettre → corriger manuellement les ADR générés concernés.
- `scan-commits` / `scan-code` ne sont pas interactifs via le préfixe `!` de Claude Code (stdin non connecté). Lancer dans un vrai terminal ou piper des réponses (`printf 'i\n%.0s' {1..50} | teambrain scan-commits`) pour afficher la liste sans créer d'ADR.

**Module 6 — Interface web** :
- `ai.py` : qwen3:1.7b copie les valeurs d'exemple du template JSON (ex: `["liste", "des", "modules", "concernés"]`) → toujours mettre `[]` comme valeur par défaut pour les listes, jamais une liste d'exemple.
- `ai.py` : qwen3:1.7b génère en anglais si le prompt système ne force pas explicitement la langue (`Rédige TOUJOURS en français`).
- `ai.py` : les conséquences peuvent être retournées sous forme de dict Python stringifié `{'positives': [...], 'négatives': [...]}` ou objet JSON — `consequencesVersTexte()` dans `nouveau/page.tsx` gère les deux cas (string ou objet).
- Next.js server component + API locale : si le serveur Next.js démarre avant l'API FastAPI, les pages qui fetchent côté serveur retournent 404 et mettent en cache ce résultat. Toujours démarrer l'API *avant* le frontend, ou redémarrer Next.js après l'API.
- `teambrain serve --http` : le flag `--repo` attend un chemin absolu seul (`--repo "/chemin"`), pas un alias `"nom:/chemin"`.

**Option B — packaging** :
- `scripts/build_frontend.sh` doit être lancé avant `pip install -e .` (ou `hatch build`) — `src/teambrain/static/` est gitignored mais embarqué dans le wheel via `artifacts` hatchling.
- Route dynamique Next.js `/adr/[projet]/[id]` incompatible avec `output: 'export'` → convertie en `/adr/?projet=X&id=Y` (query params, page statique client).
- Routes FastAPI catch-all `@app.api_route("/{path:path}", methods=["GET", "HEAD"])` ajoutées **après** toutes les routes API → les routes explicites ont la priorité.
- `redirect_slashes` doit rester à `True` (défaut FastAPI) — les pages statiques sont servies via les routes catch-all, pas via un mount Starlette.
- `request: Request` dans les routes catch-all cause un 422 — ne pas l'inclure dans la signature si inutilisé.

**Module 5** :
- Mode sémantique : `seuil_distance` est une distance cosine (0=identique, 1=orthogonal). Défaut : 0.3. L2 est désactivé dans `store.py` via `distance_metric=cosine` — sans cette déclaration explicite, sqlite-vec utilise L2 par défaut et les scores sont incorrects (Principe 18).
- La vérification de l'index (`teambrain.db`) est faite **avant** la boucle des commits — une `RuntimeError` est levée immédiatement si le fichier est absent, sans attendre le premier commit.

**Module 7 — Édition/suppression ADR (2026-05-23)** :
- `DELETE /adr/{projet}/{adr_id}` retourne 204 (No Content) — `apiFetch` ne peut pas parser un body vide avec `r.json()` → wrapper séparé dans `api.ts` qui vérifie `r.ok` sans appeler `.json()`.
- `PUT /adr/{projet}/{adr_id}` : si le titre change, `save_adr()` crée un nouveau fichier avec le nouveau slug — l'ancien fichier doit être supprimé explicitement (`ancien_path.unlink()`) sinon les deux coexistent.
- `ADRPayload` accepte `date: str | None` — toujours valider avec `date.fromisoformat()` et fallback sur `existant.date` en cas d'exception : ne pas laisser une date invalide propager un 422.
- **Playwright + `getByLabel` et labels avec span enfant** : un `<label>` contenant du texte + un `<span>` (ex: hint) ne se résout pas proprement via `getByLabel("texte")` sans `htmlFor`/`id`. Ajouter systématiquement `htmlFor` sur les labels et `id` sur les inputs/textareas des formulaires.
- **Playwright + Next.js static export** : les liens générés par Next.js en mode `output: 'export'` ont un trailing slash (`/nouveau/` au lieu de `/nouveau`) — utiliser un matcher regex (`/\/nouveau/`) plutôt qu'une égalité stricte dans les assertions `toHaveAttribute("href", ...)`.
- **Tests e2e avec données réelles** : créer les ADR de test via `request.post()` dans `beforeAll`/`beforeEach` et les supprimer dans `afterAll` — ne jamais dépendre d'un ID fixe du jeu de données réel (fragile si l'ADR est édité ou supprimé).

**Recherche GitHub-style (2026-05-25)** :
- **Redémarrage serveur obligatoire** après modification de `adr.py` ou `http_api.py` — Python charge les modules en mémoire au démarrage, `pip install -e .` (editable) ne suffit pas. Killer le PID et relancer `teambrain ui`.
- `parse_query()` est appelé dans `http_api.py` pour extraire `projet:X` de la query et l'utiliser comme filtre de projet avant d'appeler `search_adrs`. Passer `req=` à `search_adrs` évite le double parsing.
- `search_adrs` avec uniquement des qualificatifs (sans termes full-text) retourne `score=1.0` — c'est le comportement voulu pour `statut:accepte` seul.

**Recherche sémantique + indexation UI (2026-05-25)** :
- `POST /index/{projet}` lance `reindex()` dans `loop.run_in_executor(None, ...)` pour ne pas bloquer l'event loop FastAPI. L'état est stocké dans `_index_statuts` dict en mémoire (reset au redémarrage du serveur).
- `_index_statuts` est initialisé à `statut="ok"` si `teambrain.db` existe déjà, sinon `"idle"` — évite un faux "Pas d'index" au premier chargement.
- Polling côté frontend : `setTimeout` récursif toutes les 2s tant que `statut === "en_cours"`, avec auto-refresh de `/projects` quand la tâche se termine (pour mettre à jour `index_disponible`).
- `fastapi` n'est pas installé dans le Python système (`/opt/homebrew/lib/python3.14`) — le binaire `teambrain` utilise `/opt/homebrew/opt/python@3.14/bin/python3.14`. Installer les deps avec `/opt/homebrew/opt/python@3.14/bin/pip3 install "fastapi[standard]~=0.115" --break-system-packages`.
- La checkbox sémantique reste toujours dans le DOM (même désactivée) — `opacity-50 cursor-not-allowed` communique l'état sans retirer la feature de la vue.

**Refonte visuelle GitHub-style (2026-05-25)** :
- **`overflow-hidden` sur un conteneur coupe les tooltips `absolute bottom-full`** (qui sortent vers le haut) — même avec `z-index` élevé. Fix : retirer `overflow-hidden` du conteneur parent, ajouter `rounded-t-md` sur le header et `last:rounded-b-md` sur les items de liste pour conserver les coins arrondis.
- **Playwright `getByRole("link", { name: X })` fait une correspondance insensible à la casse et sous-chaîne** — "TeamBrain" (logo Nav, href="/") matche la recherche `{ name: "teambrain" }`. Toujours scoper avec `page.locator("main").getByRole(...)` pour éviter les faux positifs du logo dans la nav.
- **Named groups Tailwind v4 (`group/tab-actifs`)** : bien supportés mais inutiles si l'ancêtre a `overflow-hidden` — le tooltip n'est pas rendu visible même si les classes CSS sont présentes.
