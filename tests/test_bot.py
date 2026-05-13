from __future__ import annotations
from datetime import date
from unittest.mock import patch, MagicMock

from teambrain.adr import ADR
from teambrain.chat.base import Message
from teambrain.chat.bot import (
    _is_candidate,
    _qualify,
    DecisionBot,
    PendingProposal,
)


class FakeAdapter:
    """Adaptateur simulé pour les tests."""
    def __init__(self):
        self.dms: list[dict] = []
        self.proposals: list[dict] = []
        self.threads: list[dict] = []

    def listen(self, _channels, _on_message, _on_action):
        """Ne fait rien dans les tests."""
        pass

    def send_dm(self, user_id: str, text: str) -> str:
        self.dms.append({"user_id": user_id, "text": text})
        return "ts-mock"

    def send_proposal(self, user_id: str, adr_draft: dict, context: str, proposal_id: str) -> str:
        self.proposals.append({
            "user_id": user_id,
            "draft": adr_draft,
            "context": context,
            "proposal_id": proposal_id,
        })
        return "ts-proposal"

    def reply_thread(self, channel: str, thread_ts: str, text: str) -> None:
        self.threads.append({
            "channel": channel,
            "thread_ts": thread_ts,
            "text": text,
        })


class TestIsCandidate:
    """Tests pour le filtrage rapide par patterns."""

    def test_candidate_decision_accepte(self):
        """'on a décidé' est détecté."""
        assert _is_candidate("on a décidé d'utiliser Node.js")

    def test_candidate_partir_sur(self):
        """'on va partir sur' est détecté."""
        assert _is_candidate("on va partir sur PostgreSQL pour la BDD")

    def test_candidate_abandonne(self):
        """'on abandonne ... pour' est détecté."""
        assert _is_candidate("on abandonne MongoDB pour une SQL classique")

    def test_candidate_contrainte(self):
        """'la contrainte c'est' est détecté."""
        assert _is_candidate("la contrainte c'est que c'est cloud-only")

    def test_candidate_choisi(self):
        """'on a choisi' est détecté."""
        assert _is_candidate("on a choisi React pour l'UI")

    def test_candidate_decision_label(self):
        """'Décision:' est détecté."""
        assert _is_candidate("Décision: utiliser DDD")

    def test_candidate_retient(self):
        """'on retient' est détecté."""
        assert _is_candidate("on retient la solution A")

    def test_not_candidate(self):
        """Un texte sans pattern n'est pas candidat."""
        assert not _is_candidate("tu peux relancer le test?")
        assert not _is_candidate("j'ai fini mon feature")

    def test_case_insensitive(self):
        """Les patterns ignorent la casse."""
        assert _is_candidate("ON A DÉCIDÉ")


class TestQualify:
    """Tests pour le scoring Ollama."""

    @patch("teambrain.chat.bot.ollama.chat")
    def test_qualify_true_decision(self, mock_chat):
        """Ollama valide une décision architecturale."""
        mock_response = MagicMock()
        mock_response.message.content = '{"is_decision": true, "confidence": 0.95, "summary": "Adoption de Kubernetes"}'
        mock_chat.return_value = mock_response
        result = _qualify("on a décidé d'adopter Kubernetes", "test-model")
        assert result["is_decision"] is True
        assert result["confidence"] == 0.95
        assert "Kubernetes" in result["summary"]

    @patch("teambrain.chat.bot.ollama.chat")
    def test_qualify_false_decision(self, mock_chat):
        """Ollama rejette un faux positif."""
        mock_response = MagicMock()
        mock_response.message.content = '{"is_decision": false, "confidence": 0.1, "summary": "Discussion générale"}'
        mock_chat.return_value = mock_response
        result = _qualify("on a décidé de prendre un café", "test-model")
        assert result["is_decision"] is False

    @patch("teambrain.chat.bot.ollama.chat")
    def test_qualify_invalid_json(self, mock_chat):
        """Gère les réponses Ollama mal formées."""
        mock_response = MagicMock()
        mock_response.message.content = "réponse invalide"
        mock_chat.return_value = mock_response
        result = _qualify("texte", "test-model")
        assert result["is_decision"] is False
        assert result["confidence"] == 0.0


