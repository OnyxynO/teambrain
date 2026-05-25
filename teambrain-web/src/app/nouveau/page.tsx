"use client";

import Link from "next/link";
import { useState, useTransition, useEffect } from "react";
import { genererBrouillon, creerADR, listerProjets, getHealth, type ADR, type ProjetInfo } from "@/lib/api";
import { StatutBadge } from "@/components/StatutBadge";

function consequencesVersTexte(c: unknown): string {
  if (typeof c === "string") return c;
  if (c && typeof c === "object") {
    const obj = c as Record<string, unknown>;
    const pos = (obj["positives"] as string[] | undefined) ?? [];
    const neg = ((obj["negatives"] ?? obj["négatives"]) as string[] | undefined) ?? [];
    const lignes: string[] = [];
    if (pos.length) lignes.push("Positives :", ...pos.map((x) => `+ ${x}`));
    if (neg.length) lignes.push("Négatives :", ...neg.map((x) => `- ${x}`));
    return lignes.join("\n");
  }
  return String(c ?? "");
}

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
  titre:        "",
  statut:       "propose",
  modules:      "",
  decideurs:    "",
  contexte:     "",
  decision:     "",
  consequences: "",
};

const inputCls =
  "w-full border border-[#d0d7de] rounded-md px-3 py-2 text-sm bg-white " +
  "text-[#1f2328] focus:outline-none focus:ring-2 focus:ring-[#0969da] " +
  "focus:border-[#0969da] transition-colors";

const btnPrimary =
  "inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium text-white " +
  "bg-[#1f883d] border border-[#1a7f37] hover:bg-[#1a7f37] " +
  "disabled:opacity-50 transition-colors";

const btnSecondary =
  "inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium " +
  "text-[#1f2328] bg-[#f6f8fa] border border-[#d0d7de] hover:bg-[#eaeef2] " +
  "disabled:opacity-50 transition-colors";

