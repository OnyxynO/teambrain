from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import Callable


@dataclass
class Message:
    """Représentation normalisée d'un message entre plateformes de chat."""
    id: str
    channel: str
    thread_ts: str | None
    text: str
    user_id: str


class ChatPlatformAdapter(ABC):
    """Interface abstraite pour les adaptateurs de plateforme de chat."""

    @abstractmethod
    def listen(
        self,
        channels: list[str],
        on_message: Callable,
        on_action: Callable,
    ) -> None:
        """Écoute les messages et actions sur les canaux donnés.

        Args:
            channels: Liste des canaux à écouter
            on_message: Callback(msg: Message) appelé pour chaque message
            on_action: Callback(action_id: str, payload: dict) pour les actions interactives
        """
        pass

    @abstractmethod
    def send_dm(self, user_id: str, text: str) -> str:
        """Envoie un message privé à un utilisateur.

        Args:
            user_id: ID de l'utilisateur cible
            text: Contenu du message (markdown supporté)

        Returns:
            ID du message envoyé (pour tracking)
        """
        pass

    @abstractmethod
    def send_proposal(self, user_id: str, adr_draft: dict, context: str, proposal_id: str) -> str:
        """Envoie une proposition d'ADR avec boutons d'action Block Kit.

        Args:
            user_id: ID du tech lead
            adr_draft: Dict contenant titre, contexte, decision, consequences
            context: Contexte d'où la décision a été détectée
            proposal_id: UUID stable pour tracker cette proposition

        Returns:
            ID du message envoyé (message_ts pour Slack)
        """
        pass

    @abstractmethod
    def reply_thread(self, channel: str, thread_ts: str, text: str) -> None:
        """Répond dans le thread d'origine du message détecté.

        Args:
            channel: Nom du canal
            thread_ts: Timestamp du message parent
            text: Réponse à poster
        """
        pass
