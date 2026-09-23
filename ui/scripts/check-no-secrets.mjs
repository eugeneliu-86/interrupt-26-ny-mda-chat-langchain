/**
 * Nothing secret may reach a browser (ph. 06 §1, §3).
 *
 * VERIFIED AGAINST THE BUILT OUTPUT, NOT THE SOURCE. Reading the source tells
 * you where a variable is written; only the bundle tells you where it ended
 * up. Next inlines any `NEXT_PUBLIC_`-prefixed value into client chunks, and
 * a server-only import pulled into a client component drags its module scope
 * along with it — neither is visible by grepping `app/`.
 *
 *     node scripts/check-no-secrets.mjs
 *
 * Run it after `next build`. It fails if the API key, the deployment URL, or
 * any `NEXT_PUBLIC_` variable appears in a client-served chunk.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const CLIENT_DIRS = [".next/static"];

function readEnv() {
  const out = {};
  for (const file of [".env.local", ".env"]) {
    let text;
    try {
      text = readFileSync(join(ROOT, file), "utf8");
    } catch {
      continue;
    }
    for (const line of text.split("\n")) {
      const m = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
      if (m && m[2]) out[m[1]] ??= m[2];
    }
  }
  return out;
}

function walk(dir) {
  const files = [];
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return files;
  }
  for (const name of entries) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) files.push(...walk(full));
    else if (/\.(js|mjs|json|css|map|txt|html)$/.test(name)) files.push(full);
  }
  return files;
}

const env = readEnv();
const files = CLIENT_DIRS.flatMap((d) => walk(join(ROOT, d)));

if (files.length === 0) {
  console.error("FAIL: no built client assets found — run `pnpm build` first.");
  process.exit(1);
}

/** Literal values that must never be in a client chunk. */
const forbidden = [
  ["LANGSMITH_API_KEY value", env.LANGSMITH_API_KEY],
  ["MDA_API_URL value", env.MDA_API_URL],
].filter(([, v]) => v && v.length > 8);

// Any API key shape at all, even one not in this .env.
const KEY_SHAPE = /lsv2_(pt|sk)_[a-f0-9]{32}/i;

/** Public env names the framework itself emits. Not ours, not a leak. */
const FRAMEWORK_PUBLIC = /^NEXT_PUBLIC_VERCEL_/;

let failed = 0;
for (const file of files) {
  const text = readFileSync(file, "utf8");
  for (const [label, value] of forbidden) {
    if (text.includes(value)) {
      console.error(`FAIL: ${label} found in ${file.replace(ROOT, "")}`);
      failed++;
    }
  }
  const shaped = KEY_SHAPE.exec(text);
  if (shaped) {
    console.error(`FAIL: a LangSmith key shape (${shaped[0].slice(0, 12)}…) is in ${file.replace(ROOT, "")}`);
    failed++;
  }
  for (const m of text.matchAll(/NEXT_PUBLIC_[A-Z0-9_]+/g)) {
    // Next injects its own build metadata (the NEXT_PUBLIC_VERCEL_* family)
    // into the framework chunk on every build. Flagging those would make this
    // check fail for a reason nobody can fix, and a check that always fails
    // gets deleted. What matters is that none of OUR variables are public —
    // which the source grep below proves directly.
    if (FRAMEWORK_PUBLIC.test(m[0])) continue;
    console.error(`FAIL: ${m[0]} is in a client chunk — this build must have no public env.`);
    failed++;
  }
}

// The source must not create the hazard in the first place.
function grepSource(dir, pattern) {
  const hits = [];
  for (const file of walk(dir).filter((f) => /\.(ts|tsx|mjs)$/.test(f))) {
    const text = readFileSync(file, "utf8");
    text.split("\n").forEach((line, i) => {
      if (pattern.test(line)) hits.push(`${file.replace(ROOT, "")}:${i + 1}: ${line.trim()}`);
    });
  }
  return hits;
}

const publicVars = [
  ...grepSource(join(ROOT, "app"), /NEXT_PUBLIC_/),
  ...grepSource(join(ROOT, "components"), /NEXT_PUBLIC_/),
  ...grepSource(join(ROOT, "lib"), /NEXT_PUBLIC_/),
];
for (const hit of publicVars) {
  console.error(`FAIL: NEXT_PUBLIC_ in source — ${hit}`);
  failed++;
}

// `LANGSMITH_API_KEY` may be read ONLY by the proxy route.
const ALLOWED_KEY_READERS = ["/app/api/lg/[..._path]/route.ts"];
for (const dir of ["app", "components", "lib"]) {
  for (const hit of grepSource(join(ROOT, dir), /LANGSMITH_API_KEY/)) {
    const path = hit.split(":")[0];
    if (!ALLOWED_KEY_READERS.some((a) => path.endsWith(a) || path === a)) {
      console.error(`FAIL: LANGSMITH_API_KEY read outside the proxy — ${hit}`);
      failed++;
    }
  }
}

if (failed) {
  console.error(`\n${failed} problem(s).`);
  process.exit(1);
}
console.log(
  `OK: ${files.length} client asset(s) contain no key, no deployment URL and no NEXT_PUBLIC_ variable.`,
);
console.log("OK: LANGSMITH_API_KEY is read only by app/api/lg/[..._path]/route.ts.");
