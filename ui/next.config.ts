import path from "node:path";
import type { NextConfig } from "next";

const config: NextConfig = {
  // `lib/grants.ts` imports ../agent/contracts/grants.json, which is OUTSIDE
  // this directory. That is deliberate (ph. 06 §4): `contracts/grants.py` is
  // the single source of truth for what each role may reach, and a copy in
  // `ui/` would be a second opinion that can disagree with the agent.
  //
  // Next traces files from the package root by default, so the import
  // resolves in dev but the JSON is missing from a standalone build. Rooting
  // the trace at the repo makes it ship.
  outputFileTracingRoot: path.join(import.meta.dirname, ".."),
};

export default config;
