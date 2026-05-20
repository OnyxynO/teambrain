const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8003";

export interface ADR {
  id: number;
  titre: string;
  date: string;
  statut: string;
  modules: string[];
  decideurs: string[];
  contexte: string;
  decision: string;
  consequences: string;
}

export interface ResultatRecherche {
  adr: ADR;
  score: number;
}

export interface ReponseRecherche {
  resultats: ResultatRecherche[];
  index_disponible: boolean | null;
}

export interface Referentiels {
  modules: string[];
  statuts: string[];
}

export interface BrouillonReponse {
  titre: string;
  contexte: string;
  decision: string;
  consequences: string;
  modules: string[];
  decideurs: string[];
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    ...options,
    next: { revalidate: 0 },
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(detail.detail ?? `Erreur ${r.status}`);
  }
  return r.json();
}

export function listerADR(params?: { statut?: string; module?: string }): Promise<ADR[]> {
  const qs = new URLSearchParams();
  if (params?.statut) qs.set("statut", params.statut);
  if (params?.module) qs.set("module", params.module);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch(`/adr${query}`);
}

export function getADR(id: number): Promise<ADR> {
  return apiFetch(`/adr/${id}`);
}

export function rechercherADR(q: string, semantic = false, k = 10): Promise<ReponseRecherche> {
  const qs = new URLSearchParams({ q, k: String(k) });
  if (semantic) qs.set("semantic", "true");
  return apiFetch(`/adr/search?${qs}`);
}

export function getReferentiels(): Promise<Referentiels> {
  return apiFetch("/referentiels");
}

export function genererBrouillon(description: string): Promise<BrouillonReponse> {
  return apiFetch("/adr/draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description }),
  });
}

export function creerADR(payload: Omit<ADR, "id" | "date">): Promise<ADR> {
  return apiFetch("/adr", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
