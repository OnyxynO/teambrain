from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .adr import ADR, list_adrs, next_id, save_adr, search_adrs
from .ai import generate_draft
from .config import load_config
from .store import search_semantic


# ── Schémas ───────────────────────────────────────────────────────────────────

class ADRReponse(BaseModel):
    projet: str
    id: int
    titre: str
    date: str
    statut: str
    modules: list[str]
    decideurs: list[str]
    contexte: str
    decision: str
    consequences: str


class ADRPayload(BaseModel):
    titre: str
    statut: str = "propose"
    modules: list[str] = []
    decideurs: list[str] = []
    contexte: str = ""
    decision: str = ""
    consequences: str = ""


class BrouillonRequete(BaseModel):
    description: str
    projet: str | None = None


class ProjetInfo(BaseModel):
    id: str
    nom: str
    nb_adrs: int


def _to_reponse(adr: ADR, projet: str) -> ADRReponse:
    return ADRReponse(
        projet=projet,
        id=adr.id,
        titre=adr.titre,
        date=adr.date.isoformat(),
        statut=adr.statut,
        modules=adr.modules,
        decideurs=adr.decideurs,
        contexte=adr.contexte,
        decision=adr.decision,
        consequences=adr.consequences,
    )


# ── Usine d'application ────────────────────────────────────────────────────────

