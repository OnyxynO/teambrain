from __future__ import annotations
import re
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from datetime import date

import ollama

from ..adr import ADR, save_adr
from .base import ChatPlatformAdapter, Message


PATTERNS = [
    r"on a décidé",
    r"on va partir sur",
    r"on abandonne .+ pour",
    r"la contrainte c['']est",
    r"on a choisi",
    r"décision(:| )",
    r"on retient",
]


def _is_candidate(text: str) -> bool:
    """Filtre rapide : le texte contient-il un pattern de décision ?"""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in PATTERNS)


def _qualify(text: str, model: str) -> dict:
    """Scoring Ollama : la détection est-elle vraiment une décision architecturale ?

    Retourne {"is_decision": bool, "confidence": float, "summary": str}
    """
    prompt = (
        "Tu es un expert en architecture logicielle. "
        "Analyse le texte suivant pour déterminer s'il décrit une décision architecturale "
        "(technologie choisie, pattern adopté, trade-off évalué, contrainte acceptée).\n\n"
        f"Texte : {text}\n\n"
        "Réponds avec un JSON : {\"is_decision\": bool, \"confidence\": float (0-1), \"summary\": str}\n"
        "Le summary explique brièvement la décision en 1-2 phrases."
    )

    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=False,
    )
    content = response.message.content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    try:
        result = json.loads(content)
        return {
            "is_decision": result.get("is_decision", False),
            "confidence": float(result.get("confidence", 0.0)),
            "summary": str(result.get("summary", "")),
        }
    except (json.JSONDecodeError, ValueError):
        return {"is_decision": False, "confidence": 0.0, "summary": "Erreur parsing"}


@dataclass
class PendingProposal:
    """ADR en attente de validation par le tech lead."""
    proposal_id: str
    message_ts: str
    adr: ADR


class DecisionBot:
    """Détecte les décisions dans les messages Slack et gère l'orchestration."""

    def __init__(
        self,
        adapter: ChatPlatformAdapter,
        decisions_dir: Path,
        config: dict,
        github_creator=None,
    ):
        self._adapter = adapter
        self._decisions_dir = decisions_dir
        self._config = config
        self._github_creator = github_creator
        self._pending: dict[str, PendingProposal] = {}

    def run(self, channels: list[str]) -> None:
        """Lance le bot : écoute les canaux et traite les messages/actions."""
        self._adapter.listen(channels, self._on_message, self._on_action)

    def _on_message(self, msg: Message) -> None:
        """Traite un message entrant.

        Flux : is_candidate → qualify → generate_draft → send_proposal
        """
        if not _is_candidate(msg.text):
            return

        qual = _qualify(msg.text, self._config.get("model", "qwen3:1.7b"))
        if not qual["is_decision"] or qual["confidence"] < self._config.get("confidence_threshold", 0.7):
            return

        adr = self._generate_draft(qual, msg)
        context = f"#{msg.channel} — {msg.text[:100]}"
        proposal_id = str(uuid.uuid4())

        message_ts = self._adapter.send_proposal(
            self._config.get("lead_user_id", ""),
            {
                "titre": adr.titre,
                "contexte": adr.contexte,
                "decision": adr.decision,
                "consequences": adr.consequences,
            },
            context,
            proposal_id,
        )

        self._pending[proposal_id] = PendingProposal(proposal_id, message_ts, adr)

    def _generate_draft(self, qual: dict, msg: Message) -> ADR:
        """Crée un brouillon d'ADR à partir de la qualification Ollama."""
        adr = ADR(
            id=self._next_id(),
            titre=qual["summary"].split("\n")[0][:80],
            date=date.today(),
            statut="propose",
            modules=["détecté-auto"],
            decideurs=[],
            contexte=qual["summary"],
            decision=msg.text[:500],
            consequences="À déterminer.",
        )
        return adr

    def _next_id(self) -> int:
        """Retourne le prochain ID d'ADR disponible."""
        from ..adr import list_adrs
        adrs = list_adrs(self._decisions_dir)
        return (max([a.id for a in adrs]) if adrs else 0) + 1

    def _on_action(self, action_id: str, payload: dict) -> None:
        """Traite les actions interactives (Valider / Éditer / Ignorer)."""
        if action_id.startswith("validate_"):
            self._action_validate(action_id, payload)
        elif action_id.startswith("edit_"):
            self._action_edit(action_id, payload)
        elif action_id.startswith("ignore_"):
            self._action_ignore(action_id)

    def _action_validate(self, action_id: str, payload: dict) -> None:
        """Valide et sauvegarde l'ADR, crée une PR GitHub."""
        proposal_id = action_id.replace("validate_", "", 1)
        proposal = self._pending.pop(proposal_id, None)
        if not proposal:
            return

        adr = proposal.adr
        adr.statut = "accepte"

        save_adr(adr, self._decisions_dir)

        if self._github_creator:
            pr_url = self._github_creator.create_pr(adr, self._adr_to_markdown(adr))
            self._adapter.send_dm(
                payload.get("user_id", ""),
                f"✅ ADR #{adr.id:03d} sauvegardée.\nPR GitHub : {pr_url}",
            )
        else:
            self._adapter.send_dm(
                payload.get("user_id", ""),
                f"✅ ADR #{adr.id:03d} sauvegardée (GitHub non configuré).",
            )

    def _action_edit(self, action_id: str, payload: dict) -> None:
        """Ouvre un modal pour éditer l'ADR (à implémenter côté Slack)."""
        proposal_id = action_id.replace("edit_", "", 1)
        proposal = self._pending.get(proposal_id)
        if not proposal:
            return

        self._adapter.send_dm(
            payload.get("user_id", ""),
            f"📝 Édition de l'ADR #{proposal.adr.id:03d} — modal non encore supporté.",
        )

    def _action_ignore(self, action_id: str) -> None:
        """Supprime la proposition."""
        proposal_id = action_id.replace("ignore_", "", 1)
        self._pending.pop(proposal_id, None)

    def _adr_to_markdown(self, adr: ADR) -> str:
        """Convertit un ADR en markdown frontmatter (compatible avec from_post)."""
        from ..adr import _to_markdown
        return _to_markdown(adr)
