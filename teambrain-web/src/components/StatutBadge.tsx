const COULEURS: Record<string, string> = {
  accepte: "bg-green-100 text-green-800",
  propose: "bg-yellow-100 text-yellow-800",
  deprecie: "bg-red-100 text-red-600",
  remplace: "bg-slate-100 text-slate-500",
};

export function StatutBadge({ statut }: { statut: string }) {
  const cls = COULEURS[statut] ?? "bg-slate-100 text-slate-500";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {statut}
    </span>
  );
}
