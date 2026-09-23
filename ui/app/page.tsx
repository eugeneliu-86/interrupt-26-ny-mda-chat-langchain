/**
 * The page. A SERVER component on purpose (ph. 06 §1, §5).
 *
 * It reads the identity cookie server-side, so the grants panel is rendered
 * from the same value the proxy will send to the deployment. If the panel
 * were rendered from client state, the screen and the run could disagree —
 * and a screen that describes one identity while the trace shows another is
 * worse than no screen at all, because the audience checks the trace.
 *
 * It also hands the client the LangSmith PROJECT URL. That is not a secret
 * (the key is), and passing it as a prop rather than a `NEXT_PUBLIC_` var
 * keeps the browser from holding environment it has no other use for.
 */
import { Compare } from "@/components/Compare";
import { Console } from "@/components/Console";
import { GrantsPanel } from "@/components/GrantsPanel";
import { IdentityPicker } from "@/components/IdentityPicker";
import { ModeSwitch } from "@/components/ModeSwitch";
import { DEMO_VERSION, ROLES, type Role } from "@/lib/grants";
import { readIdentity } from "@/lib/identity";

export const dynamic = "force-dynamic";

/** The demo script, chosen by measurement in ph. 05 §4 — not by taste. */
const SUGGESTIONS = [
  "Do we require retry middleware on model calls?", // beat 1, primary
  "What environments do we have?", // beat 1, spare
  "What is our on-call escalation path?", // beat 2
];

const DEFAULT_ROLE: Role = ROLES[0];

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const identity = await readIdentity();
  const role = identity?.role ?? DEFAULT_ROLE;
  const compareEnabled = process.env.DEMO_COMPARE_MODE === "true";
  const wantCompare = (await searchParams).mode === "compare" && compareEnabled;

  const traceBase = (process.env.LANGSMITH_PROJECT_URL ?? "").replace(/\/$/, "");
  const configured = Boolean(process.env.MDA_API_URL && process.env.LANGSMITH_API_KEY);

  return (
    <>
      {/* C5. Sticky, and never conditional — including in compare mode,
          where everything else in the chrome goes away. */}
      <div className="banner">
        <span aria-hidden>⚠</span>
        <span className="bannertext">
          Simulated identity — nobody is authenticated. The role is chosen from
          a menu and injected server-side.
        </span>
        {compareEnabled && <ModeSwitch compare={wantCompare} />}
      </div>

      {!configured && (
        <div className="banner" style={{ background: "#3a1416", borderColor: "#7f2a2a", color: "#fecaca" }}>
          <span aria-hidden>✗</span>
          <span>
            <strong>Not configured.</strong> Set <code>MDA_API_URL</code> and{" "}
            <code>LANGSMITH_API_KEY</code> in <code>.env.local</code> — see{" "}
            <code>ui/.env.example</code>. Questions will fail until you do.
          </span>
        </div>
      )}

      {/* COMPARE MODE DROPS THE LEFT RAIL ENTIRELY. Both identities are
          running, so a single identity's grants panel would be describing
          one of the two panes and the picker would be choosing something
          nothing reads. Each pane carries its own heading and its own ✗
          count instead, and the two get the full width — which is what they
          need at projection size. */}
      <main className={wantCompare ? "layout wide" : "layout"}>
        {!wantCompare && (
          <aside>
            <IdentityPicker current={role} />
            <GrantsPanel role={role} />
            <div className="panel">
              <h2>Deployment</h2>
              <p className="note">
                One agent, <code>role-aware-docs-assistant</code>, build{" "}
                <strong>{DEMO_VERSION}</strong>. Both identities call the same
                model; only the tool surface differs.
              </p>
            </div>
          </aside>
        )}

        <div>
          {wantCompare ? (
            <Compare roles={ROLES} traceBase={traceBase} suggestions={SUGGESTIONS} />
          ) : (
            <Console role={role} traceBase={traceBase} suggestions={SUGGESTIONS} />
          )}
        </div>
      </main>
    </>
  );
}
