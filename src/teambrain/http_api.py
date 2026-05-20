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


def _to_reponse(adr: ADR) -> ADRReponse:
    return ADRReponse(
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

def create_app(decisions_dir: Path) -> FastAPI:
    config = load_config(decisions_dir)

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

    # ── Santé ─────────────────────────────────────────────────────────────────

    @app.get("/health")
    def health():
        return {"status": "ok", "decisions_dir": str(decisions_dir)}

    # ── Référentiels ──────────────────────────────────────────────────────────

    @app.get("/referentiels")
    def referentiels():
        adrs = list_adrs(decisions_dir)
        modules = sorted({m for adr in adrs for m in adr.modules})
        return {
            "modules": modules,
            "statuts": ["propose", "accepte", "deprecie", "remplace"],
        }

    # ── Recherche (avant /adr/{id} pour éviter tout ambiguïté) ───────────────

    @app.get("/adr/search")
    def search(
        q: str = Query(..., min_length=1),
        semantic: bool = Query(False),
        k: int = Query(10, ge=1, le=50),
    ):
        if semantic:
            resultats_ids = search_semantic(q, decisions_dir, config, k=k)
            if not resultats_ids:
                return {"resultats": [], "index_disponible": False}
            adrs_par_id = {a.id: a for a in list_adrs(decisions_dir)}
            resultats = [
                {"adr": _to_reponse(adrs_par_id[adr_id]), "score": round(1.0 - dist, 3)}
                for adr_id, dist in resultats_ids
                if adr_id in adrs_par_id
            ]
            return {"resultats": resultats, "index_disponible": True}
        else:
            bruts = search_adrs(q, decisions_dir)[:k]
            return {
                "resultats": [{"adr": _to_reponse(a), "score": round(s, 3)} for a, s in bruts],
                "index_disponible": None,
            }

    # ── Brouillon IA ──────────────────────────────────────────────────────────

    @app.post("/adr/draft")
    def generer_brouillon(req: BrouillonRequete):
        try:
            draft = generate_draft(req.description, config["model"])
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Erreur Ollama : {exc}")
        return draft

    # ── CRUD ADR ──────────────────────────────────────────────────────────────

    @app.get("/adr", response_model=list[ADRReponse])
    def liste_adrs_route(
        statut: str | None = Query(None),
        module: str | None = Query(None),
    ):
        adrs = list_adrs(decisions_dir)
        if statut:
            adrs = [a for a in adrs if a.statut.lower() == statut.lower()]
        if module:
            adrs = [a for a in adrs if module.lower() in [m.lower() for m in a.modules]]
        return [_to_reponse(a) for a in adrs]

    @app.get("/adr/{adr_id}", response_model=ADRReponse)
    def detail_adr(adr_id: int):
        adr = next((a for a in list_adrs(decisions_dir) if a.id == adr_id), None)
        if adr is None:
            raise HTTPException(status_code=404, detail=f"ADR #{adr_id} introuvable")
        return _to_reponse(adr)

    @app.post("/adr", response_model=ADRReponse, status_code=201)
    def creer_adr(payload: ADRPayload):
        adr = ADR(
            id=next_id(decisions_dir),
            titre=payload.titre,
            date=date.today(),
            statut=payload.statut,
            modules=payload.modules,
            decideurs=payload.decideurs,
            contexte=payload.contexte,
            decision=payload.decision,
            consequences=payload.consequences,
        )
        save_adr(adr, decisions_dir)
        return _to_reponse(adr)

    @app.put("/adr/{adr_id}", response_model=ADRReponse)
    def modifier_adr(adr_id: int, payload: ADRPayload):
        existant = next((a for a in list_adrs(decisions_dir) if a.id == adr_id), None)
        if existant is None:
            raise HTTPException(status_code=404, detail=f"ADR #{adr_id} introuvable")

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
        nouveau_path = save_adr(adr, decisions_dir)
        if ancien_path and ancien_path != nouveau_path and ancien_path.exists():
            ancien_path.unlink()
        return _to_reponse(adr)

    return app
