"use client";

import Link from "next/link";
import { useState, useTransition, useEffect } from "react";
import { rechercherADR, listerProjets, type ResultatRecherche, type ProjetInfo } from "@/lib/api";
import { StatutBadge } from "@/components/StatutBadge";

const inputCls =
  "border border-[#d0d7de] rounded-md px-3 py-2 text-sm bg-white text-[#1f2328] " +
  "focus:outline-none focus:ring-2 focus:ring-[#0969da] focus:border-[#0969da] " +
  "placeholder:text-[#6e7781] transition-colors";

const selectCls =
  "text-sm border border-[#d0d7de] rounded-md px-3 py-1.5 bg-white text-[#1f2328] " +
  "focus:outline-none focus:ring-2 focus:ring-[#0969da] transition-colors cursor-pointer";

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

  function rechercher(e: React.FormEvent<HTMLFormElement>) {
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
    <div className="max-w-3xl space-y-4">
      <h1 className="text-xl font-semibold text-[#1f2328]">Recherche</h1>

      <form onSubmit={rechercher} className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher dans les décisions…"
            className={`flex-1 ${inputCls}`}
          />
          <button
            type="submit"
            disabled={isPending || !query.trim()}
            className="px-4 py-2 rounded-md text-sm font-medium text-white bg-[#1f883d] border border-[#1a7f37] hover:bg-[#1a7f37] disabled:opacity-50 transition-colors"
          >
            {isPending ? "…" : "Rechercher"}
          </button>
        </div>

        <div className="flex gap-3 flex-wrap items-center">
          {projets.length > 1 && (
            <select
              value={projetFiltre}
              onChange={(e) => setProjetFiltre(e.target.value)}
              className={selectCls}
            >
              <option value="">Tous les projets</option>
              {projets.map((p) => (
                <option key={p.id} value={p.id}>{p.nom}</option>
              ))}
            </select>
          )}

          <label className="flex items-center gap-2 text-sm text-[#1f2328] cursor-pointer select-none">
            <input
              type="checkbox"
              checked={semantic}
              onChange={(e) => setSemantic(e.target.checked)}
              className="rounded border-[#d0d7de] text-[#0969da]"
            />
            Recherche sémantique
            {semantic && !projetFiltre && projets.length > 1 && (
              <span className="text-[#9a6700] text-xs bg-[#fff8c5] px-2 py-0.5 rounded-full">
                sélectionne un projet
              </span>
            )}
          </label>
        </div>
      </form>

      {erreur && (
        <div className="bg-[#ffebe9] border border-[#d1242f]/30 text-[#d1242f] rounded-md px-4 py-3 text-sm">
          {erreur}
        </div>
      )}

      {semantic && indexDispo === false && (
        <div className="bg-[#fff8c5] border border-[#d4a72c] text-[#9a6700] rounded-md px-4 py-3 text-sm">
          Index sémantique non disponible.{" "}
          Lance <code className="font-mono bg-[#fff8c5] px-1 rounded">teambrain index</code> dans le repo concerné.
        </div>
      )}

      {rechercheFaite && resultats.length === 0 && !erreur && (
        <p className="text-[#656d76] text-sm">
          Aucun résultat pour <strong>&laquo;{query}&raquo;</strong>
        </p>
      )}

      {resultats.length > 0 && (
        <div>
          <p className="text-sm text-[#656d76] mb-3">
            {resultats.length} résultat{resultats.length !== 1 ? "s" : ""}
          </p>
          <div className="bg-white border border-[#d0d7de] rounded-md overflow-hidden divide-y divide-[#d0d7de]">
            {resultats.map(({ adr, score }) => (
              <div
                key={`${adr.projet}-${adr.id}`}
                className="px-4 py-3 hover:bg-[#f6f8fa] transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <span className="font-mono text-xs text-[#6e7781] bg-[#eaeef2] px-2 py-0.5 rounded-full shrink-0">
                      #{String(adr.id).padStart(3, "0")}
                    </span>
                    <Link
                      href={`/adr/?projet=${adr.projet}&id=${adr.id}`}
                      className="font-semibold text-[#1f2328] hover:text-[#0969da] transition-colors truncate"
                    >
                      {adr.titre}
                    </Link>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="inline-block px-2 py-0 rounded-full text-xs font-medium border border-[#d0d7de] bg-[#ddf4ff] text-[#0550ae]">
                      {adr.projet}
                    </span>
                    <StatutBadge statut={adr.statut} />
                    <span className="text-xs text-[#6e7781] font-mono">
                      {Math.round(score * 100)}%
                    </span>
                  </div>
                </div>
                {adr.decision && (
                  <p className="text-sm text-[#656d76] line-clamp-2 mt-1.5 pl-16">
                    {adr.decision}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
