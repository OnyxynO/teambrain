# ROADMAP — TeamBrain

> Document vivant. Modules ordonnés par priorité — les durées sont indicatives.

---

## État actuel (mai 2026)

| Module | État | Description |
|---|---|---|
| Module 1 — Core CLI | ✅ livré | ADR git-natif, `add` / `list` / `search` / `show` / `index` |
| Module 2 — MCP Server | ✅ livré | Expose les ADR aux AI agents via FastMCP stdio |
| Module 3 — Chat Bot | ✅ livré | Slack Socket Mode + Block Kit + persistance proposals |
| Module 4 — Git/Code Mining | ✅ livré | `scan-commits` + `scan-code` + scoring Ollama |
| Module 5 — Scanner sémantique | ✅ livré | `--semantic` sur `scan-commits`, sqlite-vec cosine |
| Audit sécurité/qualité | ✅ livré | 14 corrections (injection, permissions, threading) |
| Module 6 — Interface web | ✅ livré | API REST FastAPI + frontend Next.js 16, multi-projets, /nouveau adaptatif Ollama |
| **Publication v1.0** | 🔜 priorité | Packaging, distribution, README quick start — voir section dédiée |

---

## Module 6 — Interface web (cible : non-devs)

**Objectif :** rendre TeamBrain accessible aux membres non-techniques d'une équipe (chef de projet, product owner, designer) sans passer par le terminal.

**Problème résolu :** les décisions les plus importantes viennent souvent de personnes qui ne touchent pas au code. Si la capture passe uniquement par le CLI ou les commits git, ces décisions sont perdues. Un chef de projet ne va pas ouvrir un terminal.

### Décision d'architecture : local uniquement

L'interface web tourne sur la **même machine que le repo git** — elle lit les fichiers ADR directement depuis le système de fichiers, pas via une API distante. Pas de déploiement cloud, pas de synchro, pas d'auth complexe.

Accès équipe : le tech lead lance `teambrain serve --http`, les collègues accèdent via l'IP locale ou un SSH forward. Convient pour une petite équipe co-localisée ou en VPN.

### Stack cible
- Next.js 16 + React 19 + TypeScript + Tailwind v4
- Tourne en local uniquement (`localhost` ou réseau interne)
- Consomme l'API REST FastAPI locale (à créer — voir ci-dessous)

### Fonctionnalités cibles

#### Vue principale — liste des ADR
- Tableau paginé : titre, date, statut (badge coloré), modules concernés
- Filtres : statut (proposé / accepté / déprécié), module, décideur
- Recherche full-text et sémantique (si index sqlite-vec disponible)

