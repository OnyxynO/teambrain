/* Badges GitHub Issues-style */

interface Config {
  bg:    string;
  fg:    string;
  label: string;
  icon:  "dot" | "check" | "slash" | "arrow";
}

const CONFIGS: Record<string, Config> = {
  propose:  { bg: "#dafbe1", fg: "#1a7f37", label: "Proposé",   icon: "dot"   },
  accepte:  { bg: "#fbefff", fg: "#8250df", label: "Accepté",   icon: "check" },
  deprecie: { bg: "#ffebe9", fg: "#d1242f", label: "Déprécié",  icon: "slash" },
  remplace: { bg: "#eaeef2", fg: "#6e7781", label: "Remplacé",  icon: "arrow" },
};

function StatusIconSvg({ icon, color }: { icon: Config["icon"]; color: string }) {
  switch (icon) {
    case "dot":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill={color} aria-hidden="true">
          <path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
          <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z" />
        </svg>
      );
    case "check":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill={color} aria-hidden="true">
          <path d="M8 16A8 8 0 1 1 8 0a8 8 0 0 1 0 16Zm3.78-9.72a.75.75 0 0 0-1.06-1.06L6.75 9.19 5.28 7.72a.75.75 0 0 0-1.06 1.06l2 2a.75.75 0 0 0 1.06 0l4.5-4.5Z" />
        </svg>
      );
    case "slash":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill={color} aria-hidden="true">
          <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm9.78-2.22a.749.749 0 0 0-1.06-1.06L4.72 10.22a.749.749 0 1 0 1.06 1.06l5.5-5.5Z" />
        </svg>
      );
    case "arrow":
      return (
        <svg width="14" height="14" viewBox="0 0 16 16" fill={color} aria-hidden="true">
          <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm9.78-1.22a.75.75 0 0 1 0 1.06l-2.5 2.5a.75.75 0 0 1-1.06-1.06l1.22-1.22H5.75a.75.75 0 0 1 0-1.5h3.19L7.72 6.34a.75.75 0 0 1 1.06-1.06l2.5 2.5Z" />
        </svg>
      );
  }
}

export function StatutBadge({ statut }: { statut: string }) {
  const cfg = CONFIGS[statut] ?? { bg: "#eaeef2", fg: "#6e7781", label: statut, icon: "dot" as const };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
      style={{ backgroundColor: cfg.bg, color: cfg.fg }}
    >
      <StatusIconSvg icon={cfg.icon} color={cfg.fg} />
      {cfg.label}
    </span>
  );
}

/* Icône seule (grande) pour les listes */
export function StatutIcone({ statut, size = 16 }: { statut: string; size?: number }) {
  const cfg = CONFIGS[statut] ?? { bg: "#eaeef2", fg: "#6e7781", label: statut, icon: "dot" as const };
  return (
    <span className="shrink-0 mt-0.5" title={cfg.label}>
      <svg width={size} height={size} viewBox="0 0 16 16" fill={cfg.fg} aria-label={cfg.label}>
        {cfg.icon === "dot" && (
          <>
            <path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
            <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z" />
          </>
        )}
        {cfg.icon === "check" && (
          <path d="M8 16A8 8 0 1 1 8 0a8 8 0 0 1 0 16Zm3.78-9.72a.75.75 0 0 0-1.06-1.06L6.75 9.19 5.28 7.72a.75.75 0 0 0-1.06 1.06l2 2a.75.75 0 0 0 1.06 0l4.5-4.5Z" />
        )}
        {cfg.icon === "slash" && (
          <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm9.78-2.22a.749.749 0 0 0-1.06-1.06L4.72 10.22a.749.749 0 1 0 1.06 1.06l5.5-5.5Z" />
        )}
        {cfg.icon === "arrow" && (
          <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm9.78-1.22a.75.75 0 0 1 0 1.06l-2.5 2.5a.75.75 0 0 1-1.06-1.06l1.22-1.22H5.75a.75.75 0 0 1 0-1.5h3.19L7.72 6.34a.75.75 0 0 1 1.06-1.06l2.5 2.5Z" />
        )}
      </svg>
    </span>
  );
}
