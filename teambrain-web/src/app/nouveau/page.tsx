import Link from "next/link";

export default function PageNouveau() {
  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <Link href="/" className="text-sm text-slate-500 hover:text-slate-700 transition-colors">
          ← Toutes les décisions
        </Link>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400">
        <p className="text-lg font-medium">Création guidée</p>
        <p className="text-sm mt-2">Module 6 — étape 4 (à venir)</p>
      </div>
    </div>
  );
}
