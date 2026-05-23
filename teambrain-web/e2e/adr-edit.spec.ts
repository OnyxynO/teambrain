import { test, expect, APIRequestContext } from "@playwright/test";

const PROJET = "teambrain";
const BASE = "http://localhost:8003";

async function creerADRTest(request: APIRequestContext, titre: string) {
  const r = await request.post(`${BASE}/adr/${PROJET}`, {
    data: { titre, statut: "propose", contexte: "Contexte test.", decision: "Décision test.", consequences: "" },
  });
  expect(r.ok()).toBeTruthy();
  return (await r.json()) as { id: number; titre: string };
}

async function supprimerADR(request: APIRequestContext, id: number) {
  await request.delete(`${BASE}/adr/${PROJET}/${id}`);
}

// ── Mode lecture ──────────────────────────────────────────────────────────────

test.describe("Page détail — vue lecture", () => {
  let adrId: number;

  test.beforeAll(async ({ request }) => {
    const adr = await creerADRTest(request, "ADR vue lecture — test UI");
    adrId = adr.id;
  });

  test.afterAll(async ({ request }) => {
    await supprimerADR(request, adrId);
  });

  test("affiche le titre et les boutons Éditer / Supprimer", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await expect(page.getByRole("heading", { name: /ADR vue lecture/i })).toBeVisible();
    await expect(page.getByRole("button", { name: "Éditer" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Supprimer" })).toBeVisible();
  });

  test("affiche le badge statut", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await expect(page.getByText("propose")).toBeVisible();
  });

  test("le lien projet filtre la liste", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await page.getByRole("link", { name: PROJET }).click();
    await expect(page).toHaveURL(new RegExp(`projet=${PROJET}`));
  });
});

// ── Mode édition ──────────────────────────────────────────────────────────────

test.describe("Édition ADR", () => {
  let adrId: number;

  test.beforeAll(async ({ request }) => {
    const adr = await creerADRTest(request, "ADR édition — test UI");
    adrId = adr.id;
  });

  test.afterAll(async ({ request }) => {
    await supprimerADR(request, adrId);
  });

  test("cliquer Éditer affiche le formulaire", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await page.getByRole("button", { name: "Éditer" }).click();
    await expect(page.getByLabel("Titre")).toBeVisible();
    await expect(page.getByLabel("Statut")).toBeVisible();
    await expect(page.getByLabel("Date")).toBeVisible();
    await expect(page.getByLabel("Modules")).toBeVisible();
    await expect(page.getByLabel("Décideurs")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sauvegarder" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Annuler" })).toBeVisible();
  });

  test("le formulaire est pré-rempli avec les valeurs courantes", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await page.getByRole("button", { name: "Éditer" }).click();
    await expect(page.getByLabel("Titre")).toHaveValue("ADR édition — test UI");
    await expect(page.getByLabel("Statut")).toHaveValue("propose");
  });

  test("Annuler restaure la vue lecture", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await page.getByRole("button", { name: "Éditer" }).click();
    await page.getByRole("button", { name: "Annuler" }).click();
    await expect(page.getByRole("button", { name: "Éditer" })).toBeVisible();
    await expect(page.getByLabel("Titre")).not.toBeVisible();
  });

  test("modifier le titre et sauvegarder", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await page.getByRole("button", { name: "Éditer" }).click();

    await page.getByLabel("Titre").clear();
    await page.getByLabel("Titre").fill("Titre modifié par Playwright");

    await page.getByRole("button", { name: "Sauvegarder" }).click();

    await expect(page.getByRole("heading", { name: "Titre modifié par Playwright" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Éditer" })).toBeVisible();
  });

  test("changer le statut via le select", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await page.getByRole("button", { name: "Éditer" }).click();
    await page.getByLabel("Statut").selectOption("accepte");
    await page.getByRole("button", { name: "Sauvegarder" }).click();
    await expect(page.getByText("accepte")).toBeVisible();
  });

  test("modifier les champs texte longs", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await page.getByRole("button", { name: "Éditer" }).click();

    await page.locator("#edit-contexte").fill("Nouveau contexte écrit par le test Playwright.");
    await page.locator("#edit-decision").fill("Nouvelle décision.");

    await page.getByRole("button", { name: "Sauvegarder" }).click();

    await expect(page.getByText("Nouveau contexte écrit par le test Playwright.")).toBeVisible();
  });

  test("Sauvegarder désactivé si titre vide", async ({ page }) => {
    await page.goto(`/adr/?projet=${PROJET}&id=${adrId}`);
    await page.getByRole("button", { name: "Éditer" }).click();
    await page.getByLabel("Titre").clear();
    await expect(page.getByRole("button", { name: "Sauvegarder" })).toBeDisabled();
  });
});

// ── Suppression ───────────────────────────────────────────────────────────────

test.describe("Suppression ADR", () => {
  test("cliquer Supprimer affiche la confirmation", async ({ page, request }) => {
    const adr = await creerADRTest(request, "ADR confirmation suppression");
    await page.goto(`/adr/?projet=${PROJET}&id=${adr.id}`);
    await page.getByRole("button", { name: "Supprimer" }).click();
    await expect(page.getByText("Confirmer ?")).toBeVisible();
    await expect(page.getByRole("button", { name: "Oui, supprimer" })).toBeVisible();
    // Cleanup si le test échoue avant la suppression UI
    await supprimerADR(request, adr.id);
  });

  test("Annuler dans la confirmation garde l'ADR", async ({ page, request }) => {
    const adr = await creerADRTest(request, "ADR annulation confirmation");
    await page.goto(`/adr/?projet=${PROJET}&id=${adr.id}`);
    await page.getByRole("button", { name: "Supprimer" }).click();
    await page.getByRole("button", { name: "Annuler" }).last().click();
    await expect(page.getByRole("button", { name: "Supprimer" })).toBeVisible();
    await expect(page.getByText("Confirmer ?")).not.toBeVisible();
    await supprimerADR(request, adr.id);
  });

  test("confirmer la suppression redirige vers la liste", async ({ page, request }) => {
    const adr = await creerADRTest(request, "ADR à supprimer via UI");
    await page.goto(`/adr/?projet=${PROJET}&id=${adr.id}`);
    await page.getByRole("button", { name: "Supprimer" }).click();
    await page.getByRole("button", { name: "Oui, supprimer" }).click();
    await page.waitForURL("/");
    await expect(page).toHaveURL("/");
  });

  test("l'ADR supprimé n'apparaît plus dans la liste", async ({ page, request }) => {
    const adr = await creerADRTest(request, "ADR disparu après suppression");
    const titre = adr.titre;

    await page.goto(`/adr/?projet=${PROJET}&id=${adr.id}`);
    await page.getByRole("button", { name: "Supprimer" }).click();
    await page.getByRole("button", { name: "Oui, supprimer" }).click();
    await page.waitForURL("/");

    await expect(page.getByText(titre)).not.toBeVisible();
  });
});
