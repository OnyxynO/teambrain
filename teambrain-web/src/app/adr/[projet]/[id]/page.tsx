import Link from "next/link";
import { notFound } from "next/navigation";
import { getADR } from "@/lib/api";
import { StatutBadge } from "@/components/StatutBadge";

interface PageProps {
  params: Promise<{ projet: string; id: string }>;
}

export default async function PageDetailADR({ params }: PageProps) {
  const { projet, id } = await params;
  const adrId = parseInt(id, 10);

  if (isNaN(adrId)) notFound();

  let adr;
  try {
    adr = await getADR(projet, adrId);
  } catch {
    notFound();
  }

  return (
    <div className="max-w-3xl space-y-8">
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

      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm text-slate-400">
            #{String(adr.id).padStart(3, "0")}
          </span>
          <StatutBadge statut={adr.statut} />
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
