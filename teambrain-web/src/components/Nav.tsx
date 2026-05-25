"use client";

import Link from "next/link";

function BrainIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" fill="white" opacity=".15" />
      <path
        d="M9 10a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm6 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-6 4c0 1.66 1.34 3 3 3s3-1.34 3-3"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M12 3C7.03 3 3 7.03 3 12c0 2.25.79 4.31 2.1 5.93L3 21l3.07-2.1C7.69 20.21 9.75 21 12 21"
        stroke="white"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Nav() {
  return (
    <header className="sticky top-0 z-50 bg-[#24292f] border-b border-black/30 h-14 flex items-center px-4 gap-4">
      {/* Logo + nom */}
      <Link href="/" className="flex items-center gap-2 text-white shrink-0 hover:opacity-80 transition-opacity">
        <BrainIcon />
        <span className="font-semibold text-sm tracking-tight">TeamBrain</span>
      </Link>

      {/* Espace */}
      <div className="flex-1" />

      {/* Bouton principal */}
      <Link
        href="/nouveau/"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-white bg-[#1f883d] border border-[#1a7f37] hover:bg-[#1a7f37] transition-colors"
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M7.75 2a.75.75 0 0 1 .75.75V7h4.25a.75.75 0 0 1 0 1.5H8.5v4.25a.75.75 0 0 1-1.5 0V8.5H2.75a.75.75 0 0 1 0-1.5H7V2.75A.75.75 0 0 1 7.75 2Z" />
        </svg>
        Nouvelle décision
      </Link>
    </header>
  );
}
