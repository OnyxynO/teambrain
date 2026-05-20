import Link from "next/link";
import { Suspense } from "react";
import { listerADR, getReferentiels } from "@/lib/api";
import { StatutBadge } from "@/components/StatutBadge";
import { FiltresADR } from "@/components/FiltresADR";

interface PageProps {
  searchParams: Promise<{ projet?: string; statut?: string; module?: string }>;
}

export default async function PageListe({ searchParams }: PageProps) {
  const { projet, statut, module } = await searchParams;

  const [adrs, refs] = await Promise.all([
    listerADR({ projet, statut, module }).catch(() => []),
    getReferentiels().catch(() => ({ modules: [], statuts: [], projets: [] })),
  ]);

  const multiProjets = refs.projets.length > 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Décisions d&apos;architecture</h1>
          <p className="text-sm text-slate-500 mt-1">{adrs.length} ADR</p>
        </div>
        <Link
          href="/nouveau"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
        >
          + Nouvelle décision
        </Link>
      </div>

      <Suspense>
        <FiltresADR
          statuts={refs.statuts}
          modules={refs.modules}
          projets={refs.projets}
        />
      </Suspense>

      {adrs.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <p className="text-lg">Aucun ADR trouvé</p>
          {(projet || statut || module) && (
            <p className="text-sm mt-2">
              <Link href="/" className="text-indigo-600 hover:underline">
                Effacer les filtres
              </Link>
            </p>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left px-4 py-3 font-medium text-slate-500 w-12">#</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500">Titre</th>
                {multiProjets && !projet && (
                  <th className="text-left px-4 py-3 font-medium text-slate-500 w-28">Projet</th>
                )}
                <th className="text-left px-4 py-3 font-medium text-slate-500">Modules</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500 w-28">Statut</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500 w-28">Date</th>
              </tr>
            </thead>
            <tbody>
              {adrs.map((adr) => (
                <tr
                  key={`${adr.projet}-${adr.id}`}
                  className="border-b border-slate-50 last:border-0 hover:bg-slate-50 transition-colors"
                >
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                    {String(adr.id).padStart(3, "0")}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/adr/${adr.projet}/${adr.id}`}
                      className="font-medium text-slate-900 hover:text-indigo-600 transition-colors"
                    >
                      {adr.titre}
                    </Link>
                  </td>
                  {multiProjets && !projet && (
                    <td className="px-4 py-3">
                      <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium">
                        {adr.projet}
                      </span>
                    </td>
                  )}
                  <td className="px-4 py-3 text-slate-500">
                    {adr.modules.length > 0 ? adr.modules.join(", ") : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatutBadge statut={adr.statut} />
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{adr.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
