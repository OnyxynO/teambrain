from __future__ import annotations
import logging
import re
import json
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from datetime import date

import ollama

from ..adr import ADR, save_adr
from .base import ChatPlatformAdapter, Message

logger = logging.getLogger(__name__)


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
    system = (
        "Tu es un expert en architecture logicielle. "
        "Réponds uniquement avec un objet JSON valide, sans markdown ni explication."
    )
    prompt = (
        "Analyse le texte suivant pour déterminer s'il décrit une décision architecturale "
        "(technologie choisie, pattern adopté, trade-off évalué, contrainte acceptée).\n\n"
        f"Texte : {text}\n\n"
        'Réponds avec un JSON : {"is_decision": bool, "confidence": float (0-1), "summary": str}\n'
        "Le summary explique brièvement la décision en 1-2 phrases."
    )

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
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
        self._lock = threading.Lock()
        self._pending_path = decisions_dir / ".teambrain_pending.json"
        self._load_pending()

    def _pending_to_dict(self) -> dict:
        """Sérialise _pending en dict JSON-serialisable."""
        result = {}
        for pid, prop in self._pending.items():
            adr = prop.adr
            result[pid] = {
                "proposal_id": prop.proposal_id,
                "message_ts": prop.message_ts,
                "adr": {
                    "id": adr.id, "titre": adr.titre, "date": adr.date.isoformat(),
                    "statut": adr.statut, "modules": adr.modules, "decideurs": adr.decideurs,
                    "contexte": adr.contexte, "decision": adr.decision, "consequences": adr.consequences,
                },
            }
        return result

    def _save_pending(self) -> None:
        """Persiste _pending sur disque (appelé sous self._lock)."""
        try:
            self._pending_path.write_text(
                json.dumps(self._pending_to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Impossible de sauvegarder _pending : %s", exc)

    def _load_pending(self) -> None:
        """Charge _pending depuis disque au démarrage."""
        if not self._pending_path.exists():
            return
        try:
            data = json.loads(self._pending_path.read_text(encoding="utf-8"))
            for pid, item in data.items():
                d = item["adr"]
                adr = ADR(
                    id=d["id"], titre=d["titre"], date=date.fromisoformat(d["date"]),
                    statut=d["statut"], modules=d["modules"], decideurs=d["decideurs"],
                    contexte=d["contexte"], decision=d["decision"], consequences=d["consequences"],
                )
                self._pending[pid] = PendingProposal(item["proposal_id"], item["message_ts"], adr)
            logger.info("%d proposition(s) en attente rechargée(s) depuis disque.", len(self._pending))
        except Exception as exc:
            logger.warning("Impossible de charger _pending : %s — fichier ignoré.", exc)

    def run(self, channels: list[str]) -> None:
        """Lance le bot : écoute les canaux et traite les messages/actions."""
        self._adapter.listen(channels, self._on_message, self._on_action)

    def _on_message(self, msg: Message) -> None:
        """Traite un message entrant.

        Flux : is_candidate → qualify → generate_draft → send_proposal
        """
        if not _is_candidate(msg.text):
            logger.info("Message ignoré (pas candidat) : %s", msg.text[:60])
            return

        qual = _qualify(msg.text, self._config.get("model", "qwen3:1.7b"))
        logger.info("Scoring : is_decision=%s confidence=%.2f", qual["is_decision"], qual["confidence"])
        if not qual["is_decision"] or qual["confidence"] < self._config.get("confidence_threshold", 0.7):
            logger.info("Message écarté (seuil non atteint)")
            return

        with self._lock:
            adr = self._generate_draft(qual, msg)
            logger.info("Brouillon généré : %s", adr.titre)
            context = f"#{msg.channel} — {msg.text[:100]}"
            proposal_id = str(uuid.uuid4())
            lead = self._config.get("lead_user_id", "")
            logger.info("Envoi proposition DM à lead_user_id=%r", lead)

            message_ts = self._adapter.send_proposal(
                lead,
                {
                    "titre": adr.titre,
                    "contexte": adr.contexte,
                    "decision": adr.decision,
                    "consequences": adr.consequences,
                },
                context,
                proposal_id,
            )

            logger.info("Proposition envoyée (ts=%s) — en attente de validation", message_ts)
            self._pending[proposal_id] = PendingProposal(proposal_id, message_ts, adr)
            self._save_pending()

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
        """Retourne le prochain ID disponible (appelé sous self._lock)."""
        from ..adr import list_adrs
        adrs = list_adrs(self._decisions_dir)
        saved_max = max((a.id for a in adrs), default=0)
        pending_max = max((p.adr.id for p in self._pending.values()), default=0)
        return max(saved_max, pending_max) + 1

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
        with self._lock:
            proposal = self._pending.pop(proposal_id, None)
            self._save_pending()
        if not proposal:
            return

        adr = proposal.adr
        adr.statut = "accepte"

        save_adr(adr, self._decisions_dir)

        if self._github_creator:
            pr_url = self._github_creator.create_pr(adr, self._adr_to_markdown(adr))
            self._adapter.send_dm(
                payload.get("user", {}).get("id", ""),
                f"✅ ADR #{adr.id:03d} sauvegardée.\nPR GitHub : {pr_url}",
            )
        else:
            self._adapter.send_dm(
                payload.get("user", {}).get("id", ""),
                f"✅ ADR #{adr.id:03d} sauvegardée (GitHub non configuré).",
            )

    def _action_edit(self, action_id: str, payload: dict) -> None:
        """Ouvre un modal pour éditer l'ADR (à implémenter côté Slack)."""
        proposal_id = action_id.replace("edit_", "", 1)
        with self._lock:
            proposal = self._pending.get(proposal_id)
        if not proposal:
            return

        self._adapter.send_dm(
            payload.get("user", {}).get("id", ""),
            f"📝 Édition de l'ADR #{proposal.adr.id:03d} — modal non encore supporté.",
        )

    def _action_ignore(self, action_id: str) -> None:
        """Supprime la proposition."""
        proposal_id = action_id.replace("ignore_", "", 1)
        with self._lock:
            self._pending.pop(proposal_id, None)
            self._save_pending()

    def _adr_to_markdown(self, adr: ADR) -> str:
        """Convertit un ADR en markdown frontmatter (compatible avec from_post)."""
        from ..adr import _to_markdown
        return _to_markdown(adr)
