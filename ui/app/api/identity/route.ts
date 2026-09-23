/**
 * Selecting a simulated identity. The only writer of the identity cookie.
 *
 * The role is validated against `grants.json` here, so an arbitrary string
 * never becomes a cookie. That matters less than it looks — the agent rejects
 * an unknown role anyway (C1) — but a 400 from this route is legible, and a
 * rejected run three seconds later is not.
 */
import { NextResponse } from "next/server";

import { GRANTS, isRole } from "@/lib/grants";
import { COOKIE, COOKIE_OPTIONS } from "@/lib/identity";

export async function POST(req: Request) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "expected a JSON body" }, { status: 400 });
  }

  const role = (body as Record<string, unknown> | null)?.role;
  if (!isRole(role)) {
    return NextResponse.json(
      { error: `unknown role ${JSON.stringify(role)}; expected one of ${Object.keys(GRANTS).join(", ")}` },
      { status: 400 },
    );
  }

  const res = NextResponse.json({ role, label: GRANTS[role].label });
  res.cookies.set(
    COOKIE,
    JSON.stringify({ role, displayName: GRANTS[role].label }),
    COOKIE_OPTIONS,
  );
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({ role: null });
  res.cookies.set(COOKIE, "", { ...COOKIE_OPTIONS, maxAge: 0 });
  return res;
}
