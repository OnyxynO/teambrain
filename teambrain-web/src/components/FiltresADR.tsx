"use client";

import { useRouter, useSearchParams } from "next/navigation";

interface Props {
  statuts: string[];
  modules: string[];
}

export function FiltresADR({ statuts, modules }: Props) {
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

  return (
    <div className="flex gap-3 flex-wrap">
      <select
        value={params.get("statut") ?? ""}
        onChange={(e) => onChange("statut", e.target.value)}
        className="text-sm border border-slate-200 rounded px-3 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="">Tous les statuts</option>
        {statuts.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <select
        value={params.get("module") ?? ""}
        onChange={(e) => onChange("module", e.target.value)}
        className="text-sm border border-slate-200 rounded px-3 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="">Tous les modules</option>
        {modules.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    </div>
  );
}