def create_app(projets: dict[str, Path], static_dir: Path | None = None) -> FastAPI:
    """
    projets    : dict nom_projet → chemin .decisions/
    static_dir : dossier du build Next.js (out/) — active le serving de l'UI
    """
    configs = {nom: load_config(d) for nom, d in projets.items()}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app = FastAPI(title="TeamBrain API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _require_projet(nom: str) -> Path:
        if nom not in projets:
            raise HTTPException(status_code=404, detail=f"Projet « {nom} » introuvable")
        return projets[nom]

    def _filtrer(
        projet: str | None,
        statut: str | None,
        module: str | None,
    ) -> list[ADRReponse]:
        if projet and projet not in projets:
            return []
        noms = [projet] if projet else list(projets.keys())
        result = []
        for nom in noms:
            for adr in list_adrs(projets[nom]):
                if statut and adr.statut.lower() != statut.lower():
                    continue
                if module and module.lower() not in [m.lower() for m in adr.modules]:
                    continue
                result.append(_to_reponse(adr, nom))
        return result

    # ── Santé ─────────────────────────────────────────────────────────────────

    @app.get("/health")
    def health():
        try:
            import ollama as _ollama
            _ollama.list()
            ollama_disponible = True
        except Exception:
            ollama_disponible = False
        return {
            "status": "ok",
            "projets": {nom: str(d) for nom, d in projets.items()},
            "ollama_disponible": ollama_disponible,
        }

    # ── Projets ───────────────────────────────────────────────────────────────

    @app.get("/projects", response_model=list[ProjetInfo])
    def liste_projets():
        return [
            ProjetInfo(id=nom, nom=nom, nb_adrs=len(list_adrs(d)))
            for nom, d in projets.items()
        ]

    # ── Référentiels ──────────────────────────────────────────────────────────

    @app.get("/referentiels")
    def referentiels(projet: str | None = Query(None)):
        noms = [projet] if projet and projet in projets else list(projets.keys())
        modules = sorted({
            m
            for nom in noms
            for adr in list_adrs(projets[nom])
            for m in adr.modules
        })
        return {
            "modules": modules,
            "statuts": ["propose", "accepte", "deprecie", "remplace"],
            "projets": list(projets.keys()),
        }

    # ── Recherche (avant /adr/{projet}/... pour priorité de routage) ──────────

    @app.get("/adr/search")
    def search(
        q: str = Query(..., min_length=1),
        projet: str | None = Query(None),
        semantic: bool = Query(False),
        k: int = Query(10, ge=1, le=50),
    ):
        if semantic:
            if not projet or projet not in projets:
                raise HTTPException(
                    status_code=400,
                    detail="La recherche sémantique requiert ?projet= (index local par repo).",
                )
            config = configs[projet]
            d = projets[projet]
            resultats_ids = search_semantic(q, d, config, k=k)
            if not resultats_ids:
                return {"resultats": [], "index_disponible": False}
            adrs_par_id = {a.id: a for a in list_adrs(d)}
            resultats = [
                {"adr": _to_reponse(adrs_par_id[adr_id], projet), "score": round(1.0 - dist, 3)}
                for adr_id, dist in resultats_ids
                if adr_id in adrs_par_id
            ]
            return {"resultats": resultats, "index_disponible": True}
        else:
            noms = [projet] if projet and projet in projets else list(projets.keys())
            resultats = []
            for nom in noms:
                for adr, score in search_adrs(q, projets[nom]):
                    resultats.append({"adr": _to_reponse(adr, nom), "score": round(score, 3)})
            resultats.sort(key=lambda x: x["score"], reverse=True)
            return {"resultats": resultats[:k], "index_disponible": None}

    # ── Brouillon IA (avant /adr/{projet} pour priorité de routage) ───────────

    @app.post("/adr/draft")
    def generer_brouillon(req: BrouillonRequete):
        nom = req.projet if req.projet and req.projet in projets else next(iter(projets))
        config = configs[nom]
        try:
            draft = generate_draft(req.description, config["model"])
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Erreur Ollama : {exc}")
        return draft

    # ── Liste ADR ─────────────────────────────────────────────────────────────

    @app.get("/adr", response_model=list[ADRReponse])
    def liste_adrs_route(
        projet: str | None = Query(None),
        statut: str | None = Query(None),
        module: str | None = Query(None),
    ):
        return _filtrer(projet, statut, module)

    # ── Détail ADR ────────────────────────────────────────────────────────────

    @app.get("/adr/{projet}/{adr_id}", response_model=ADRReponse)
    def detail_adr(projet: str, adr_id: int):
        d = _require_projet(projet)
        adr = next((a for a in list_adrs(d) if a.id == adr_id), None)
        if adr is None:
            raise HTTPException(status_code=404, detail=f"ADR #{adr_id} introuvable dans {projet}")
        return _to_reponse(adr, projet)

    # ── Création ADR ──────────────────────────────────────────────────────────

    @app.post("/adr/{projet}", response_model=ADRReponse, status_code=201)
    def creer_adr(projet: str, payload: ADRPayload):
        d = _require_projet(projet)
        adr = ADR(
            id=next_id(d),
            titre=payload.titre,
            date=date.today(),
            statut=payload.statut,
            modules=payload.modules,
            decideurs=payload.decideurs,
            contexte=payload.contexte,
            decision=payload.decision,
            consequences=payload.consequences,
        )
        save_adr(adr, d)
        return _to_reponse(adr, projet)

    # ── Modification ADR ──────────────────────────────────────────────────────

    @app.put("/adr/{projet}/{adr_id}", response_model=ADRReponse)
    def modifier_adr(projet: str, adr_id: int, payload: ADRPayload):
        d = _require_projet(projet)
        existant = next((a for a in list_adrs(d) if a.id == adr_id), None)
        if existant is None:
            raise HTTPException(status_code=404, detail=f"ADR #{adr_id} introuvable dans {projet}")

        ancien_path = existant.path
        adr = ADR(
            id=adr_id,
            titre=payload.titre,
            date=existant.date,
            statut=payload.statut,
            modules=payload.modules,
            decideurs=payload.decideurs,
            contexte=payload.contexte,
            decision=payload.decision,
            consequences=payload.consequences,
        )
        nouveau_path = save_adr(adr, d)
        if ancien_path and ancien_path != nouveau_path and ancien_path.exists():
            ancien_path.unlink()
        return _to_reponse(adr, projet)

    if static_dir and static_dir.exists():
        from fastapi.responses import FileResponse

        @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
        async def serve_root():
            return FileResponse(static_dir / "index.html")

        @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
        async def serve_static(path: str):
            clean = path.rstrip("/")
            f = static_dir / clean
            if f.is_file():
                return FileResponse(f)
            idx = static_dir / clean / "index.html"
            if idx.is_file():
                return FileResponse(idx)
            return FileResponse(static_dir / "index.html")

    return app
