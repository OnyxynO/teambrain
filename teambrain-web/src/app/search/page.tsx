"use client";

import Link from "next/link";
import { useState, useTransition, useEffect, useRef } from "react";
import {
  rechercherADR, listerProjets, getHealth, getIndexStatut, lancerIndexation,
  type ResultatRecherche, type ProjetInfo, type IndexStatut,
} from "@/lib/api";
import { StatutBadge } from "@/components/StatutBadge";

/* ── Types ── */

interface QualificatifDetecte {
  type: "statut" | "module" | "decideur" | "projet" | "in" | "phrase" | "regex" | "exclusion";
  valeur: string;
  raw: string; // texte brut dans la query, pour le badge
}

/* ── Parser léger côté client (pour les badges visuels) ── */

function detecterQualificatifs(q: string): QualificatifDetecte[] {
  const detectes: QualificatifDetecte[] = [];

  // Phrases exactes
  for (const m of q.matchAll(/"([^"]+)"/g)) {
    detectes.push({ type: "phrase", valeur: m[1], raw: m[0] });
  }
  // Regex
  for (const m of q.matchAll(/\/([^/]+)\//g)) {
    detectes.push({ type: "regex", valeur: m[1], raw: m[0] });
  }
  // Qualificatifs field:value
  const QUALS = ["statut", "module", "decideur", "projet", "in"] as const;
  for (const qual of QUALS) {
    for (const m of q.matchAll(new RegExp(`\\b${qual}:(\\S+)`, "gi"))) {
      detectes.push({ type: qual, valeur: m[1], raw: m[0] });
    }
  }
  // Exclusions -terme
  for (const m of q.matchAll(/(?:^|\s)(-\S+)/g)) {
    detectes.push({ type: "exclusion", valeur: m[1].slice(1), raw: m[1] });
  }
  return detectes;
}

/* ── Couleurs des badges qualificatifs ── */

const BADGE_STYLES: Record<QualificatifDetecte["type"], string> = {
  statut:    "bg-[#fbefff] text-[#8250df] border-[#d8b9ff]",
  module:    "bg-[#ddf4ff] text-[#0969da] border-[#b6d9f7]",
  decideur:  "bg-[#dafbe1] text-[#1a7f37] border-[#b5e9c0]",
  projet:    "bg-[#fff8c5] text-[#9a6700] border-[#e3b341]",
  in:        "bg-[#eaeef2] text-[#6e7781] border-[#d0d7de]",
  phrase:    "bg-[#1f2328] text-white border-[#1f2328]",
  regex:     "bg-[#ffebe9] text-[#d1242f] border-[#ffc1c0]",
  exclusion: "bg-[#ffebe9] text-[#d1242f] border-[#ffc1c0]",
};

const BADGE_LABELS: Record<QualificatifDetecte["type"], string> = {
  statut:    "statut",
  module:    "module",
  decideur:  "décideur",
  projet:    "projet",
  in:        "dans",
  phrase:    '"…"',
  regex:     "/regex/",
  exclusion: "–",
};

/* ── Référence aide ── */

const AIDE_SYNTAXE = [
  { exemple: 'statut:accepte', desc: 'Filtrer par statut (propose, accepte, deprecie, remplace)' },
  { exemple: 'module:auth', desc: 'Filtrer par module' },
  { exemple: 'decideur:alice', desc: 'Filtrer par décideur' },
  { exemple: 'projet:teambrain', desc: 'Filtrer par projet' },
  { exemple: 'in:titre', desc: 'Chercher uniquement dans un champ (titre, decision, contexte, consequences)' },
  { exemple: '"base de données"', desc: 'Phrase exacte' },
  { exemple: '/postgres|mysql/', desc: 'Expression régulière' },
  { exemple: '-terme', desc: 'Exclure un terme' },
];

/* ── Composants ── */

const inputCls =
  "w-full border border-[#d0d7de] rounded-md px-3 py-2 text-sm bg-white text-[#1f2328] " +
  "focus:outline-none focus:ring-2 focus:ring-[#0969da] focus:border-[#0969da] " +
  "placeholder:text-[#6e7781] transition-colors";

