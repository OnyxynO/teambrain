"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { rechercherADR, listerProjets, type ResultatRecherche, type ProjetInfo } from "@/lib/api";
import { StatutBadge } from "@/components/StatutBadge";
import { useEffect } from "react";

export default function PageRecherche() {
  const [query, setQuery] = useState("");
  const [projetFiltre, setProjetFiltre] = useState("");
  const [semantic, setSemantic] = useState(false);
  const [resultats, setResultats] = useState<ResultatRecherche[]>([]);
  const [indexDispo, setIndexDispo] = useState<boolean | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [rechercheFaite, setRechercheFaite] = useState(false);
  const [projets, setProjets] = useState<ProjetInfo[]>([]);

  useEffect(() => {
    listerProjets().then(setProjets).catch(() => {});
  }, []);

  function rechercher(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setErreur(null);
    startTransition(async () => {
      try {
        const data = await rechercherADR(query.trim(), {
          projet: projetFiltre || undefined,
          semantic,
        });
        setResultats(data.resultats);
        setIndexDispo(data.index_disponible);
        setRechercheFaite(true);
      } catch (err) {
        setErreur(err instanceof Error ? err.message : "Erreur de recherche");
        setResultats([]);
      }
    });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">Recherche</h1>

      <form onSubmit={rechercher} className="space-y-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher dans les décisions…"
            className="flex-1 border border-slate-200 rounded-lg px-4 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={isPending || !query.trim()}
            className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {isPending ? "…" : "Rechercher"}
          </button>
        </div>

        <div className="flex gap-4 flex-wrap">
          {projets.length > 1 && (
            <select
              value={projetFiltre}
              onChange={(e) => setProjetFiltre(e.target.value)}
              className="text-sm border border-slate-200 rounded px-3 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Tous les projets</option>
              {projets.map((p) => (
                <option key={p.id} value={p.id}>{p.nom}</option>
              ))}
            </select>
          )}

          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={semantic}
              onChange={(e) => setSemantic(e.target.checked)}
              className="rounded"
            />
            Sémantique
            {semantic && !projetFiltre && projets.length > 1 && (
              <span className="text-yellow-600 text-xs">— sélectionne un projet</span>
            )}
          </label>
        </div>
      </form>

      {erreur && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {erreur}
        </div>
      )}

      {semantic && indexDispo === false && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 rounded-lg px-4 py-3 text-sm">
          Index sémantique non disponible.{" "}
          Lance <code className="font-mono">teambrain index</code> dans le repo concerné.
        </div>
      )}

      {rechercheFaite && resultats.length === 0 && !erreur && (
        <p className="text-slate-400 text-sm">Aucun résultat pour « {query} »</p>
      )}

      {resultats.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-slate-500">{resultats.length} résultat(s)</p>
          {resultats.map(({ adr, score }) => (
            <div
              key={`${adr.projet}-${adr.id}`}
              className="bg-white rounded-xl border border-slate-200 p-4 space-y-2"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-xs text-slate-400 shrink-0">
                    #{String(adr.id).padStart(3, "0")}
                  </span>
                  <Link
                    href={`/adr/${adr.projet}/${adr.id}`}
                    className="font-medium text-slate-900 hover:text-indigo-600 transition-colors truncate"
                  >
                    {adr.titre}
                  </Link>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium">
                    {adr.projet}
                  </span>
                  <StatutBadge statut={adr.statut} />
                  <span className="text-xs text-slate-400">{Math.round(score * 100)}%</span>
                </div>
              </div>
              {adr.decision && (
                <p className="text-sm text-slate-500 line-clamp-2">{adr.decision}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
