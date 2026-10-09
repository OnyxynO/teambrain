#!/usr/bin/env bash
# Serveur API + UI des tests E2E, sur un .decisions/ jetable.
#
# Les specs créent, modifient et suppriment des ADR : lancées contre le vrai
# dépôt, elles écrivaient dans .decisions/ (versionné) et y laissaient des ADR
# de test dès qu'un test échouait avant son nettoyage. Le projet temporaire
# s'appelle « teambrain » parce que les specs ciblent ce nom de projet.
set -euo pipefail

racine="$(cd "$(dirname "$0")/../.." && pwd)"
tmp="$(mktemp -d -t teambrain-e2e)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/teambrain/.decisions"
echo '{}' > "$tmp/teambrain/.decisions/.teambrain.json"

# Pas de `teambrain ui` : sans --browser il ouvre une fenêtre native, avec il
# ouvre le navigateur système à chaque run.
"$racine/.venv/bin/python" - "$tmp/teambrain/.decisions" <<'EOF'
import sys
from pathlib import Path

import uvicorn

import teambrain
from teambrain.http_api import create_app

static = Path(teambrain.__file__).parent / "static"
api = create_app({"teambrain": Path(sys.argv[1])}, static_dir=static)
uvicorn.run(api, host="127.0.0.1", port=8003, log_level="warning")
EOF
