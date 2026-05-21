import Link from "next/link";

export function Nav() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-6">
        <span className="font-semibold text-slate-900 tracking-tight">TeamBrain</span>
        <nav className="flex gap-4 text-sm text-slate-600">
          <Link href="/" className="hover:text-slate-900 transition-colors">
            ADR
          </Link>
          <Link href="/search/" className="hover:text-slate-900 transition-colors">
            Recherche
          </Link>
          <Link href="/nouveau/" className="hover:text-slate-900 transition-colors">
            Nouveau
          </Link>
        </nav>
      </div>
    </header>
  );
}
