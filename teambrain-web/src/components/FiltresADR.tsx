"use client";

import { useRouter, useSearchParams } from "next/navigation";

interface Props {
  statuts: string[];
  modules: string[];
  projets: string[];
}

const LABELS_STATUT: Record<string, string> = {
  propose:  "Proposé",
  accepte:  "Accepté",
  deprecie: "Déprécié",
  remplace: "Remplacé",
};

const selectCls =
  "text-sm border border-[#d0d7de] rounded-md px-3 py-1.5 bg-white text-[#1f2328] " +
  "focus:outline-none focus:ring-2 focus:ring-[#0969da] focus:border-[#0969da] " +
  "hover:border-[#57606a] transition-colors cursor-pointer";

export function FiltresADR({ statuts, modules, projets }: Props) {
  const router = useRouter();
  const params = useSearchParams();

  function onChange(key: string, value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    router.push(`/?${next}`);
  }

  const actif = params.get("projet") || params.get("statut") || params.get("module");

  return (
    <div className="flex gap-2 flex-wrap items-center">
      {projets.length > 1 && (
        <select
          value={params.get("projet") ?? ""}
          onChange={(e) => onChange("projet", e.target.value)}
          className={selectCls}
        >
          <option value="">Tous les projets</option>
          {projets.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      )}

      <select
        value={params.get("statut") ?? ""}
        onChange={(e) => onChange("statut", e.target.value)}
        className={selectCls}
      >
        <option value="">Tous les statuts</option>
        {statuts.map((s) => (
          <option key={s} value={s}>{LABELS_STATUT[s] ?? s}</option>
        ))}
      </select>

      <select
        value={params.get("module") ?? ""}
        onChange={(e) => onChange("module", e.target.value)}
        className={selectCls}
      >
        <option value="">Tous les modules</option>
        {modules.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>

      {actif && (
        <button
          onClick={() => router.push("/")}
          className="text-xs text-[#0969da] hover:underline px-1"
        >
          Effacer les filtres ×
        </button>
      )}
    </div>
  );
}
