#!/usr/bin/env node
/**
 * Screenshot all 5 MemWeaver dashboard tabs via Playwright.
 *
 * Requires: `playwright` npm package + Chromium browser binary.
 *
 *   npm install playwright && npx playwright install chromium
 *
 * Usage:
 *
 *   node scripts/screenshot-tabs.mjs
 *   node scripts/screenshot-tabs.mjs --url http://localhost:3000 --out ../assets
 *
 * Defaults: url=http://localhost:3000, out=assets/
 */

import { chromium } from "playwright";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";
import { existsSync, mkdirSync } from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Config ──────────────────────────────────────────────────────────────────
const TABS = [
  { id: "compare", label: "Compare", name: "Compare" },
  { id: "qa",      label: "QA Chat",  name: "QA Chat" },
  { id: "rag",     label: "RAG",      name: "RAG" },
  { id: "wiki",    label: "LLM-Wiki", name: "LLM-Wiki" },
  { id: "inventory", label: "Inventory", name: "Inventory" },
];

function parseArgs() {
  const args = process.argv.slice(2);
  let url = "http://localhost:3000";
  let outDir = resolve(__dirname, "..", "assets");
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--url" && args[i + 1]) url = args[++i];
    if (args[i] === "--out" && args[i + 1]) outDir = resolve(__dirname, args[++i]);
  }
  return { url, outDir };
}

// ── Main ────────────────────────────────────────────────────────────────────
async function main() {
  const { url, outDir } = parseArgs();

  if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  try {
    console.log(`Navigating to ${url} …`);
    await page.goto(url, { waitUntil: "networkidle" });
    // Small extra wait for any client-side render to settle
    await page.waitForTimeout(1000);

    for (const tab of TABS) {
      if (tab.id !== "compare") {
        // Click the nav button by its accessible name (matches aria-label / inner text)
        const btn = page.getByRole("button", { name: tab.name });
        await btn.click();
        await page.waitForTimeout(800);
      }

      const filename = resolve(outDir, `memweaver-${tab.id}.png`);
      await page.screenshot({ path: filename, fullPage: true });
      console.log(`  ✓ ${tab.label.padEnd(12)} → ${filename}`);
    }

    console.log("\nAll screenshots saved to", outDir);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("Failed:", err.message);
  process.exit(1);
});
