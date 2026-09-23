"use client";

/**
 * Choosing a simulated identity (ph. 06 §3, C5).
 *
 * The click posts to `/api/identity`, which is the ONLY writer of the
 * identity cookie. The browser never holds the role: it asks the server to
 * change it and then re-reads what the server decided.
 *
 * SWITCHING CLEARS THE THREAD, visibly. A thread carries the previous role's
 * answers in its history; continuing it after a switch would feed the new
 * identity documents the old one fetched, and the demo would appear to leak
 * exactly the thing it claims to prevent.
 */
import { useState, useTransition } from "react";

import { GRANTS, ROLES, type Role } from "@/lib/grants";

export function IdentityPicker({ current }: { current: Role }) {
  const [pending, start] = useTransition();
  const [busy, setBusy] = useState<Role | null>(null);

  async function choose(role: Role) {
    if (role === current || pending) return;
    setBusy(role);
    const res = await fetch("/api/identity", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ role }),
    });
    setBusy(null);
    if (!res.ok) return;
    // Re-render the server component so the grants panel and the proxy agree
    // on who is asking. Reloading is heavy-handed but it makes it impossible
    // for the panel to describe one identity while the cookie names another.
    start(() => window.location.reload());
  }

  return (
    <div className="panel">
      <h2>Identity</h2>
      <div className="identity">
        {ROLES.map((role) => (
          <button
            key={role}
            type="button"
            aria-pressed={role === current}
            disabled={pending || busy !== null}
            onClick={() => choose(role)}
          >
            <span className="dot" aria-hidden />
            <span>{GRANTS[role].label}</span>
          </button>
        ))}
      </div>
      <p className="note">
        Switching identity starts a <strong>new thread</strong>. The previous
        identity&rsquo;s answers are not carried over.
      </p>
    </div>
  );
}
