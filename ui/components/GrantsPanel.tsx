/**
 * What this identity can and cannot reach (ph. 06 §4).
 *
 * The ordered list shows PREFERENCE (a prompt). The ✗ row shows ENFORCEMENT
 * (a missing tool). They must not look alike, because only one of them is
 * guaranteed — presenting them identically is the one thing on screen that
 * would make the UI lie about the mechanism.
 *
 * Every value here comes from `grants.json`. Nothing is computed.
 */
import { describe, GRANTS, type Role } from "@/lib/grants";

export function GrantsPanel({ role }: { role: Role }) {
  const grants = GRANTS[role];

  return (
    <div className="panel">
      <h2>{grants.label.split("·")[0].trim()} can search</h2>

      <ul className="grants">
        {grants.order.map((corpus, i) => (
          <li key={corpus} className={i === 0 ? "preferred" : undefined}>
            <span className="rank">{i + 1}</span>
            <span className="name">{describe(corpus)}</span>
            {i === 0 && grants.order.length > 1 && (
              <span className="tag">preferred</span>
            )}
          </li>
        ))}

        {/* The single most valuable row in the UI. With nested grants it is
            the ONLY place the enforced difference is visible before a
            question has been asked. The engineer's panel has none. */}
        {grants.withheld.map((corpus) => (
          <li key={corpus} className="withheld">
            <span className="rank">✗</span>
            <span className="name">{describe(corpus)}</span>
            <span className="tag">no tool</span>
          </li>
        ))}
      </ul>

      <p className="note">
        {grants.withheld.length > 0 ? (
          <>
            <strong>Enforced.</strong> The crossed-out corpus has no tool on
            this run — the model is never offered one, so it cannot call it
            even if asked to.
          </>
        ) : (
          <>
            <strong>Nested grants.</strong> This identity reaches everything
            the other one can, plus the internal runbooks. The numbering is a
            preference in the prompt, not a restriction.
          </>
        )}
      </p>
    </div>
  );
}
