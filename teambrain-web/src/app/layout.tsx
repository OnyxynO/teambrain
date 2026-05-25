import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "TeamBrain",
  description: "Mémoire décisionnelle d'équipe",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="bg-[#f6f8fa] text-[#1f2328]">
        {/* Header global fixe */}
        <Nav />

        {/* Corps : sidebar gauche + contenu principal */}
        <div className="flex min-h-[calc(100vh-56px)]">
          <Suspense fallback={<div className="w-60 shrink-0 border-r border-[#d0d7de] bg-white" />}>
            <Sidebar />
          </Suspense>

          <main className="flex-1 min-w-0 px-8 py-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
