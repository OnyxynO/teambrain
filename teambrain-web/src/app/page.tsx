"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { listerADR, getReferentiels, type ADR, type Referentiels } from "@/lib/api";
import { StatutIcone } from "@/components/StatutBadge";
import { FiltresADR } from "@/components/FiltresADR";

const LABELS_MODULE_MAX = 3;

function ModulesTags({ modules }: { modules: string[] }) {
  if (modules.length === 0) return null;
  const visibles = modules.slice(0, LABELS_MODULE_MAX);
  const reste = modules.length - LABELS_MODULE_MAX;
  return (
    <span className="flex items-center gap-1 flex-wrap">
      {visibles.map((m) => (
        <span
          key={m}
          className="inline-block px-2 py-0 rounded-full text-xs font-medium border border-[#d0d7de] bg-[#eaeef2] text-[#6e7781]"
        >
          {m}
        </span>
      ))}
      {reste > 0 && (
        <span className="text-xs text-[#6e7781]">+{reste}</span>
      )}
    </span>
  );
}

function ProjetTag({ projet }: { projet: string }) {
  return (
    <span className="inline-block px-2 py-0 rounded-full text-xs font-medium border border-[#d0d7de] bg-[#ddf4ff] text-[#0550ae]">
      {projet}
    </span>
  );
}

function ListeADR() {
  const params = useSearchParams();
  const projet = params.get("projet") ?? undefined;
  const statut = params.get("statut") ?? undefined;
  const module = params.get("module") ?? undefined;

  const [adrs, setAdrs] = useState<ADR[]>([]);
  const [refs, setRefs] = useState<Referentiels>({ modules: [], statuts: [], projets: [] });
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    setChargement(true);
    Promise.all([
      listerADR({ projet, statut, module }).catch(() => []),
      getReferentiels().catch(() => ({ modules: [], statuts: [], projets: [] })),
    ]).then(([a, r]) => {
      setAdrs(a);
      setRefs(r);
      setChargement(false);
    });
  }, [projet, statut, module]);

  const multiProjets = refs.projets.length > 1;

  return (
    <div className="space-y-4">
      {/* ── En-tête ── */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-[#1f2328]">
            Décisions d&apos;architecture
          </h1>
          {!chargement && (
            <p className="text-sm text-[#656d76] mt-0.5">
              {adrs.length} ADR{adrs.length !== 1 ? "s" : ""}
              {projet ? ` dans ${projet}` : ""}
            </p>
          )}
        </div>
        <Link
          href="/nouveau/"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-white border border-[#1a7f37] transition-colors"
          style={{ backgroundColor: "#1f883d" }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#1a7f37")}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#1f883d")}
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M7.75 2a.75.75 0 0 1 .75.75V7h4.25a.75.75 0 0 1 0 1.5H8.5v4.25a.75.75 0 0 1-1.5 0V8.5H2.75a.75.75 0 0 1 0-1.5H7V2.75A.75.75 0 0 1 7.75 2Z" />
          </svg>
          Nouvelle décision
        </Link>
      </div>

      {/* ── Filtres ── */}
      <FiltresADR
        statuts={refs.statuts}
        modules={refs.modules}
        projets={refs.projets}
      />

      {/* ── Liste ── */}
      {chargement ? (
        <div className="text-center py-16 text-[#656d76] text-sm">Chargement…</div>
      ) : adrs.length === 0 ? (
        <div className="bg-white border border-[#d0d7de] rounded-md px-8 py-16 text-center">
          <p className="text-[#656d76]">Aucune décision trouvée</p>
          {(projet || statut || module) && (
            <p className="text-sm mt-2">
              <Link href="/" className="text-[#0969da] hover:underline">
                Effacer les filtres
              </Link>
            </p>
          )}
        </div>
      ) : (
        <div className="bg-white border border-[#d0d7de] rounded-md overflow-hidden">
          {/* Barre de comptage */}
          <div className="px-4 py-2.5 bg-[#f6f8fa] border-b border-[#d0d7de] flex items-center gap-4">
            <span className="text-sm font-semibold text-[#1f2328]">
              {adrs.length} décision{adrs.length !== 1 ? "s" : ""}
            </span>
          </div>

          {/* Items */}
          <ul className="divide-y divide-[#d0d7de]">
            {adrs.map((adr) => (
              <li
                key={`${adr.projet}-${adr.id}`}
                className="flex items-start gap-3 px-4 py-3 hover:bg-[#f6f8fa] transition-colors"
              >
                {/* Icône statut */}
                <StatutIcone statut={adr.statut} size={18} />

                {/* Contenu principal */}
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-start gap-2 flex-wrap">
                    <Link
                      href={`/adr/?projet=${adr.projet}&id=${adr.id}`}
                      className="font-semibold text-[#1f2328] hover:text-[#0969da] transition-colors leading-snug"
                    >
                      {adr.titre}
                    </Link>
                    {multiProjets && !projet && <ProjetTag projet={adr.projet} />}
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-[#656d76]">
                      <span className="font-mono">#{String(adr.id).padStart(3, "0")}</span>
                      {" · "}{adr.date}
                    </span>
                    {adr.modules.length > 0 && (
                      <>
                        <span className="text-[#d0d7de]">·</span>
                        <ModulesTags modules={adr.modules} />
                      </>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function PageListe() {
  return (
    <Suspense>
      <ListeADR />
    </Suspense>
  );
}