#### Création d'un ADR (sans CLI)
- Formulaire guidé : titre → contexte → décision → conséquences
- Génération du brouillon via Ollama (appel à l'API backend)
- Prévisualisation Markdown avant validation
- Bouton "Valider → sauvegarder dans git"

#### Vue détail d'un ADR
- Rendu Markdown complet
- Historique git de l'ADR (auteur, date, diff)
- Lien vers les fichiers du repo concernés (si `module_mappings` configuré)

#### Tableau de bord (optionnel, phase 2)
- Frise chronologique des décisions
- Carte des modules et leurs ADR liés
- Alertes : ADR en statut "proposé" depuis >30j sans validation

### API REST à créer dans TeamBrain (backend)

TeamBrain expose actuellement un **serveur MCP** (stdio) — pas une API HTTP. Il faudra ajouter une couche HTTP FastAPI pour que l'interface web puisse communiquer :

| Endpoint | Rôle |
|---|---|
| `GET /adr` | Lister les ADR (filtres : statut, module) |
| `GET /adr/{id}` | Détail d'un ADR |
| `POST /adr` | Créer un ADR (sauvegarde dans git) |
| `PUT /adr/{id}` | Modifier un ADR |
| `GET /adr/search?q=...` | Recherche texte + sémantique |
| `POST /adr/draft` | Générer un brouillon via Ollama |
| `GET /referentiels` | Lister les modules détectés dans le repo |

Port cible : **8003** (après NormMatch 8002, SemanticMatch 8001).

### Séquence de développement recommandée

1. **API REST FastAPI** dans `teambrain serve --http` (port 8003)
   — CORS configuré pour le frontend local
2. **Scaffold Next.js** (`teambrain-web/`)
3. **Liste + recherche** — lecture seule, déjà utile
4. **Création guidée** — formulaire + brouillon Ollama
5. **Auth** — aucune pour l'instant (réseau local de confiance) ; IP whitelist ou token Bearer si besoin

### Utilisateurs cibles

| Profil | Usage principal |
|---|---|
| Chef de projet | Créer des ADR depuis les réunions, consulter l'historique |
| Product owner | Retrouver "pourquoi on a fait ça" sans déranger les devs |
| Designer | Comprendre les contraintes techniques qui impactent l'UX |
| Dev junior | Onboarding : lire les décisions passées en contexte |
| AI agent (Claude/Cursor) | Consomme via MCP (inchangé) |

---

## Publication v1.0 — Packaging et distribution

**Objectif :** rendre TeamBrain installable et utilisable par n'importe qui en quelques minutes, sur le modèle d'ICSMulti (release GitHub propre, documentation claire).

### Question ouverte : architecture de distribution

Deux options à trancher avant de coder :

| Option | Avantages | Inconvénients |
|---|---|---|
| **A — Deux processus séparés** | Simple à implémenter, stack inchangée | L'utilisateur doit lancer API + frontend manuellement, DX médiocre |
| **B — Frontend bundlé dans Python** | `teambrain ui` lance tout d'un coup, DX excellente | Build Next.js à embarquer dans le package, complexité CI/CD |

**Recommandation :** Option B avec une commande `teambrain ui` qui :
1. Lance l'API FastAPI (`--http`) en arrière-plan
2. Sert le frontend Next.js **pré-buildé** (fichiers statiques via FastAPI `StaticFiles`)
3. Ouvre le navigateur sur `http://localhost:8003`

Le build Next.js (`bun run build` → `out/`) est inclus dans le package Python via `package_data`. L'utilisateur n'a pas besoin de Node.js installé.

### Tâches

#### Packaging
- [ ] Décision finale Option A ou B
- [ ] Si B : script de build `scripts/build_frontend.sh` + intégration dans `pyproject.toml` (`package_data`)
- [ ] Commande `teambrain ui` dans `cli.py` (lance API + ouvre navigateur)
- [ ] Tester `pip install teambrain` depuis zéro sur une machine propre

#### Documentation
- [ ] README refondu : quick start en 3 commandes (`pip install` → `teambrain init` → `teambrain ui`)
- [ ] Section "Sans Ollama" (création manuelle, pas de brouillon IA)
- [ ] Section "Multi-projets" (`--repo` répétable)
- [ ] `EXAMPLE_CONFIG.md` mis à jour

#### Release
- [ ] Bump version → **v1.0.0** dans `pyproject.toml`
- [ ] GitHub Release avec tag `v1.0.0` + changelog
- [ ] Décision : publier sur PyPI ou GitHub Releases uniquement ?

### Prérequis à valider avant release

- Tests existants verts sur machine propre (sans `.decisions/` pré-existant)
- `teambrain init` + `teambrain add` + `teambrain ui` : parcours complet fonctionnel
- Frontend buildé testé dans le contexte servi par FastAPI (pas juste en dev Next.js)

---

## Module 7 — Éditeur collaboratif (idée, non planifié)

- Edition simultanée d'un ADR (WebSocket ou polling)
- Commentaires inline par section
- Workflow de validation formelle (propose → review → accepte)

---

## Voir aussi

- `CLAUDE.md` — stack, commandes dev, pièges connus
- `_ideas/TeamBrain/PROPOSITION.md` — vision produit complète
