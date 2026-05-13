from __future__ import annotations
import logging
from github import Github
from github.GithubException import GithubException

from ..adr import ADR, slugify

logger = logging.getLogger(__name__)


class GitHubPRCreator:
    """Crée des branches et PR GitHub pour les ADRs validées."""

    def __init__(self, token: str, repo_name: str):
        """Initialise le client GitHub.

        Args:
            token: Token GitHub (ghp-...)
            repo_name: Format "owner/repo"
        """
        self.gh = Github(token)
        self.repo = self.gh.get_repo(repo_name)

    def create_pr(self, adr: ADR, adr_content: str) -> str:
        """Crée une branche et une PR pour l'ADR.

        Args:
            adr: L'ADR validée
            adr_content: Contenu markdown (frontmatter) de l'ADR

        Returns:
            URL de la PR créée
        """
        branch_name = f"feat/adr-{adr.id:03d}-{slugify(adr.titre)}"
        filename = f".decisions/{adr.id:03d}-{slugify(adr.titre)}.md"

        try:
            main_ref = self.repo.get_git_ref("heads/main")
            main_sha = main_ref.object.sha

            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=main_sha,
            )

            self.repo.create_file(
                path=filename,
                message=f"feat(adr): {adr.titre}",
                content=adr_content,
                branch=branch_name,
            )

            pr = self.repo.create_pull(
                title=f"ADR #{adr.id:03d} — {adr.titre}",
                body=self._pr_body(adr),
                head=branch_name,
                base="main",
            )

            return pr.html_url

        except GithubException:
            logger.exception("Erreur création PR")
            raise

    def _pr_body(self, adr: ADR) -> str:
        """Génère le body de la PR."""
        modules_str = ", ".join(adr.modules) if adr.modules else "—"
        return (
            f"## ADR #{adr.id:03d}\n\n"
            f"Modules : {modules_str}\n"
            f"Date : {adr.date.isoformat()}\n\n"
            f"### Contexte\n\n{adr.contexte}\n\n"
            f"### Décision\n\n{adr.decision}\n\n"
            f"### Conséquences\n\n{adr.consequences}\n"
        )
