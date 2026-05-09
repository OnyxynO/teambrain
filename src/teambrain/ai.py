from __future__ import annotations
import json

import ollama

_SYSTEM = """Tu es un expert en Architecture Decision Records (ADR).
Génère un brouillon d'ADR en JSON à partir d'une description.
Réponds uniquement avec un objet JSON valide, sans markdown ni explication."""

_USER = """Description : {description}

Génère un ADR avec exactement ces champs JSON :
{{
  "titre": "titre court et descriptif de la décision",
  "modules": ["liste", "des", "modules", "concernés"],
  "decideurs": [],
  "contexte": "contexte et contraintes qui ont mené à cette décision",
  "decision": "la décision prise et pourquoi",
  "consequences": "conséquences positives et négatives"
}}"""


def generate_draft(description: str, model: str) -> dict:
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _USER.format(description=description)},
        ],
        options={"temperature": 0.3},
    )
    content = response.message.content.strip()
    # Ollama peut envelopper la réponse dans des blocs ```json malgré le prompt
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])
    return json.loads(content)
