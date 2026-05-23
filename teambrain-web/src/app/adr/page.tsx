"use client";

import { useEffect, useState, useTransition, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getADR, modifierADR, supprimerADR, type ADR } from "@/lib/api";
import { StatutBadge } from "@/components/StatutBadge";

interface ChampsEdit {
  titre: string;
  statut: string;
  date: string;
  modules: string;
  decideurs: string;
  contexte: string;
  decision: string;
  consequences: string;
}

function adrVersChamps(adr: ADR): ChampsEdit {
  return {
    titre: adr.titre,
    statut: adr.statut,
    date: adr.date,
    modules: adr.modules.join(", "),
    decideurs: adr.decideurs.join(", "),
    contexte: adr.contexte,
    decision: adr.decision,
    consequences: adr.consequences,
  };
}

function parseConsequencesPythonDict(texte: string): { positives: string[]; negatives: string[] } | null {
  const posMatch = texte.match(/'positives':\s*\[([^\]]*)\]/);
  const negMatch = texte.match(/'n[eé]gatives':\s*\[([^\]]*)\]/);
  if (!posMatch && !negMatch) return null;
  const parseItems = (raw: string) =>
    raw.split(/,\s*(?=')/).map((s) => s.trim().replace(/^'|'$/g, "")).filter(Boolean);
  return {
    positives: posMatch ? parseItems(posMatch[1]) : [],
    negatives: negMatch ? parseItems(negMatch[1]) : [],
  };
}

function DetailADR() {
  const params = useSearchParams();
  const router = useRouter();
  const projet = params.get("projet") ?? "";
  const id = parseInt(params.get("id") ?? "", 10);

  const [adr, setAdr] = useState<ADR | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);

  const [modeEdit, setModeEdit] = useState(false);
  const [champs, setChamps] = useState<ChampsEdit | null>(null);
  const [erreurSave, setErreurSave] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const [confirmSuppression, setConfirmSuppression] = useState(false);

  useEffect(() => {
    if (!projet || isNaN(id)) {
      setErreur("Paramètres invalides");
      setChargement(false);
      return;
    }
    setChargement(true);
    getADR(projet, id)
      .then((a) => {
        setAdr(a);
        setChargement(false);
      })
      .catch(() => {
        setErreur("ADR introuvable");
        setChargement(false);
      });
  }, [projet, id]);

  function ouvrirEdit() {
    if (!adr) return;
    setChamps(adrVersChamps(adr));
    setErreurSave(null);
    setModeEdit(true);
  }

  function annulerEdit() {
    setModeEdit(false);
    setChamps(null);
    setErreurSave(null);
  }

  function setChamp(key: keyof ChampsEdit, value: string) {
    setChamps((prev) => prev ? { ...prev, [key]: value } : prev);
  }

  function sauvegarder() {
    if (!champs) return;
    setErreurSave(null);
    startTransition(async () => {
      try {
        const mis_a_jour = await modifierADR(projet, id, {
          titre: champs.titre,
          statut: champs.statut,
          modules: champs.modules.split(",").map((s) => s.trim()).filter(Boolean),
          decideurs: champs.decideurs.split(",").map((s) => s.trim()).filter(Boolean),
          contexte: champs.contexte,
          decision: champs.decision,
          consequences: champs.consequences,
        });
        setAdr(mis_a_jour);
        setModeEdit(false);
        setChamps(null);
      } catch (err) {
        setErreurSave(err instanceof Error ? err.message : "Erreur lors de la sauvegarde");
      }
    });
  }

  function supprimer() {
    startTransition(async () => {
      try {
        await supprimerADR(projet, id);
        router.push("/");
      } catch (err) {
        setErreurSave(err instanceof Error ? err.message : "Erreur lors de la suppression");
        setConfirmSuppression(false);
      }
    });
  }

  if (chargement) {
    return <div className="text-center py-16 text-slate-400">Chargement…</div>;
  }

  if (erreur || !adr) {
    return (
      <div className="text-center py-16 text-slate-400">
        <p>{erreur ?? "ADR introuvable"}</p>
        <Link href="/" className="text-indigo-600 hover:underline text-sm mt-2 block">
          ← Retour à la liste
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-8">
      {/* ── Fil d'Ariane ── */}
      <div className="flex items-center gap-3">
        <Link href="/" className="text-sm text-slate-500 hover:text-slate-700 transition-colors">
          ← Toutes les décisions
        </Link>
        <span className="text-slate-300">·</span>
        <Link
          href={`/?projet=${projet}`}
          className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium hover:bg-indigo-100 transition-colors"
        >
          {projet}
        </Link>
      </div>

      {erreurSave && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {erreurSave}
        </div>
      )}

      {/* ── Mode lecture ── */}
      {!modeEdit && (
        <>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm text-slate-400">
                  #{String(adr.id).padStart(3, "0")}
                </span>
                <StatutBadge statut={adr.statut} />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={ouvrirEdit}
                  className="px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  Éditer
                </button>
                {!confirmSuppression ? (
                  <button
                    onClick={() => setConfirmSuppression(true)}
                    className="px-3 py-1.5 text-sm font-medium text-red-600 bg-white border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                  >
                    Supprimer
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-red-600">Confirmer ?</span>
                    <button
                      onClick={supprimer}
                      disabled={isPending}
                      className="px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                    >
                      {isPending ? "Suppression…" : "Oui, supprimer"}
                    </button>
                    <button
                      onClick={() => setConfirmSuppression(false)}
                      className="px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                    >
                      Annuler
                    </button>
                  </div>
                )}
              </div>
            </div>
            <h1 className="text-2xl font-semibold text-slate-900">{adr.titre}</h1>
            <div className="flex gap-4 text-sm text-slate-500">
              <span>{adr.date}</span>
              {adr.modules.length > 0 && (
                <span>Modules : {adr.modules.join(", ")}</span>
              )}
              {adr.decideurs.length > 0 && (
                <span>Décideurs : {adr.decideurs.join(", ")}</span>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <Section titre="Contexte" contenu={adr.contexte} />
            <Section titre="Décision" contenu={adr.decision} />
            <SectionConsequences contenu={adr.consequences} />
          </div>
        </>
      )}

      {/* ── Mode édition ── */}
      {modeEdit && champs && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-700">
              Édition — #{String(adr.id).padStart(3, "0")}
            </span>
          </div>

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
              <label className="block text-sm font-medium text-slate-700">Date</label>
              <input
                type="date"
                value={champs.date}
                onChange={(e) => setChamp("date", e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-700">
                Modules
                <span className="text-slate-400 font-normal ml-1">(virgule)</span>
              </label>
              <input
                type="text"
                value={champs.modules}
                onChange={(e) => setChamp("modules", e.target.value)}
                placeholder="api, core"
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-slate-700">
                Décideurs
                <span className="text-slate-400 font-normal ml-1">(virgule)</span>
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

          <hr className="border-slate-100" />

          <ChampTextarea label="Contexte" hint="Quel problème ?" value={champs.contexte} onChange={(v) => setChamp("contexte", v)} />
          <ChampTextarea label="Décision" hint="Qu'a-t-on décidé ?" value={champs.decision} onChange={(v) => setChamp("decision", v)} />
          <ChampTextarea label="Conséquences" hint="Impacts, compromis, risques" value={champs.consequences} onChange={(v) => setChamp("consequences", v)} />

          <div className="flex gap-3 pt-2">
            <button
              onClick={sauvegarder}
              disabled={isPending || !champs.titre.trim()}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {isPending ? "Sauvegarde…" : "Sauvegarder"}
            </button>
            <button
              onClick={annulerEdit}
              disabled={isPending}
              className="px-4 py-2 bg-white text-slate-700 text-sm font-medium rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ titre, contenu }: { titre: string; contenu: string }) {
  if (!contenu) return null;
  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{titre}</h2>
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">{contenu}</p>
      </div>
    </div>
  );
}

function SectionConsequences({ contenu }: { contenu: string }) {
  if (!contenu) return null;
  const parsed = parseConsequencesPythonDict(contenu);
  return (
    <div className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Conséquences</h2>
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        {parsed ? (
          <div className="space-y-4">
            {parsed.positives.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-emerald-600 uppercase tracking-wide mb-2">Positives</p>
                <ul className="space-y-1.5">
                  {parsed.positives.map((item, i) => (
                    <li key={i} className="flex gap-2 text-slate-700 leading-snug">
                      <span className="text-emerald-500 font-bold shrink-0">+</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {parsed.negatives.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-2">Négatives</p>
                <ul className="space-y-1.5">
                  {parsed.negatives.map((item, i) => (
                    <li key={i} className="flex gap-2 text-slate-700 leading-snug">
                      <span className="text-red-400 font-bold shrink-0">−</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">{contenu}</p>
        )}
      </div>
    </div>
  );
}

function ChampTextarea({
  label, hint, value, onChange,
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
        rows={4}
        className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
      />
    </div>
  );
}

export default function PageDetailADR() {
  return (
    <Suspense>
      <DetailADR />
    </Suspense>
  );
}
