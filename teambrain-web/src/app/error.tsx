"use client";

export default function Erreur({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center space-y-3">
      <p className="text-red-700 font-medium">Erreur de connexion à l&apos;API</p>
      <p className="text-red-600 text-sm">{error.message}</p>
      <p className="text-slate-500 text-sm">
        Vérifie que <code className="font-mono">teambrain serve --http</code> tourne sur le port 8003.
      </p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors"
      >
        Réessayer
      </button>
    </div>
  );
}
