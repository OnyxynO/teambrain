"use client";

import Link from "next/link";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams, usePathname } from "next/navigation";
import { listerProjets, type ProjetInfo } from "@/lib/api";

/* ── Icônes SVG (Octicons) ── */

function IconDossier() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M1.75 1A1.75 1.75 0 0 0 0 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0 0 16 13.25v-8.5A1.75 1.75 0 0 0 14.25 3H7.5a.25.25 0 0 1-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1Z" />
    </svg>
  );
}

function IconRepo() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z" />
    </svg>
  );
}

function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.499 4.499 0 1 0-8.997 0A4.499 4.499 0 0 0 11.5 7Z" />
    </svg>
  );
}

/* ── Item sidebar ── */

function SidebarItem({
  href,
  active,
  icon,
  label,
  count,
}: {
  href: string;
  active: boolean;
  icon: React.ReactNode;
  label: string;
  count?: number;
}) {
  return (
    <Link
      href={href}
      className={[
        "group flex items-center justify-between px-2 py-1.5 rounded-md text-sm transition-colors",
        active
          ? "bg-[#ddf4ff] text-[#0969da] font-semibold"
          : "text-[#1f2328] hover:bg-[#f6f8fa]",
      ].join(" ")}
    >
      <span className="flex items-center gap-2 min-w-0">
        <span
          className={[
            "shrink-0 transition-colors",
            active ? "text-[#0969da]" : "text-[#656d76] group-hover:text-[#1f2328]",
          ].join(" ")}
        >
          {icon}
        </span>
        <span className="truncate">{label}</span>
      </span>
      {count !== undefined && (
        <span className="text-xs tabular-nums shrink-0 ml-1 text-[#6e7781]">
          {count}
        </span>
      )}
    </Link>
  );
}

/* ── Contenu de la sidebar (client, lit les params URL) ── */

function SidebarContent() {
  const params = useSearchParams();
  const pathname = usePathname();
  const projetActif = params.get("projet") ?? "";

  const [projets, setProjets] = useState<ProjetInfo[]>([]);

  useEffect(() => {
    listerProjets().then(setProjets).catch(() => {});
  }, []);

  const total = projets.reduce((s, p) => s + p.nb_adrs, 0);
  const estListePage = pathname === "/";

  /* Lien projet : conserve les autres params URL */
  function lienProjet(id: string) {
    if (!id) return "/";
    return `/?projet=${encodeURIComponent(id)}`;
  }

  return (
    <nav className="py-3 px-3 flex flex-col gap-1">

      {/* ── Section Projets ── */}
      <p className="px-2 pt-1 pb-1 text-xs font-semibold text-[#656d76] uppercase tracking-wider select-none">
        Projets
      </p>

      <SidebarItem
        href="/"
        active={!projetActif && estListePage}
        icon={<IconDossier />}
        label="Tous les projets"
        count={total}
      />

      {projets.map((p) => (
        <SidebarItem
          key={p.id}
          href={lienProjet(p.id)}
          active={projetActif === p.id && estListePage}
          icon={<IconRepo />}
          label={p.nom}
          count={p.nb_adrs}
        />
      ))}

      {/* ── Séparateur ── */}
      <hr className="my-2 border-[#d0d7de]" />

      {/* ── Liens fixes ── */}
      <SidebarItem
        href="/search/"
        active={pathname.startsWith("/search")}
        icon={<IconSearch />}
        label="Recherche sémantique"
      />

    </nav>
  );
}

/* ── Sidebar — export ── */

export function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-[#d0d7de] bg-white sticky top-14 h-[calc(100vh-56px)] overflow-y-auto">
      <Suspense fallback={<div className="p-4 text-sm text-[#656d76]">…</div>}>
        <SidebarContent />
      </Suspense>
    </aside>
  );
}
