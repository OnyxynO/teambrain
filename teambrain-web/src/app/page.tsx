"use client";

import { useEffect, useState, useMemo, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { listerADR, getReferentiels, type ADR, type Referentiels } from "@/lib/api";
import { StatutIcone } from "@/components/StatutBadge";

/* ── Constantes ── */

const ACTIFS   = ["propose", "accepte"];
const ARCHIVES = ["deprecie", "remplace"];
type Groupe = "actifs" | "archives";
type Sort   = "newest" | "oldest" | "alpha";

/* ── Dropdown Modules ── */

function DropdownModules({
  modules,
  actif,
  onChange,
}: {
  modules: string[];
  actif: string;
  onChange: (v: string) => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function clic(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOuvert(false);
    }
    document.addEventListener("mousedown", clic);
    return () => document.removeEventListener("mousedown", clic);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOuvert((o) => !o)}
        className={[
          "inline-flex items-center gap-1 px-3 py-2 text-sm border rounded-md transition-colors",
          actif
            ? "border-[#0969da] bg-[#ddf4ff] text-[#0969da] font-medium"
            : "border-[#d0d7de] bg-white text-[#1f2328] hover:bg-[#f6f8fa]",
        ].join(" ")}
      >
        Modules
        {actif && (
          <span className="text-xs bg-[#0969da] text-white rounded-full px-1.5 font-medium">1</span>
        )}
        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" className={ouvert ? "rotate-180" : ""} style={{ transition: "transform .15s" }}>
          <path d="M4.427 7.427l3.396 3.396a.25.25 0 0 0 .354 0l3.396-3.396A.25.25 0 0 0 11.396 7H4.604a.25.25 0 0 0-.177.427Z" />
        </svg>
      </button>

      {ouvert && (
        <div className="absolute top-full left-0 mt-1 w-52 bg-white border border-[#d0d7de] rounded-md shadow-lg z-20 overflow-hidden">
          <div className="px-3 py-2 border-b border-[#d0d7de]">
            <p className="text-xs font-semibold text-[#1f2328]">Filtrer par module</p>
          </div>
          <ul className="py-1 max-h-64 overflow-y-auto">
            <li>
              <button
                onClick={() => { onChange(""); setOuvert(false); }}
                className={[
                  "w-full text-left px-4 py-2 text-sm flex items-center gap-2 hover:bg-[#f6f8fa]",
                  !actif ? "font-semibold text-[#1f2328]" : "text-[#656d76]",
                ].join(" ")}
              >
                {!actif && (
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="#1f883d">
                    <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z" />
                  </svg>
                )}
                <span className={!actif ? "ml-0" : "ml-5"}>Tous les modules</span>
              </button>
            </li>
            {modules.map((m) => (
              <li key={m}>
                <button
                  onClick={() => { onChange(m); setOuvert(false); }}
                  className={[
                    "w-full text-left px-4 py-2 text-sm flex items-center gap-2 hover:bg-[#f6f8fa]",
                    actif === m ? "font-semibold text-[#1f2328]" : "text-[#656d76]",
                  ].join(" ")}
                >
                  {actif === m && (
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="#1f883d" className="shrink-0">
                      <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z" />
                    </svg>
                  )}
                  <span className={actif === m ? "ml-0" : "ml-5"}>{m}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ── Page principale ── */

function ListeADR() {
  const params = useSearchParams();
  const router = useRouter();
  const projet = params.get("projet") ?? undefined;
  const module = params.get("module") ?? undefined;

  const [adrs, setAdrs]       = useState<ADR[]>([]);
  const [refs, setRefs]       = useState<Referentiels>({ modules: [], statuts: [], projets: [] });
  const [chargement, setChargement] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [groupe, setGroupe]   = useState<Groupe>("actifs");
  const [sort, setSort]       = useState<Sort>("newest");

  useEffect(() => {
    setChargement(true);
    Promise.all([
      listerADR({ projet, module }).catch(() => []),
      getReferentiels().catch(() => ({ modules: [], statuts: [], projets: [] })),
    ]).then(([a, r]) => {
      setAdrs(a);
      setRefs(r);
      setChargement(false);
    });
  }, [projet, module]);

  /* Changer le filtre module via URL */
  function changerModule(val: string) {
    const next = new URLSearchParams(params.toString());
    if (val) next.set("module", val);
    else next.delete("module");
    router.push(`/?${next}`);
  }

  /* ADRs filtrés, groupés, triés */
  const adrsAffichés = useMemo(() => {
    const grouped = groupe === "actifs"
      ? adrs.filter((a) => ACTIFS.includes(a.statut))
      : adrs.filter((a) => ARCHIVES.includes(a.statut));

    const filtered = searchQuery.trim()
      ? grouped.filter((a) =>
          a.titre.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (a.contexte ?? "").toLowerCase().includes(searchQuery.toLowerCase())
        )
      : grouped;

    return [...filtered].sort((a, b) => {
      if (sort === "alpha")   return a.titre.localeCompare(b.titre, "fr");
      const da = new Date(a.date).getTime();
      const db = new Date(b.date).getTime();
      return sort === "newest" ? db - da : da - db;
    });
  }, [adrs, groupe, searchQuery, sort]);

  const cntActifs   = adrs.filter((a) => ACTIFS.includes(a.statut)).length;
  const cntArchives = adrs.filter((a) => ARCHIVES.includes(a.statut)).length;
  const multiProjets = refs.projets.length > 1;

  return (
    <div className="space-y-3">

      {/* ── Barre de recherche + actions ── */}
      <div className="flex items-center gap-2 flex-wrap">

        {/* Champ de recherche */}
        <div className="flex-1 min-w-48 relative">
          <span className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-[#6e7781]">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.499 4.499 0 1 0-8.997 0A4.499 4.499 0 0 0 11.5 7Z" />
            </svg>
          </span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filtrer par titre ou contexte…"
            className="w-full border border-[#d0d7de] rounded-md pl-9 pr-3 py-2 text-sm bg-white text-[#1f2328] focus:outline-none focus:ring-2 focus:ring-[#0969da] focus:border-[#0969da] placeholder:text-[#6e7781]"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute inset-y-0 right-2 flex items-center text-[#6e7781] hover:text-[#1f2328] px-1"
              aria-label="Effacer la recherche"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.749.749 0 0 1 1.275.326.749.749 0 0 1-.215.734L9.06 8l3.22 3.22a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215L8 9.06l-3.22 3.22a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z" />
              </svg>
            </button>
          )}
        </div>

        {/* Dropdown Modules */}
        {refs.modules.length > 0 && (
          <DropdownModules
            modules={refs.modules}
            actif={module ?? ""}
            onChange={changerModule}
          />
        )}
      </div>

      {/* ── Liste avec tabs ── */}
      {chargement ? (
        <div className="text-center py-16 text-[#656d76] text-sm">Chargement…</div>
      ) : (
        <div className="bg-white border border-[#d0d7de] rounded-md overflow-hidden">

          {/* ── Tabs + sort ── */}
          <div className="flex items-center border-b border-[#d0d7de] px-4 bg-[#f6f8fa]">

            {/* Onglet Actifs */}
            <button
              onClick={() => setGroupe("actifs")}
              className={[
                "flex items-center gap-1.5 px-3 py-2.5 text-sm border-b-2 -mb-px transition-colors",
                groupe === "actifs"
                  ? "border-[#fd8c73] text-[#1f2328] font-semibold"
                  : "border-transparent text-[#656d76] hover:text-[#1f2328]",
              ].join(" ")}
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
                <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z" />
              </svg>
              Actifs
              <span className="text-xs tabular-nums bg-[#eaeef2] text-[#6e7781] px-1.5 py-0.5 rounded-full">
                {cntActifs}
              </span>
            </button>

            {/* Onglet Archivés */}
            <button
              onClick={() => setGroupe("archives")}
              className={[
                "flex items-center gap-1.5 px-3 py-2.5 text-sm border-b-2 -mb-px transition-colors",
                groupe === "archives"
                  ? "border-[#fd8c73] text-[#1f2328] font-semibold"
                  : "border-transparent text-[#656d76] hover:text-[#1f2328]",
              ].join(" ")}
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 16A8 8 0 1 1 8 0a8 8 0 0 1 0 16Zm3.78-9.72a.75.75 0 0 0-1.06-1.06L6.75 9.19 5.28 7.72a.75.75 0 0 0-1.06 1.06l2 2a.75.75 0 0 0 1.06 0l4.5-4.5Z" />
              </svg>
              Archivés
              <span className="text-xs tabular-nums bg-[#eaeef2] text-[#6e7781] px-1.5 py-0.5 rounded-full">
                {cntArchives}
              </span>
            </button>

            <div className="flex-1" />

            {/* Sort */}
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as Sort)}
              className="text-xs text-[#656d76] bg-transparent border-0 cursor-pointer focus:outline-none py-2.5 pr-1"
            >
              <option value="newest">↓ Plus récent</option>
              <option value="oldest">↑ Plus ancien</option>
              <option value="alpha">A → Z</option>
            </select>
          </div>

          {/* ── Items ── */}
          {adrsAffichés.length === 0 ? (
            <div className="px-4 py-14 text-center">
              <p className="text-[#656d76] text-sm">
                {searchQuery
                  ? `Aucun résultat pour « ${searchQuery} »`
                  : groupe === "actifs"
                  ? "Aucune décision active"
                  : "Aucune décision archivée"}
              </p>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="text-[#0969da] text-sm hover:underline mt-1"
                >
                  Effacer la recherche
                </button>
              )}
            </div>
          ) : (
            <ul className="divide-y divide-[#d0d7de]">
              {adrsAffichés.map((adr) => (
                <li
                  key={`${adr.projet}-${adr.id}`}
                  className="flex items-start gap-3 px-4 py-3 hover:bg-[#f6f8fa] transition-colors"
                >
                  {/* Icône statut */}
                  <span className="mt-0.5 shrink-0">
                    <StatutIcone statut={adr.statut} size={18} />
                  </span>

                  {/* Contenu */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3">
                      {/* Titre + méta */}
                      <div className="min-w-0">
                        <Link
                          href={`/adr/?projet=${adr.projet}&id=${adr.id}`}
                          className="font-semibold text-[#1f2328] hover:text-[#0969da] transition-colors leading-snug"
                        >
                          {adr.titre}
                        </Link>
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                          <span className="text-xs text-[#6e7781]">
                            <span className="font-mono">#{String(adr.id).padStart(3, "0")}</span>
                            {" · "}{adr.date}
                            {multiProjets && (
                              <>
                                {" · "}
                                <Link href={`/?projet=${adr.projet}`} className="hover:text-[#0969da]">
                                  {adr.projet}
                                </Link>
                              </>
                            )}
                          </span>
                        </div>
                      </div>

                      {/* Labels modules (droite) */}
                      {adr.modules.length > 0 && (
                        <div className="flex items-center gap-1 flex-wrap justify-end shrink-0">
                          {adr.modules.slice(0, 3).map((m) => (
                            <button
                              key={m}
                              onClick={() => changerModule(module === m ? "" : m)}
                              className="inline-block px-2 py-0.5 rounded-full text-xs font-medium border border-[#d0d7de] bg-[#eaeef2] text-[#6e7781] hover:border-[#0969da] hover:bg-[#ddf4ff] hover:text-[#0969da] transition-colors"
                            >
                              {m}
                            </button>
                          ))}
                          {adr.modules.length > 3 && (
                            <span className="text-xs text-[#6e7781]">
                              +{adr.modules.length - 3}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
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
