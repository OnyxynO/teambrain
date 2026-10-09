import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8003",
    trace: "on-first-retry",
  },
  // Serveur dédié sur un .decisions/ jetable (cf. e2e/serveur-e2e.sh). Pas de
  // réutilisation : un serveur déjà lancé sur 8003 pointe sur un vrai dépôt.
  webServer: {
    command: "bash e2e/serveur-e2e.sh",
    url: "http://localhost:8003/health",
    reuseExistingServer: false,
    timeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