function TextareaChamp({
  id, label, hint, value, onChange,
}: {
  id?: string;
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-[#1f2328]">
        {label}
        <span className="text-[#656d76] font-normal ml-1">— {hint}</span>
      </label>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className={`${inputCls} resize-y`}
      />
    </div>
  );
}

export default function PageNouveau() {
  const [etape, setEtape] = useState<Etape>("description");
  const [description, setDescription] = useState("");
  const [projetChoisi, setProjetChoisi] = useState("");
  const [champs, setChamps] = useState<ChampsBrouillon>(BROUILLON_VIDE);
  const [erreur, setErreur] = useState<string | null>(null);
  const [adrCree, setAdrCree] = useState<ADR | null>(null);
  const [isPending, startTransition] = useTransition();
  const [projets, setProjets] = useState<ProjetInfo[]>([]);
  const [ollamaDisponible, setOllamaDisponible] = useState<boolean | null>(null);

  useEffect(() => {
    Promise.all([listerProjets(), getHealth()]).then(([liste, health]) => {
      setProjets(liste);
      setOllamaDisponible(health.ollama_disponible);
      if (liste.length === 1) setProjetChoisi(liste[0].id);
      if (!health.ollama_disponible) setEtape("edition");
    }).catch(() => {
      setOllamaDisponible(false);
      setEtape("edition");
    });
  }, []);

  function setChamp(key: keyof ChampsBrouillon, value: string) {
    setChamps((prev) => ({ ...prev, [key]: value }));
  }

  function generer() {
    if (!description.trim()) return;
    setErreur(null);
    setEtape("generation");
    startTransition(async () => {
      try {
        const draft = await genererBrouillon(description.trim(), projetChoisi || undefined);
        setChamps({
          titre:        draft.titre ?? "",
          statut:       "propose",
          modules:      (draft.modules ?? []).join(", "),
          decideurs:    (draft.decideurs ?? []).join(", "),
          contexte:     draft.contexte ?? "",
          decision:     draft.decision ?? "",
          consequences: consequencesVersTexte(draft.consequences),
        });
        setEtape("edition");
      } catch (err) {
        setErreur(err instanceof Error ? err.message : "Erreur Ollama");
        setEtape("description");
      }
    });
  }

  function sauvegarder() {
    if (!projetChoisi) {
      setErreur("Sélectionne un projet avant de sauvegarder.");
      return;
    }
    setErreur(null);
    setEtape("sauvegarde");
    startTransition(async () => {
      try {
        const adr = await creerADR(projetChoisi, {
          titre:        champs.titre || description.slice(0, 60),
          statut:       champs.statut,
          modules:      champs.modules.split(",").map((s) => s.trim()).filter(Boolean),
          decideurs:    champs.decideurs.split(",").map((s) => s.trim()).filter(Boolean),
          contexte:     champs.contexte,
          decision:     champs.decision,
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
    <div className="max-w-2xl space-y-5">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-[#656d76]">
        <Link href="/" className="hover:text-[#0969da] transition-colors">
          Décisions
        </Link>
        <span className="text-[#d0d7de]">/</span>
        <span>Nouvelle décision</span>
      </nav>

      <h1 className="text-xl font-semibold text-[#1f2328]">Nouvelle décision</h1>

      {erreur && (
        <div className="bg-[#ffebe9] border border-[#d1242f]/30 text-[#d1242f] rounded-md px-4 py-3 text-sm">
          {erreur}
        </div>
      )}

      {/* ── Étape 1 — Description ── */}
      {(etape === "description" || etape === "generation") && (
        <div className="bg-white border border-[#d0d7de] rounded-md p-6 space-y-4">
          {projets.length > 1 && (
            <div className="space-y-1.5">
              <label htmlFor="projet-select" className="block text-sm font-medium text-[#1f2328]">Projet</label>
              <select
                id="projet-select"
                value={projetChoisi}
                onChange={(e) => setProjetChoisi(e.target.value)}
                className={inputCls}
              >
                <option value="">Sélectionner un projet…</option>
                {projets.map((p) => (
                  <option key={p.id} value={p.id}>{p.nom} ({p.nb_adrs} ADR)</option>
                ))}
              </select>
            </div>
          )}

          <div className="space-y-1.5">
            <label htmlFor="description-input" className="block text-sm font-medium text-[#1f2328]">
              Décris la décision à documenter
              <span className="text-[#656d76] font-normal ml-1">— en quelques phrases</span>
            </label>
            <textarea
              id="description-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ex : On a décidé d'utiliser SQLite pour le stockage local plutôt que PostgreSQL…"
              rows={4}
              className={`${inputCls} resize-none`}
            />
          </div>

          <button
            onClick={generer}
            disabled={isPending || !description.trim() || (projets.length > 1 && !projetChoisi)}
            className={btnPrimary}
          >
            {etape === "generation" ? (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" className="mr-1.5 animate-spin" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
                Génération en cours…
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" className="mr-1.5" aria-hidden="true">
                  <path d="M9.504.43a1.516 1.516 0 0 1 2.437 1.713L10.415 5.5h2.123c1.57 0 2.454 1.75 1.46 3.004L9.506 15.71a1.516 1.516 0 0 1-2.437-1.713L8.585 10.5H6.462c-1.57 0-2.454-1.75-1.46-3.004L9.504.43Z" />
                </svg>
                Générer le brouillon
              </>
            )}
          </button>
        </div>
      )}

      {/* ── Étape 2 — Édition du brouillon ── */}
      {(etape === "edition" || etape === "sauvegarde") && (
        <div className="bg-white border border-[#d0d7de] rounded-md p-6 space-y-5">
          {/* Projet */}
          {ollamaDisponible === false ? (
            <div className="space-y-1.5">
              <label htmlFor="projet-edit-select" className="block text-sm font-medium text-[#1f2328]">Projet</label>
              <select
                id="projet-edit-select"
                value={projetChoisi}
                onChange={(e) => setProjetChoisi(e.target.value)}
                className={inputCls}
              >
                <option value="">Sélectionner un projet…</option>
                {projets.map((p) => (
                  <option key={p.id} value={p.id}>{p.nom} ({p.nb_adrs} ADR)</option>
                ))}
              </select>
            </div>
          ) : projetChoisi ? (
            <div className="flex items-center gap-2 text-sm text-[#656d76]">
              Projet :
              <span className="inline-block px-2 py-0 rounded-full text-xs font-medium border border-[#d0d7de] bg-[#ddf4ff] text-[#0550ae]">
                {projetChoisi}
              </span>
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 space-y-1.5">
              <label htmlFor="nouveau-titre" className="block text-sm font-medium text-[#1f2328]">Titre</label>
              <input
                id="nouveau-titre"
                type="text"
                value={champs.titre}
                onChange={(e) => setChamp("titre", e.target.value)}
                className={inputCls}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="nouveau-statut" className="block text-sm font-medium text-[#1f2328]">
                Statut
              </label>
              <select
                id="nouveau-statut"
                value={champs.statut}
                onChange={(e) => setChamp("statut", e.target.value)}
                className={inputCls}
              >
                <option value="propose">Proposé</option>
                <option value="accepte">Accepté</option>
                <option value="deprecie">Déprécié</option>
                <option value="remplace">Remplacé</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="nouveau-modules" className="block text-sm font-medium text-[#1f2328]">
                Modules
                <span className="text-[#656d76] font-normal ml-1">(virgule)</span>
              </label>
              <input
                id="nouveau-modules"
                type="text"
                value={champs.modules}
                onChange={(e) => setChamp("modules", e.target.value)}
                placeholder="api, core"
                className={inputCls}
              />
            </div>

            <div className="col-span-2 space-y-1.5">
              <label htmlFor="nouveau-decideurs" className="block text-sm font-medium text-[#1f2328]">
                Décideurs
                <span className="text-[#656d76] font-normal ml-1">(virgule)</span>
              </label>
              <input
                id="nouveau-decideurs"
                type="text"
                value={champs.decideurs}
                onChange={(e) => setChamp("decideurs", e.target.value)}
                placeholder="alice, bob"
                className={inputCls}
              />
            </div>
          </div>

          <hr className="border-[#d0d7de]" />

          <TextareaChamp id="nouveau-contexte"      label="Contexte"      hint="Quel problème ?"        value={champs.contexte}      onChange={(v) => setChamp("contexte", v)} />
          <TextareaChamp id="nouveau-decision"      label="Décision"      hint="Qu'a-t-on décidé ?"     value={champs.decision}      onChange={(v) => setChamp("decision", v)} />
          <TextareaChamp id="nouveau-consequences"  label="Conséquences"  hint="Impacts, compromis"     value={champs.consequences}  onChange={(v) => setChamp("consequences", v)} />

          <div className="flex gap-2 pt-2">
            <button
              onClick={sauvegarder}
              disabled={isPending || !champs.titre.trim()}
              className={btnPrimary}
            >
              {etape === "sauvegarde" ? "Sauvegarde…" : "Valider et sauvegarder"}
            </button>
            {ollamaDisponible !== false && (
              <button
                onClick={() => setEtape("description")}
                disabled={isPending}
                className={btnSecondary}
              >
                ← Recommencer
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Étape 3 — Succès ── */}
      {etape === "done" && adrCree && (
        <div className="bg-white border border-[#d0d7de] rounded-md p-8 text-center space-y-4">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center mx-auto"
            style={{ backgroundColor: "#dafbe1" }}
          >
            <svg width="20" height="20" viewBox="0 0 16 16" fill="#1a7f37" aria-hidden="true">
              <path d="M8 16A8 8 0 1 1 8 0a8 8 0 0 1 0 16Zm3.78-9.72a.75.75 0 0 0-1.06-1.06L6.75 9.19 5.28 7.72a.75.75 0 0 0-1.06 1.06l2 2a.75.75 0 0 0 1.06 0l4.5-4.5Z" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-[#1f2328]">
              ADR{" "}
              <span className="font-mono">#{String(adrCree.id).padStart(3, "0")}</span>{" "}
              sauvegardé
            </p>
            <p className="text-sm text-[#656d76] mt-1">{adrCree.titre}</p>
            <div className="flex items-center justify-center gap-2 mt-2">
              <span className="inline-block px-2 py-0 rounded-full text-xs font-medium border border-[#d0d7de] bg-[#ddf4ff] text-[#0550ae]">
                {adrCree.projet}
              </span>
              <StatutBadge statut={adrCree.statut} />
            </div>
          </div>
          <div className="flex gap-2 justify-center">
            <Link
              href={`/adr/?projet=${adrCree.projet}&id=${adrCree.id}`}
              className={btnPrimary}
            >
              Voir l&apos;ADR
            </Link>
            <button onClick={recommencer} className={btnSecondary}>
              Créer un autre
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
