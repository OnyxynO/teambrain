"""Client HTTP pour le service SemanticMatch (/classify)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

_QUESTION = "Ce texte décrit-il une décision architecturale ?"
_CONTEXT = "historique git ou commentaire de code d'un projet logiciel"


def classifier(texte: str, url: str) -> dict:
    """Appelle /classify sur SemanticMatch et retourne un dict normalisé.

    Returns:
        {"est_decision": bool, "confiance": float, "resume": str}

    Raises:
        ConnectionError: si le service est inaccessible.
        ValueError: si la réponse est invalide ou signale une erreur HTTP.
    """
    payload = json.dumps({
        "query": texte,
        "question": _QUESTION,
        "context": _CONTEXT,
    }).encode()
    req = urllib.request.Request(
        f"{url}/classify",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise ValueError(f"SemanticMatch a retourné HTTP {exc.code} : {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ConnectionError(f"SemanticMatch inaccessible ({url}) : {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Réponse JSON invalide de SemanticMatch : {exc}") from exc

    try:
        return {
            "est_decision": bool(data["answer"]),
            "confiance": float(data["confidence"]),
            "resume": str(data["reason"]),
        }
    except KeyError as exc:
        raise ValueError(f"Champ manquant dans la réponse SemanticMatch : {exc}") from exc
