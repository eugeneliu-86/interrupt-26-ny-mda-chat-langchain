/**
 * The identity cookie — the ONLY place the role is decided (ph. 06 §1, C5).
 *
 * SIMULATED, NOT AUTHENTICATED. Nobody logs in. A person picks a name from a
 * dropdown and the server writes it into an httpOnly cookie. That is the
 * whole identity system, it is stated on screen, and the demo must never be
 * narrated as access control.
 *
 * What it *does* model honestly is provenance: the role is established
 * server-side and the browser cannot set it, so swapping this cookie for a
 * verified JWT claim changes nothing downstream. That sentence is only true
 * because of the `httpOnly` flag below and the overwrite in the proxy.
 */
import { cookies } from "next/headers";

import { isRole, type Role } from "./grants";

export const COOKIE = "demo-identity";

export interface Identity {
  role: Role;
  displayName: string;
}

/**
 * The selected identity, or null.
 *
 * Returns null rather than a default. A default would let a misrouted request
 * run as somebody — quietly, and as whichever role we happened to pick. C1's
 * whole design is that a run without an identity does not happen, and the
 * proxy depends on this returning null to refuse (§1).
 */
export async function readIdentity(): Promise<Identity | null> {
  const raw = (await cookies()).get(COOKIE)?.value;
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (typeof parsed !== "object" || parsed === null) return null;
    const { role, displayName } = parsed as Record<string, unknown>;
    // Re-validate on READ, not only on write. The cookie is httpOnly, so a
    // page cannot forge one — but a stale cookie from an older build can name
    // a role that no longer exists, and that must read as "no identity"
    // rather than as a role the agent will reject with a confusing error.
    if (!isRole(role)) return null;
    return { role, displayName: typeof displayName === "string" ? displayName : role };
  } catch {
    return null;
  }
}

export const COOKIE_OPTIONS = {
  httpOnly: true,   // the browser may not read it, so it may not forge it
  sameSite: "lax",  // no cross-site POST can flip your identity mid-demo
  secure: process.env.NODE_ENV === "production",
  path: "/",
  maxAge: 60 * 60 * 12,
} as const;
