from __future__ import annotations
import json

import ollama

_SYSTEM = """Tu es un expert en Architecture Decision Records (ADR).
Génère un brouillon d'ADR en JSON à partir d'une description.
Réponds UNIQUEMENT avec un objet JSON valide, sans markdown ni explication.
Rédige TOUJOURS en français, quelle que soit la langue de la description."""

_USER_SUFFIX = """

Génère un ADR avec exactement ces champs JSON :
{
  "titre": "titre court et descriptif de la décision",
  "modules": [],
  "decideurs": [],
  "contexte": "contexte et contraintes qui ont mené à cette décision",
  "decision": "la décision prise et pourquoi",
  "consequences": "conséquences positives et négatives"
}

Le champ "modules" doit contenir les noms des composants ou couches techniques concernés (ex: ["auth", "api"]), ou rester vide si inconnu."""


def generate_draft(description: str, model: str) -> dict:
    user_content = f"Description : {description}" + _USER_SUFFIX
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_content},
        ],
        options={"temperature": 0.3},
    )
    content = response.message.content.strip()
    # Ollama peut envelopper la réponse dans des blocs ```json malgré le prompt
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Réponse JSON malformée : {exc}\nContenu : {content!r}") from exc
