from __future__ import annotations
import logging
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from ..base import ChatPlatformAdapter, Message

logger = logging.getLogger(__name__)


class SlackAdapter(ChatPlatformAdapter):
    """Adaptateur Slack utilisant Socket Mode (WebSocket local) et Block Kit interactif."""

    def __init__(self, bot_token: str, app_token: str):
        """Initialise le client Slack avec tokens.

        Args:
            bot_token: Token du bot (xoxb-...)
            app_token: Token Socket Mode (xapp-...)
        """
        self.web_client = WebClient(token=bot_token)
        self.socket_client = SocketModeClient(
            app_token=app_token,
            web_client=self.web_client,
        )

    def listen(self, channels: list[str], on_message, on_action) -> None:
        """Lance l'écoute Socket Mode sur les canaux donnés."""

        def handle_events_api(client: SocketModeClient, req: SocketModeRequest) -> None:
            """Traite les événements API (messages)."""
            if req.type == "events_api":
                event = req.payload.get("event", {})
                if event.get("type") == "message":
                    msg = Message(
                        id=event.get("ts", ""),
                        channel=event.get("channel", ""),
                        thread_ts=event.get("thread_ts"),
                        text=event.get("text", ""),
                        user_id=event.get("user", ""),
                    )
                    try:
                        on_message(msg)
                    except Exception:
                        logger.exception("Erreur traitement message")

                client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

        def handle_interactive(client: SocketModeClient, req: SocketModeRequest) -> None:
            """Traite les actions interactives (boutons Block Kit)."""
            if req.type == "interactive":
                payload = req.payload
                action = payload.get("actions", [{}])[0]
                action_id = action.get("action_id", "")
                if action_id:
                    try:
                        on_action(action_id, payload)
                    except Exception:
                        logger.exception("Erreur traitement action")

                client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

        self.socket_client.socket_mode_request_listeners.append(handle_events_api)
        self.socket_client.socket_mode_request_listeners.append(handle_interactive)

        try:
            self.socket_client.connect()
        except KeyboardInterrupt:
            pass
        finally:
            self.socket_client.close()

    def send_dm(self, user_id: str, text: str) -> str:
        """Envoie un DM à l'utilisateur."""
        response = self.web_client.conversations_open(users=user_id)
        channel_id = response["channel"]["id"]
        msg = self.web_client.chat_postMessage(channel=channel_id, text=text)
        return msg["ts"]

    def send_proposal(self, user_id: str, adr_draft: dict, context: str, proposal_id: str) -> str:
        """Envoie une proposition d'ADR avec boutons Block Kit."""
        blocks = self._build_proposal_blocks(adr_draft, context, proposal_id)

        response = self.web_client.conversations_open(users=user_id)
        channel_id = response["channel"]["id"]

        msg = self.web_client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text="Nouvelle décision détectée",
        )
        return msg["ts"]

    def reply_thread(self, channel: str, thread_ts: str, text: str) -> None:
        """Répond dans un thread."""
        self.web_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=text,
        )

    def _build_proposal_blocks(self, adr_draft: dict, context: str, proposal_id: str) -> list[dict]:
        """Construit les blocs Block Kit pour la proposition d'ADR."""
        titre = adr_draft.get("titre", "Sans titre")
        decision_preview = adr_draft.get("decision", "")[:100]

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📋 Décision détectée",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{titre}*\n{context}",
                },
            },
            {
                "type": "divider",
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"**Contexte**\n{adr_draft.get('contexte', '—')}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"**Décision**\n{decision_preview}...",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Valider",
                        },
                        "value": "validate",
                        "action_id": f"validate_{proposal_id}",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✏️ Éditer",
                        },
                        "value": "edit",
                        "action_id": f"edit_{proposal_id}",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🚫 Ignorer",
                        },
                        "value": "ignore",
                        "action_id": f"ignore_{proposal_id}",
                        "style": "danger",
                    },
                ],
            },
        ]