class TestDecisionBot:
    """Tests du bot lui-même."""

    def test_bot_init(self, tmp_path):
        """Le bot s'initialise correctement."""
        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path, {"model": "test", "confidence_threshold": 0.7})
        assert bot._pending == {}

    @patch("teambrain.chat.bot._qualify")
    @patch("teambrain.chat.bot._is_candidate")
    def test_on_message_not_candidate(self, mock_is_cand, mock_qualify, tmp_path):
        """Un message non-candidat est ignoré."""
        mock_is_cand.return_value = False
        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path, {})
        msg = Message(
            id="1", channel="tech", thread_ts=None,
            text="j'ai fini mon feature", user_id="U123"
        )
        bot._on_message(msg)
        assert len(adapter.proposals) == 0
        assert mock_qualify.call_count == 0

    @patch("teambrain.chat.bot._qualify")
    @patch("teambrain.chat.bot._is_candidate")
    def test_on_message_candidate_but_low_confidence(self, mock_is_cand, mock_qualify, tmp_path):
        """Un candidat avec confiance basse est rejeté."""
        mock_is_cand.return_value = True
        mock_qualify.return_value = {
            "is_decision": True,
            "confidence": 0.5,
            "summary": "Décision A"
        }
        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path, {"confidence_threshold": 0.7})
        msg = Message(
            id="1", channel="tech", thread_ts=None,
            text="on a décidé quelque chose", user_id="U123"
        )
        bot._on_message(msg)
        assert len(adapter.proposals) == 0

    @patch("teambrain.chat.bot._qualify")
    @patch("teambrain.chat.bot._is_candidate")
    def test_on_message_valid_decision(self, mock_is_cand, mock_qualify, tmp_path):
        """Un candidat avec haute confiance crée une proposition."""
        mock_is_cand.return_value = True
        mock_qualify.return_value = {
            "is_decision": True,
            "confidence": 0.95,
            "summary": "Adoption de FastAPI"
        }
        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path, {
            "model": "test",
            "confidence_threshold": 0.7,
            "lead_user_id": "U999"
        })
        msg = Message(
            id="ts-123", channel="tech", thread_ts=None,
            text="on va partir sur FastAPI pour l'API", user_id="U123"
        )
        bot._on_message(msg)
        assert len(adapter.proposals) == 1
        proposal = adapter.proposals[0]
        assert proposal["user_id"] == "U999"
        assert "FastAPI" in proposal["draft"]["titre"]

    @patch("teambrain.chat.bot.save_adr")
    def test_on_action_validate(self, mock_save, tmp_path):
        """L'action 'valider' sauvegarde l'ADR."""
        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path, {"lead_user_id": "U999"})

        adr = ADR(
            id=1,
            titre="Test ADR",
            date=date.today(),
            statut="propose",
            modules=[],
            decideurs=[],
            contexte="ctx",
            decision="dec",
            consequences="cons"
        )
        proposal_id = "test-proposal-123"
        bot._pending[proposal_id] = PendingProposal(proposal_id, "ts-proposal", adr)

        bot._on_action(f"validate_{proposal_id}", {"user_id": "U999"})

        assert mock_save.called
        assert len(bot._pending) == 0
        assert len(adapter.dms) == 1

    def test_on_action_ignore(self, tmp_path):
        """L'action 'ignorer' supprime la proposition."""
        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path, {})

        adr = ADR(
            id=1, titre="Test", date=date.today(),
            statut="propose", modules=[], decideurs=[],
            contexte="", decision="", consequences=""
        )
        proposal_id = "test-proposal-456"
        bot._pending[proposal_id] = PendingProposal(proposal_id, "ts-proposal", adr)

        bot._on_action(f"ignore_{proposal_id}", {})

        assert len(bot._pending) == 0

    def test_generate_draft_uses_summary(self, tmp_path):
        """_generate_draft utilise le summary Ollama pour le titre."""
        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path, {})

        qual = {
            "is_decision": True,
            "confidence": 0.9,
            "summary": "Adoption de Kubernetes comme orchestration"
        }
        msg = Message(
            id="1", channel="tech", thread_ts=None,
            text="texte complet", user_id="U123"
        )
        adr = bot._generate_draft(qual, msg)

        assert "Kubernetes" in adr.titre
        assert adr.date == date.today()
        assert adr.statut == "propose"

    def test_next_id_increments(self, tmp_path):
        """_next_id retourne l'ID suivant disponible."""
        from teambrain.adr import save_adr

        # Créer une ADR existante
        adr = ADR(
            id=5, titre="Existing", date=date.today(),
            statut="propose", modules=[], decideurs=[],
            contexte="", decision="", consequences=""
        )
        (tmp_path / ".decisions").mkdir(exist_ok=True)
        save_adr(adr, tmp_path / ".decisions")

        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path / ".decisions", {})
        next_id = bot._next_id()

        assert next_id == 6


class TestIntegrationBot:
    """Tests d'intégration du bot."""

    @patch("teambrain.chat.bot._qualify")
    @patch("teambrain.chat.bot._is_candidate")
    @patch("teambrain.chat.bot.save_adr")
    def test_full_flow_message_to_action(self, mock_save, mock_qualify, mock_is_cand, tmp_path):
        """Flux complet : message → proposition → action valider."""
        mock_is_cand.return_value = True
        mock_qualify.return_value = {
            "is_decision": True,
            "confidence": 0.85,
            "summary": "Choix de Pydantic"
        }

        adapter = FakeAdapter()
        bot = DecisionBot(adapter, tmp_path, {
            "model": "test",
            "confidence_threshold": 0.7,
            "lead_user_id": "U999"
        })

        msg = Message(
            id="ts-msg", channel="decisions", thread_ts=None,
            text="on a choisi Pydantic pour la validation", user_id="U123"
        )
        bot._on_message(msg)

        assert len(adapter.proposals) == 1
        assert len(bot._pending) == 1

        # Récupérer le proposal_id depuis la proposition
        proposal_data = adapter.proposals[0]
        proposal_id = proposal_data["proposal_id"]

        bot._on_action(f"validate_{proposal_id}", {"user_id": "U999"})

        assert len(bot._pending) == 0
        assert mock_save.called
