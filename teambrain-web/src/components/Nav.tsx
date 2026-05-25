"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function BrainIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3C7.03 3 3 7.03 3 12c0 2.25.79 4.31 2.1 5.93L3 21l3.07-2.1C7.69 20.21 9.75 21 12 21c4.97 0 9-4.03 9-9s-4.03-9-9-9z"
        fill="currentColor"
        opacity=".25"
      />
      <path
        d="M9 10a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm6 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-6 4c0 1.66 1.34 3 3 3s3-1.34 3-3"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

const NAV_LINKS = [
  { href: "/",         label: "ADR" },
  { href: "/search/",  label: "Recherche" },
  { href: "/nouveau/", label: "Nouveau" },
] as const;

export function Nav() {
  const pathname = usePathname();

  function actif(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href.replace(/\/$/, ""));
  }

  return (
    <header className="bg-[#24292f] border-b border-black/20">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 text-white shrink-0">
          <BrainIcon />
          <span className="font-semibold text-sm tracking-tight">TeamBrain</span>
        </Link>

        {/* Séparateur */}
        <span className="text-white/20 text-lg font-thin select-none">/</span>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={[
                "px-3 py-1.5 rounded-md text-sm transition-colors",
                actif(href)
                  ? "bg-white/15 text-white font-medium"
                  : "text-[#cdd9e5] hover:text-white hover:bg-white/10",
              ].join(" ")}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
