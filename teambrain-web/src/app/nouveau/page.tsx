"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { genererBrouillon, creerADR, type ADR } from "@/lib/api";

type Etape = "description" | "generation" | "edition" | "sauvegarde" | "done";

interface ChampsBrouillon {
  titre: string;
  statut: string;
  modules: string;
  decideurs: string;
  contexte: string;
  decision: string;
  consequences: string;
}

const BROUILLON_VIDE: ChampsBrouillon = {
  titre: "",
  statut: "propose",
  modules: "",
  decideurs: "",
  contexte: "",
  decision: "",
  consequences: "",
};

export default function PageNouveau() {
  const [etape, setEtape] = useState<Etape>("description");
  const [description, setDescription] = useState("");
  const [champs, setChamps] = useState<ChampsBrouillon>(BROUILLON_VIDE);
  const [erreur, setErreur] = useState<string | null>(null);
  const [adrCree, setAdrCree] = useState<ADR | null>(null);
  const [isPending, startTransition] = useTransition();

  function setChamp(key: keyof ChampsBrouillon, value: string) {
    setChamps((prev) => ({ ...prev, [key]: value }));
  }

  function generer() {
    if (!description.trim()) return;
    setErreur(null);
    setEtape("generation");
    startTransition(async () => {
      try {
        const draft = await genererBrouillon(description.trim());
        setChamps({
          titre: draft.titre ?? "",
          statut: "propose",
          modules: (draft.modules ?? []).join(", "),
          decideurs: (draft.decideurs ?? []).join(", "),
          contexte: draft.contexte ?? "",
          decision: draft.decision ?? "",
          consequences: draft.consequences ?? "",
        });
        setEtape("edition");
      } catch (err) {
        setErreur(err instanceof Error ? err.message : "Erreur Ollama");
        setEtape("description");
      }
    });
  }

  function creerManuellement() {
    setChamps({ ...BROUILLON_VIDE, decision: description.trim() });
    setEtape("edition");
  }

  function sauvegarder() {
    setErreur(null);
    setEtape("sauvegarde");
    startTransition(async () => {
      try {
        const adr = await creerADR({
          titre: champs.titre || description.slice(0, 60),
          statut: champs.statut,
          modules: champs.modules.split(",").map((s) => s.trim()).filter(Boolean),
          decideurs: champs.decideurs.split(",").map((s) => s.trim()).filter(Boolean),
          contexte: champs.contexte,
          decision: champs.decision,
          consequences: champs.consequences,
        });
        setAdrCree(adr);
        setEtape("done");
      } catch (err) {
        setErreur(err instanceof Error ? err.message : "Erreur lors de la sauvegarde");
        setEtape("edition");
      }
    });
  }

  function recommencer() {
    setEtape("description");
    setDescription("");
    setChamps(BROUILLON_VIDE);
    setErreur(null);
    setAdrCree(null);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <Link href="/" className="text-sm text-slate-500 hover:text-slate-700 transition-colors">
          ← Toutes les décisions
        </Link>
      </div>

      <h1 className="text-2xl font-semibold">Nouvelle décision</h1>

      {erreur && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {erreur}
        </div>
      )}

      {/* ── Étape 1 — Description ── */}
      {(etape === "description" || etape === "generation") && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-700">
              Décris la décision à documenter
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ex : On a décidé d'utiliser SQLite pour le stockage local plutôt que PostgreSQL…"
              rows={4}
              className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={generer}
              disabled={isPending || !description.trim()}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {etape === "generation" ? "Génération en cours…" : "Générer le brouillon"}
            </button>
            <button
              onClick={creerManuellement}
              disabled={isPending}
              className="px-4 py-2 bg-white text-slate-700 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              Créer manuellement
            </button>
          </div>

          {etape === "generation" && (
            <p className="text-sm text-slate-400">
              Génération via Ollama en cours…
            </p>
          )}
        </div>
      )}

      {/* ── Étape 2 — Édition du brouillon ── */}
      {(etape === "edition" || etape === "sauvegarde") && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 space-y-1.5">
              <label className="block text-sm font-medium text-slate-700">Titre</label>
              <input
                type="text"
                value={champs.titre}
                onChange={(e) => setChamp("titre", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-700">Statut</label>
              <select
                value={champs.statut}
                onChange={(e) => setChamp("statut", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="propose">propose</option>
                <option value="accepte">accepte</option>
                <option value="deprecie">deprecie</option>
                <option value="remplace">remplace</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-700">
                Modules
                <span className="text-slate-400 font-normal ml-1">(séparés par virgule)</span>
              </label>
              <input
                type="text"
                value={champs.modules}
                onChange={(e) => setChamp("modules", e.target.value)}
                placeholder="api, core, auth"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="col-span-2 space-y-1.5">
              <label className="block text-sm font-medium text-slate-700">
                Décideurs
                <span className="text-slate-400 font-normal ml-1">(séparés par virgule)</span>
              </label>
              <input
                type="text"
                value={champs.decideurs}
                onChange={(e) => setChamp("decideurs", e.target.value)}
                placeholder="alice, bob"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <Separateur />

          <TextareaChamp
            label="Contexte"
            hint="Quel problème cherchait-on à résoudre ?"
            value={champs.contexte}
            onChange={(v) => setChamp("contexte", v)}
          />
          <TextareaChamp
            label="Décision"
            hint="Qu'a-t-on décidé ?"
            value={champs.decision}
            onChange={(v) => setChamp("decision", v)}
          />
          <TextareaChamp
            label="Conséquences"
            hint="Quels sont les impacts, compromis, risques ?"
            value={champs.consequences}
            onChange={(v) => setChamp("consequences", v)}
          />

          <div className="flex gap-3 pt-2">
            <button
              onClick={sauvegarder}
              disabled={isPending || !champs.titre.trim()}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {etape === "sauvegarde" ? "Sauvegarde…" : "Valider et sauvegarder"}
            </button>
            <button
              onClick={() => setEtape("description")}
              disabled={isPending}
              className="px-4 py-2 bg-white text-slate-700 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              ← Recommencer
            </button>
          </div>
        </div>
      )}

      {/* ── Étape 3 — Succès ── */}
      {etape === "done" && adrCree && (
        <div className="bg-white rounded-xl border border-green-200 p-8 text-center space-y-4">
          <div className="text-green-600 text-4xl">✓</div>
          <div>
            <p className="font-semibold text-slate-900">
              ADR #{String(adrCree.id).padStart(3, "0")} sauvegardé
            </p>
            <p className="text-sm text-slate-500 mt-1">{adrCree.titre}</p>
          </div>
          <div className="flex gap-3 justify-center">
            <Link
              href={`/adr/${adrCree.id}`}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Voir l&apos;ADR
            </Link>
            <button
              onClick={recommencer}
              className="px-4 py-2 bg-white text-slate-700 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
            >
              Créer un autre
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Separateur() {
  return <hr className="border-slate-100" />;
}

function TextareaChamp({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-slate-700">
        {label}
        <span className="text-slate-400 font-normal ml-1">— {hint}</span>
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
      />
    </div>
  );
}