function BadgeQualificatif({ q }: { q: QualificatifDetecte }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${BADGE_STYLES[q.type]}`}>
      <span className="opacity-60">{BADGE_LABELS[q.type]}</span>
      <span className="font-mono">{q.valeur}</span>
    </span>
  );
}

function AideSyntaxe({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div className="bg-white border border-[#d0d7de] rounded-md p-4 space-y-2">
      <p className="text-xs font-semibold text-[#656d76] uppercase tracking-wider mb-3">
        Syntaxe de recherche
      </p>
      <div className="grid grid-cols-1 gap-1.5">
        {AIDE_SYNTAXE.map(({ exemple, desc }) => (
          <div key={exemple} className="flex items-baseline gap-3">
            <code className="font-mono text-xs text-[#0969da] bg-[#ddf4ff] px-1.5 py-0.5 rounded shrink-0 whitespace-nowrap">
              {exemple}
            </code>
            <span className="text-xs text-[#656d76]">{desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Page principale ── */

export default function PageRecherche() {
  const [query, setQuery] = useState("");
  const [semantic, setSemantic] = useState(false);
  const [resultats, setResultats] = useState<ResultatRecherche[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [rechercheFaite, setRechercheFaite] = useState(false);
  const [projets, setProjets] = useState<ProjetInfo[]>([]);
  const [aideVisible, setAideVisible] = useState(false);
  const [ollamaDisponible, setOllamaDisponible] = useState(false);
  const [indexStatuts, setIndexStatuts] = useState<Record<string, IndexStatut>>({});
  const inputRef = useRef<HTMLInputElement>(null);
  // Ref pour contrôler le polling par projet (faux = arrêt, ex : démontage du composant)
  const pollingActifRef = useRef<Record<string, boolean>>({});

  // Chargement initial : projets + health + statuts d'index en parallèle
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [ps, health] = await Promise.all([listerProjets(), getHealth()]);
        if (cancelled) return;
        setProjets(ps);
        setOllamaDisponible(health.ollama_disponible);
        const statuts = await Promise.all(ps.map((p) => getIndexStatut(p.id).catch(() => null)));
        if (cancelled) return;
        const map: Record<string, IndexStatut> = {};
        statuts.forEach((s) => { if (s) map[s.projet] = s; });
        setIndexStatuts(map);
      } catch {}
    })();
    return () => {
      cancelled = true;
      // Arrêter tous les pollings en cours si le composant est démonté
      Object.keys(pollingActifRef.current).forEach((k) => { pollingActifRef.current[k] = false; });
    };
  }, []);

  // Lancer l'indexation d'un projet + polling jusqu'à la fin
  async function demarrerIndex(nomProjet: string) {
    pollingActifRef.current[nomProjet] = true;
    try {
      const s = await lancerIndexation(nomProjet);
      setIndexStatuts((prev) => ({ ...prev, [nomProjet]: s }));
      const poll = async () => {
        if (!pollingActifRef.current[nomProjet]) return;
        try {
          const statut = await getIndexStatut(nomProjet);
          setIndexStatuts((prev) => ({ ...prev, [nomProjet]: statut }));
          if (statut.statut === "en_cours") {
            setTimeout(poll, 2000);
          } else {
            pollingActifRef.current[nomProjet] = false;
            // Rafraîchir la liste des projets pour mettre à jour index_disponible
            listerProjets().then((ps) => setProjets(ps)).catch(() => {});
          }
        } catch {
          pollingActifRef.current[nomProjet] = false;
        }
      };
      setTimeout(poll, 2000);
    } catch (err) {
      pollingActifRef.current[nomProjet] = false;
      setIndexStatuts((prev) => ({
        ...prev,
        [nomProjet]: {
          projet: nomProjet,
          statut: "erreur",
          detail: err instanceof Error ? err.message : "Erreur réseau",
        },
      }));
    }
  }

  // Si un seul projet a un index et que la recherche sémantique s'active,
  // injecter automatiquement projet:nom dans la query
  useEffect(() => {
    if (!semantic) return;
    const projetsIndexes = projets.filter((p) => p.index_disponible);
    if (projetsIndexes.length === 1 && !query.match(/\bprojet:/i)) {
      setQuery((q) => q ? `projet:${projetsIndexes[0].id} ${q}`.trim() : `projet:${projetsIndexes[0].id}`);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [semantic]);

  // Focus sur le champ au chargement
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const qualificatifs = detecterQualificatifs(query);

  // Calcul des conditions sémantiques (utilisé dans le formulaire + le panneau)
  const aUnIndex = projets.some((p) => p.index_disponible);
  const semantiqueActif = ollamaDisponible && aUnIndex;

  function rechercher(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!query.trim()) return;
    setErreur(null);
    startTransition(async () => {
      try {
        // Extraire le projet du qualificatif projet: côté client pour la recherche sémantique
        const projetMatch = query.match(/\bprojet:(\S+)/i);
        const projetPourSemantic = projetMatch?.[1];
        const data = await rechercherADR(query.trim(), {
          semantic,
          projet: projetPourSemantic,
        });
        setResultats(data.resultats);
        setRechercheFaite(true);
      } catch (err) {
        setErreur(err instanceof Error ? err.message : "Erreur de recherche");
        setResultats([]);
      }
    });
  }

  return (
    <div className="max-w-3xl space-y-4">

      {/* ── En-tête ── */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-[#1f2328]">Recherche</h1>
        <button
          type="button"
          onClick={() => setAideVisible((v) => !v)}
          className={[
            "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border transition-colors",
            aideVisible
              ? "bg-[#ddf4ff] text-[#0969da] border-[#0969da]"
              : "bg-white text-[#656d76] border-[#d0d7de] hover:bg-[#f6f8fa]",
          ].join(" ")}
          aria-expanded={aideVisible}
        >
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.92 6.085h.001a.749.749 0 1 1-1.342-.67C6.223 4.498 7.01 4 8 4a2.5 2.5 0 0 1 2.5 2.5c0 1.357-.87 2.024-1.55 2.535-.042.03-.083.06-.123.09a5.06 5.06 0 0 0-.44.39.3.3 0 0 0-.087.196v.25a.75.75 0 0 1-1.5 0V9.7c0-.44.169-.861.47-1.179.155-.162.328-.312.487-.445l.114-.087C8.5 7.61 9 7.24 9 6.5a1 1 0 0 0-2-.085ZM9 11a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z" />
          </svg>
          Syntaxe
        </button>
      </div>

      {/* ── Aide syntaxe ── */}
      <AideSyntaxe visible={aideVisible} />

      {/* ── Formulaire de recherche ── */}
      <form onSubmit={rechercher} className="space-y-2">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            {/* Icône loupe */}
            <span className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-[#6e7781]">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.499 4.499 0 1 0-8.997 0A4.499 4.499 0 0 0 11.5 7Z" />
              </svg>
            </span>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='statut:accepte module:auth "base de données"'
              className={`${inputCls} pl-9 pr-8`}
              aria-label="Requête de recherche"
            />
            {query && (
              <button
                type="button"
                onClick={() => { setQuery(""); setResultats([]); setRechercheFaite(false); }}
                className="absolute inset-y-0 right-2 flex items-center text-[#6e7781] hover:text-[#1f2328] px-1"
                aria-label="Effacer"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.749.749 0 0 1 1.275.326.749.749 0 0 1-.215.734L9.06 8l3.22 3.22a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215L8 9.06l-3.22 3.22a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z" />
                </svg>
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={isPending || !query.trim()}
            className="px-4 py-2 rounded-md text-sm font-medium text-white bg-[#1f883d] border border-[#1a7f37] hover:bg-[#1a7f37] disabled:opacity-50 transition-colors"
          >
            {isPending ? "…" : "Rechercher"}
          </button>
        </div>

        {/* ── Badges qualificatifs détectés ── */}
        {qualificatifs.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {qualificatifs.map((q, i) => (
              <BadgeQualificatif key={i} q={q} />
            ))}
          </div>
        )}

        {/* ── Option sémantique — toujours visible, désactivée si conditions non remplies ── */}
        <div className="flex items-center gap-3 px-1">
          <div className={`relative group/semantic flex items-center gap-2 ${!semantiqueActif ? "opacity-50" : ""}`}>
            <label className={`flex items-center gap-2 text-sm text-[#1f2328] select-none ${semantiqueActif ? "cursor-pointer" : "cursor-not-allowed"}`}>
              <input
                type="checkbox"
                checked={semantic}
                disabled={!semantiqueActif}
                onChange={(e) => setSemantic(e.target.checked)}
                className="rounded border-[#d0d7de] text-[#0969da] disabled:cursor-not-allowed"
              />
              Recherche sémantique
            </label>
            {/* Icône info + tooltip */}
            <span className="relative cursor-default">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="#6e7781"
                className="group-hover/semantic:fill-[#0969da] transition-colors" aria-hidden="true">
                <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM7.25 9.5V8.75a.75.75 0 0 1 1.5 0v.75h.25a.75.75 0 0 1 0 1.5h-2a.75.75 0 0 1 0-1.5h.25Zm1.5-3.75a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" />
              </svg>
              <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-30 opacity-0 group-hover/semantic:opacity-100 transition-opacity duration-150 w-64">
                <div className="bg-[#1f2328] text-white text-xs rounded-md px-3 py-2 shadow-lg leading-relaxed">
                  {!ollamaDisponible ? (
                    <><span className="text-[#f85149]">Ollama non disponible.</span> Lance <code className="font-mono bg-[#ffffff20] px-1 rounded">ollama serve</code> puis relance le serveur.</>
                  ) : !aUnIndex ? (
                    <><span className="text-[#d4a72c]">Aucun index construit.</span> Utilise le bouton <strong>Indexer</strong> ci-dessous pour chaque projet.</>
                  ) : (
                    <>Trouve des décisions <span className="text-[#7ee787]">sémantiquement proches</span> sans correspondance exacte des mots.</>
                  )}
                </div>
                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[#1f2328]" />
              </div>
            </span>
          </div>
          {semantic && semantiqueActif && projets.filter((p) => p.index_disponible).length > 1 && !query.match(/\bprojet:/i) && (
            <span className="text-[#9a6700] text-xs bg-[#fff8c5] px-2 py-0.5 rounded-full border border-[#e3b341]">
              ajouter <code className="font-mono">projet:nom</code> dans la requête
            </span>
          )}
        </div>
      </form>

      {/* ── Panneau d'indexation sémantique ── */}
      {ollamaDisponible && projets.length > 0 && (
        <details className="group" open={!projets.some((p) => p.index_disponible)}>
          <summary className="flex items-center gap-2 cursor-pointer list-none select-none text-sm text-[#656d76] hover:text-[#1f2328] transition-colors py-1">
            <svg
              width="12" height="12" viewBox="0 0 16 16" fill="currentColor"
              className="transition-transform group-open:rotate-90 shrink-0"
              aria-hidden="true"
            >
              <path d="M6.22 3.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L9.94 8 6.22 4.28a.75.75 0 0 1 0-1.06Z" />
            </svg>
            Index sémantique
            <span className="ml-1 text-xs text-[#6e7781]">
              ({projets.filter((p) => p.index_disponible).length}/{projets.length} prêt{projets.filter(p => p.index_disponible).length !== 1 ? "s" : ""})
            </span>
          </summary>
          <div className="mt-2 bg-white border border-[#d0d7de] rounded-md divide-y divide-[#d0d7de]">
            {projets.map((p) => {
              const s = indexStatuts[p.id];
              const enCours = s?.statut === "en_cours";
              const ok = p.index_disponible || s?.statut === "ok";
              const erreurIndex = s?.statut === "erreur";
              return (
                <div key={p.id} className="flex items-center justify-between px-4 py-2.5 gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-xs text-[#6e7781] shrink-0">{p.id}</span>
                    {/* Badge statut */}
                    {enCours ? (
                      <span className="inline-flex items-center gap-1 text-xs text-[#9a6700] bg-[#fff8c5] border border-[#e3b341] px-2 py-0.5 rounded-full">
                        <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" className="animate-spin" aria-hidden="true">
                          <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM1.5 8a6.5 6.5 0 1 1 13 0 6.5 6.5 0 0 1-13 0Z" opacity=".4"/>
                          <path d="M8 0a8 8 0 0 1 8 8h-1.5a6.5 6.5 0 0 0-6.5-6.5V0Z"/>
                        </svg>
                        En cours…
                      </span>
                    ) : ok ? (
                      <span className="inline-flex items-center gap-1 text-xs text-[#1a7f37] bg-[#dafbe1] border border-[#b5e9c0] px-2 py-0.5 rounded-full">
                        <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                          <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"/>
                        </svg>
                        Indexé
                        {s?.nb_adrs != null && <span className="opacity-70">— {s.nb_adrs} ADR</span>}
                      </span>
                    ) : erreurIndex ? (
                      <span className="inline-flex items-center gap-1 text-xs text-[#d1242f] bg-[#ffebe9] border border-[#ffc1c0] px-2 py-0.5 rounded-full" title={s?.detail ?? ""}>
                        <svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                          <path d="M4.47.22A.749.749 0 0 1 5 0h6c.199 0 .389.079.53.22l4.25 4.25c.141.14.22.331.22.53v6a.749.749 0 0 1-.22.53l-4.25 4.25A.749.749 0 0 1 11 16H5a.749.749 0 0 1-.53-.22L.22 11.53A.749.749 0 0 1 0 11V5c0-.199.079-.389.22-.53Zm.84 1.28L1.5 5.31v5.38l3.81 3.81h5.38l3.81-3.81V5.31L10.69 1.5ZM8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"/>
                        </svg>
                        Erreur
                      </span>
                    ) : (
                      <span className="text-xs text-[#6e7781]">Pas d'index</span>
                    )}
                  </div>
                  <button
                    type="button"
                    disabled={enCours}
                    onClick={() => demarrerIndex(p.id)}
                    className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium border transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-white border-[#d0d7de] text-[#24292f] hover:bg-[#f6f8fa] hover:border-[#b6bcc2]"
                  >
                    {enCours ? (
                      <><svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" className="animate-spin" aria-hidden="true"><path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM1.5 8a6.5 6.5 0 1 1 13 0 6.5 6.5 0 0 1-13 0Z" opacity=".4"/><path d="M8 0a8 8 0 0 1 8 8h-1.5a6.5 6.5 0 0 0-6.5-6.5V0Z"/></svg>En cours</>
                    ) : ok ? (
                      <><svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M1.5 8a6.5 6.5 0 1 1 13 0 6.5 6.5 0 0 1-13 0ZM0 8a8 8 0 1 0 16 0A8 8 0 0 0 0 8Zm6.5 3.25a.75.75 0 0 0 1.5 0v-5.5a.75.75 0 0 0-1.5 0v5.5Z"/></svg>Ré-indexer</>
                    ) : (
                      <><svg width="10" height="10" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 2a.75.75 0 0 1 .75.75v4.5h4.5a.75.75 0 0 1 0 1.5h-4.5v4.5a.75.75 0 0 1-1.5 0v-4.5h-4.5a.75.75 0 0 1 0-1.5h4.5v-4.5A.75.75 0 0 1 8 2Z"/></svg>Indexer</>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </details>
      )}

      {/* ── Erreur ── */}
      {erreur && (
        <div className="bg-[#ffebe9] border border-[#d1242f]/30 text-[#d1242f] rounded-md px-4 py-3 text-sm">
          {erreur}
        </div>
      )}

      {/* ── Aucun résultat ── */}
      {rechercheFaite && resultats.length === 0 && !erreur && (
        <div className="bg-white border border-[#d0d7de] rounded-md px-6 py-12 text-center">
          <svg width="24" height="24" viewBox="0 0 16 16" fill="#6e7781" className="mx-auto mb-3" aria-hidden="true">
            <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.499 4.499 0 1 0-8.997 0A4.499 4.499 0 0 0 11.5 7Z" />
          </svg>
          <p className="text-[#656d76] text-sm font-medium">
            Aucun résultat pour <span className="font-mono text-[#1f2328]">{query}</span>
          </p>
          <p className="text-[#6e7781] text-xs mt-1">
            Vérifiez la syntaxe ou essayez des termes plus larges
          </p>
        </div>
      )}

      {/* ── Résultats ── */}
      {resultats.length > 0 && (
        <div>
          <p className="text-sm text-[#656d76] mb-3">
            {resultats.length} résultat{resultats.length !== 1 ? "s" : ""}
            {semantic && <span className="ml-1 text-xs">(sémantique)</span>}
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
                    {score < 1 && (
                      <span className="text-xs text-[#6e7781] font-mono tabular-nums">
                        {Math.round(score * 100)}%
                      </span>
                    )}
                  </div>
                </div>
                {adr.modules.length > 0 && (
                  <div className="flex gap-1 mt-1.5 pl-16 flex-wrap">
                    {adr.modules.map((m) => (
                      <span key={m} className="text-xs text-[#6e7781] bg-[#eaeef2] border border-[#d0d7de] px-1.5 py-0 rounded-full">
                        {m}
                      </span>
                    ))}
                  </div>
                )}
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
