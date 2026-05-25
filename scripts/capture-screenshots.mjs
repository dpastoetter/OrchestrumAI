import { chromium } from "playwright";
import { mkdir } from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, "..", "docs", "screenshots");
const BASE = process.env.OMA_UI_BASE ?? "http://127.0.0.1:5173";
const API = process.env.OMA_API_BASE ?? "http://127.0.0.1:8000";

async function waitForApp(page) {
  await page.waitForSelector("nav", { timeout: 15000 });
  await page.waitForTimeout(800);
}

async function createWorkflowRequest() {
  const res = await fetch(`${API}/api/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: "README screenshot request",
      description: "Demonstrate approval flow and topology chips on the detail page.",
      priority: "normal",
      agent_type: "workflow",
      agent_topology: {
        type: "orchestrator",
        nodes: [
          { id: "n1", kind: "catalog", catalog_id: "research" },
          { id: "n2", kind: "catalog", catalog_id: "writer" },
        ],
        edges: [],
      },
    }),
  });
  if (!res.ok) throw new Error(`create request failed: ${res.status} ${await res.text()}`);
  const body = await res.json();
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 500));
    const d = await fetch(`${API}/api/requests/${body.id}`);
    const detail = await d.json();
    if (detail.current_step === "AWAITING_APPROVAL") return body.id;
  }
  return body.id;
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

await mkdir(OUT, { recursive: true });

await page.goto(`${BASE}/`);
await waitForApp(page);
await page.screenshot({ path: path.join(OUT, "requests.png"), fullPage: true });

await page.goto(`${BASE}/submit`);
await waitForApp(page);
const workflowBtn = page.getByRole("button", { name: /General workflow/i });
if (await workflowBtn.count()) {
  await workflowBtn.click();
  await page.waitForTimeout(600);
}
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 3));
await page.waitForTimeout(400);
await page.screenshot({ path: path.join(OUT, "submit.png"), fullPage: true });
await page.screenshot({ path: path.join(OUT, "submit-topology.png"), fullPage: true });

await page.goto(`${BASE}/settings`);
await waitForApp(page);
await page.screenshot({ path: path.join(OUT, "settings.png"), fullPage: true });

let requestId;
try {
  requestId = await createWorkflowRequest();
} catch (e) {
  console.warn("Could not create stub request:", e.message);
  const list = await fetch(`${API}/api/requests`);
  const items = await list.json();
  requestId = items[0]?.id;
}

if (requestId) {
  await page.goto(`${BASE}/requests/${requestId}`);
  await waitForApp(page);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(OUT, "request-detail.png"), fullPage: true });
}

await browser.close();
console.log("Screenshots written to", OUT);
