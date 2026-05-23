import { test, expect } from "@playwright/test";

test.describe("Navigation générale", () => {
  test("page liste charge et affiche des projets", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/TeamBrain/);
    // La liste doit contenir au moins un projet
    await expect(page.locator("main")).toBeVisible();
  });

  test("lien Nouvelle décision pointe vers /nouveau", async ({ page }) => {
    await page.goto("/");
    const lien = page.getByRole("link", { name: /nouvelle/i });
    await expect(lien).toBeVisible();
    await expect(lien).toHaveAttribute("href", /\/nouveau/);
  });

  test("page recherche est accessible", async ({ page }) => {
    await page.goto("/search");
    await expect(page.getByRole("textbox")).toBeVisible();
  });

  test("page nouveau est accessible", async ({ page }) => {
    await page.goto("/nouveau");
    await expect(page.locator("h1")).toContainText(/décision/i);
  });

  test("ADR inexistant affiche un message d'erreur", async ({ page }) => {
    await page.goto("/adr/?projet=teambrain&id=99999");
    await expect(page.getByText(/introuvable/i)).toBeVisible();
  });
});
