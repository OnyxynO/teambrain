#!/usr/bin/env bash
# Build le frontend Next.js et copie le résultat dans src/teambrain/static/
# à lancer depuis la racine du projet teambrain avant un pip install -e . ou hatch build

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "▶ Build du frontend..."
cd "$ROOT_DIR/teambrain-web"
NEXT_PUBLIC_API_URL="" bun run build

echo "▶ Copie dans src/teambrain/static/..."
rm -rf "$ROOT_DIR/src/teambrain/static"
cp -r out/ "$ROOT_DIR/src/teambrain/static"

echo "✓ Frontend prêt dans src/teambrain/static/"
