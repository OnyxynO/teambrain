"use client";

import { useEffect, useState, useTransition, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getADR, modifierADR, supprimerADR, type ADR } from "@/lib/api";
import { StatutBadge } from "@/components/StatutBadge";

/* ── Helpers ── */

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
    titre:       adr.titre,
    statut:      adr.statut,
    date:        adr.date,
    modules:     adr.modules.join(", "),
    decideurs:   adr.decideurs.join(", "),
    contexte:    adr.contexte,
    decision:    adr.decision,
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

/* ── Composants UI ── */

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

const btnDanger =
  "inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium " +
  "text-[#d1242f] bg-white border border-[#d0d7de] hover:bg-[#ffebe9] " +
  "hover:border-[#d1242f] disabled:opacity-50 transition-colors";

function SectionContent({ titre, contenu }: { titre: string; contenu: string }) {
  if (!contenu) return null;
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-[#656d76] mb-3">
        {titre}
      </h2>
      <div className="text-[#1f2328] text-sm leading-relaxed whitespace-pre-wrap">
        {contenu}
      </div>
    </div>
  );
}

function SectionConsequences({ contenu }: { contenu: string }) {
  if (!contenu) return null;
  const parsed = parseConsequencesPythonDict(contenu);
  return (
    <div>
      <h2 className="text-xs font-semibold uppercase tracking-widest text-[#656d76] mb-3">
        Conséquences
      </h2>
      {parsed ? (
        <div className="space-y-4">
          {parsed.positives.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-[#1a7f37] uppercase tracking-wide mb-2">
                Positives
              </p>
              <ul className="space-y-1.5">
                {parsed.positives.map((item, i) => (
                  <li key={i} className="flex gap-2 text-sm text-[#1f2328] leading-snug">
                    <span className="text-[#1a7f37] font-bold shrink-0">+</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {parsed.negatives.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-[#d1242f] uppercase tracking-wide mb-2">
                Négatives
              </p>
              <ul className="space-y-1.5">
                {parsed.negatives.map((item, i) => (
                  <li key={i} className="flex gap-2 text-sm text-[#1f2328] leading-snug">
                    <span className="text-[#d1242f] font-bold shrink-0">−</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="text-[#1f2328] text-sm leading-relaxed whitespace-pre-wrap">
          {contenu}
        </div>
      )}
    </div>
  );
}

function SidebarSection({ titre, children }: { titre: string; children: React.ReactNode }) {
  return (
    <div className="py-4 border-b border-[#d0d7de] last:border-0">
      <h3 className="text-xs font-semibold text-[#1f2328] mb-2">{titre}</h3>
      {children}
    </div>
  );
}

function ChampTextarea({
  id, label, hint, value, onChange,
}: {
  id: string;
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
        rows={4}
        className={`${inputCls} resize-y`}
      />
    </div>
  );
}

/* ── Page principale ── */

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
    setChamps((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function sauvegarder() {
    if (!champs) return;
    setErreurSave(null);
    startTransition(async () => {
      try {
        const mis_a_jour = await modifierADR(projet, id, {
          titre:        champs.titre,
          statut:       champs.statut,
          modules:      champs.modules.split(",").map((s) => s.trim()).filter(Boolean),
          decideurs:    champs.decideurs.split(",").map((s) => s.trim()).filter(Boolean),
          contexte:     champs.contexte,
          decision:     champs.decision,
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
    return <div className="text-center py-16 text-[#656d76] text-sm">Chargement…</div>;
  }

  if (erreur || !adr) {
    return (
      <div className="text-center py-16 text-[#656d76]">
        <p>{erreur ?? "ADR introuvable"}</p>
        <Link href="/" className="text-[#0969da] hover:underline text-sm mt-2 block">
          ← Retour à la liste
        </Link>
      </div>
    );
  }

  /* ── Mode édition ── */
  if (modeEdit && champs) {
    return (
      <div className="max-w-4xl space-y-6">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-[#656d76]">
          <Link href="/" className="hover:text-[#0969da] transition-colors">
            Décisions
          </Link>
          <span className="text-[#d0d7de]">/</span>
          <Link
            href={`/?projet=${projet}`}
            className="hover:text-[#0969da] transition-colors"
          >
            {projet}
          </Link>
          <span className="text-[#d0d7de]">/</span>
          <span className="font-mono text-xs">#{String(adr.id).padStart(3, "0")}</span>
          <span className="text-[#d0d7de]">/</span>
          <span>Édition</span>
        </nav>

        {erreurSave && (
          <div className="bg-[#ffebe9] border border-[#d1242f]/30 text-[#d1242f] rounded-md px-4 py-3 text-sm">
            {erreurSave}
          </div>
        )}

        <div className="bg-white border border-[#d0d7de] rounded-md p-6 space-y-5">
          <h1 className="text-base font-semibold text-[#1f2328]">
            Édition — <span className="font-mono text-[#656d76]">#{String(adr.id).padStart(3, "0")}</span>
          </h1>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 space-y-1.5">
              <label htmlFor="edit-titre" className="block text-sm font-medium text-[#1f2328]">Titre</label>
              <input
                id="edit-titre"
                type="text"
                value={champs.titre}
                onChange={(e) => setChamp("titre", e.target.value)}
                className={inputCls}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="edit-statut" className="block text-sm font-medium text-[#1f2328]">Statut</label>
              <select
                id="edit-statut"
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
              <label htmlFor="edit-date" className="block text-sm font-medium text-[#1f2328]">Date</label>
              <input
                id="edit-date"
                type="date"
                value={champs.date}
                onChange={(e) => setChamp("date", e.target.value)}
                className={inputCls}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="edit-modules" className="block text-sm font-medium text-[#1f2328]">
                Modules
                <span className="text-[#656d76] font-normal ml-1">(virgule)</span>
              </label>
              <input
                id="edit-modules"
                type="text"
                value={champs.modules}
                onChange={(e) => setChamp("modules", e.target.value)}
                placeholder="api, core"
                className={inputCls}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="edit-decideurs" className="block text-sm font-medium text-[#1f2328]">
                Décideurs
                <span className="text-[#656d76] font-normal ml-1">(virgule)</span>
              </label>
              <input
                id="edit-decideurs"
                type="text"
                value={champs.decideurs}
                onChange={(e) => setChamp("decideurs", e.target.value)}
                placeholder="alice, bob"
                className={inputCls}
              />
            </div>
          </div>

          <hr className="border-[#d0d7de]" />

          <ChampTextarea id="edit-contexte"      label="Contexte"      hint="Quel problème ?"        value={champs.contexte}      onChange={(v) => setChamp("contexte", v)} />
          <ChampTextarea id="edit-decision"      label="Décision"      hint="Qu'a-t-on décidé ?"     value={champs.decision}      onChange={(v) => setChamp("decision", v)} />
          <ChampTextarea id="edit-consequences"  label="Conséquences"  hint="Impacts, compromis"     value={champs.consequences}  onChange={(v) => setChamp("consequences", v)} />

          <div className="flex gap-2 pt-2">
            <button
              onClick={sauvegarder}
              disabled={isPending || !champs.titre.trim()}
              className={btnPrimary}
            >
              {isPending ? "Sauvegarde…" : "Sauvegarder les modifications"}
            </button>
            <button onClick={annulerEdit} disabled={isPending} className={btnSecondary}>
              Annuler
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ── Mode lecture ── */
  return (
    <div className="space-y-4 max-w-4xl">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-[#656d76]">
        <Link href="/" className="hover:text-[#0969da] transition-colors">
          Décisions
        </Link>
        <span className="text-[#d0d7de]">/</span>
        <Link
          href={`/?projet=${projet}`}
          className="hover:text-[#0969da] transition-colors"
        >
          {projet}
        </Link>
        <span className="text-[#d0d7de]">/</span>
        <span className="font-mono text-xs">#{String(adr.id).padStart(3, "0")}</span>
      </nav>

      {erreurSave && (
        <div className="bg-[#ffebe9] border border-[#d1242f]/30 text-[#d1242f] rounded-md px-4 py-3 text-sm">
          {erreurSave}
        </div>
      )}

      {/* ── Titre + actions ── */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-semibold text-[#1f2328] leading-snug flex-1">
            {adr.titre}
          </h1>
          {/* Actions */}
          <div className="flex items-center gap-2 shrink-0 mt-0.5">
            <button onClick={ouvrirEdit} className={btnSecondary}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" className="mr-1.5" aria-hidden="true">
                <path d="M11.013 1.427a1.75 1.75 0 0 1 2.474 0l1.086 1.086a1.75 1.75 0 0 1 0 2.474l-8.61 8.61c-.21.21-.47.364-.756.445l-3.251.93a.75.75 0 0 1-.927-.928l.929-3.25c.081-.286.235-.547.445-.758l8.61-8.61Zm.176 4.823L9.75 4.81l-6.286 6.287a.253.253 0 0 0-.064.108l-.558 1.953 1.953-.558a.253.253 0 0 0 .108-.064Zm1.238-3.763a.25.25 0 0 0-.354 0L10.811 3.75l1.439 1.44 1.263-1.263a.25.25 0 0 0 0-.354Z" />
              </svg>
              Éditer
            </button>
            {!confirmSuppression ? (
              <button onClick={() => setConfirmSuppression(true)} className={btnDanger}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" className="mr-1.5" aria-hidden="true">
                  <path d="M11 1.75V3h2.25a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1 0-1.5H5V1.75C5 .784 5.784 0 6.75 0h2.5C10.216 0 11 .784 11 1.75ZM4.496 6.675l.66 6.6a.25.25 0 0 0 .249.225h5.19a.25.25 0 0 0 .249-.225l.66-6.6a.75.75 0 0 1 1.492.149l-.66 6.6A1.748 1.748 0 0 1 10.595 15h-5.19a1.75 1.75 0 0 1-1.741-1.576l-.66-6.6a.75.75 0 1 1 1.492-.149Z" />
                </svg>
                Supprimer
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-sm text-[#d1242f] font-medium">Confirmer ?</span>
                <button
                  onClick={supprimer}
                  disabled={isPending}
                  className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium text-white bg-[#d1242f] hover:bg-[#a40e26] disabled:opacity-50 transition-colors"
                >
                  {isPending ? "Suppression…" : "Oui, supprimer"}
                </button>
                <button onClick={() => setConfirmSuppression(false)} className={btnSecondary}>
                  Annuler
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Ligne de métadonnées inline */}
        <div className="flex items-center gap-2 flex-wrap text-sm text-[#656d76]">
          <StatutBadge statut={adr.statut} />
          <span className="font-mono text-xs bg-[#eaeef2] text-[#6e7781] px-2 py-0.5 rounded-full">
            #{String(adr.id).padStart(3, "0")}
          </span>
          <span>·</span>
          <span>{adr.date}</span>
          {adr.decideurs.length > 0 && (
            <>
              <span>·</span>
              <span>{adr.decideurs.join(", ")}</span>
            </>
          )}
        </div>
      </div>

      <hr className="border-[#d0d7de]" />

      {/* ── Layout deux colonnes ── */}
      <div className="flex gap-8 items-start">
        {/* Contenu principal */}
        <div className="flex-1 min-w-0 space-y-8">
          <SectionContent titre="Contexte" contenu={adr.contexte} />
          <SectionContent titre="Décision" contenu={adr.decision} />
          <SectionConsequences contenu={adr.consequences} />
        </div>

        {/* Sidebar */}
        <aside className="w-56 shrink-0">
          <SidebarSection titre="Statut">
            <StatutBadge statut={adr.statut} />
          </SidebarSection>

          <SidebarSection titre="Projet">
            <Link
              href={`/?projet=${adr.projet}`}
              className="inline-flex items-center gap-1 text-sm text-[#0969da] hover:underline"
            >
              {adr.projet}
            </Link>
          </SidebarSection>

          {adr.modules.length > 0 && (
            <SidebarSection titre="Modules">
              <div className="flex flex-wrap gap-1.5">
                {adr.modules.map((m) => (
                  <Link
                    key={m}
                    href={`/?module=${m}`}
                    className="inline-block px-2 py-0.5 rounded-full text-xs font-medium border border-[#d0d7de] bg-[#eaeef2] text-[#6e7781] hover:border-[#57606a] transition-colors"
                  >
                    {m}
                  </Link>
                ))}
              </div>
            </SidebarSection>
          )}

          {adr.decideurs.length > 0 && (
            <SidebarSection titre="Décideurs">
              <ul className="space-y-1">
                {adr.decideurs.map((d) => (
                  <li key={d} className="text-sm text-[#1f2328] flex items-center gap-1.5">
                    <span className="inline-block w-5 h-5 rounded-full bg-[#eaeef2] text-center text-xs leading-5 text-[#656d76] font-medium shrink-0">
                      {d.charAt(0).toUpperCase()}
                    </span>
                    {d}
                  </li>
                ))}
              </ul>
            </SidebarSection>
          )}

          <SidebarSection titre="Date">
            <time className="text-sm text-[#656d76]">{adr.date}</time>
          </SidebarSection>
        </aside>
      </div>
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
