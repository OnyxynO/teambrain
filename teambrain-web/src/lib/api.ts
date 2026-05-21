const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8003";

export interface ADR {
  projet: string;
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

export interface ProjetInfo {
  id: string;
  nom: string;
  nb_adrs: number;
}

export interface ResultatRecherche {
  adr: ADR;
  score: number;
}

export interface ReponseRecherche {
  resultats: ResultatRecherche[];
  index_disponible: boolean | null;
}

export interface HealthReponse {
  status: string;
  ollama_disponible: boolean;
}

export interface Referentiels {
  modules: string[];
  statuts: string[];
  projets: string[];
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

export function listerProjets(): Promise<ProjetInfo[]> {
  return apiFetch("/projects");
}

export function listerADR(params?: {
  projet?: string;
  statut?: string;
  module?: string;
}): Promise<ADR[]> {
  const qs = new URLSearchParams();
  if (params?.projet) qs.set("projet", params.projet);
  if (params?.statut) qs.set("statut", params.statut);
  if (params?.module) qs.set("module", params.module);
  const query = qs.toString() ? `?${qs}` : "";
  return apiFetch(`/adr${query}`);
}

export function getADR(projet: string, id: number): Promise<ADR> {
  return apiFetch(`/adr/${projet}/${id}`);
}

export function rechercherADR(
  q: string,
  opts?: { projet?: string; semantic?: boolean; k?: number }
): Promise<ReponseRecherche> {
  const qs = new URLSearchParams({ q, k: String(opts?.k ?? 10) });
  if (opts?.projet) qs.set("projet", opts.projet);
  if (opts?.semantic) qs.set("semantic", "true");
  return apiFetch(`/adr/search?${qs}`);
}

export function getHealth(): Promise<HealthReponse> {
  return apiFetch("/health");
}

export function getReferentiels(projet?: string): Promise<Referentiels> {
  const qs = projet ? `?projet=${projet}` : "";
  return apiFetch(`/referentiels${qs}`);
}

export function genererBrouillon(
  description: string,
  projet?: string
): Promise<BrouillonReponse> {
  return apiFetch("/adr/draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, projet }),
  });
}

export function creerADR(
  projet: string,
  payload: Omit<ADR, "id" | "date" | "projet">
): Promise<ADR> {
  return apiFetch(`/adr/${projet}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
