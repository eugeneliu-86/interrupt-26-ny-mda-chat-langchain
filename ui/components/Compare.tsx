"use client";

/**
 * Both identities, one question, side by side (ph. 06 §6).
 *
 * The strongest version of the demo is not switching identities — it is not
 * having to. Two panes, one input box, one submit: the audience sees the
 * divergence rather than being asked to remember the previous answer.
 *
 * Each pane pins its role with the `x-demo-role` header, which the proxy
 * validates against `grants.json` and honours ONLY when `DEMO_COMPARE_MODE`
 * is on. That is a deliberate, documented relaxation of the trust boundary
 * (see the route), and it is why compare mode is opt-in rather than default.
 */
import { useStream } from "@langchain/langgraph-sdk/react";
import { useCallback, useState } from "react";

import { proxyUrl } from "@/lib/apiUrl";
import { describeError } from "@/lib/content";
import { GRANTS, type Role } from "@/lib/grants";

import { ASSISTANT_ID } from "./Console";
import { Transcript } from "./Transcript";

function usePane(role: Role) {
  const [runId, setRunId] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const stream = useStream({
    // Absolute, same-origin. The SDK cannot parse a relative apiUrl — see
    // lib/apiUrl.ts. Still this app's own origin; still no key in the browser.
    apiUrl: proxyUrl(),
    assistantId: ASSISTANT_ID,
    defaultHeaders: { "x-demo-role": role },
    onCreated: (run) => {
      setRunId(run.run_id);
      setFailure(null);
    },
    onError: (err) => setFailure(describeError(err)),
  });
  return { role, stream, runId, failure };
}

export function Compare({
  roles,
  traceBase,
  suggestions,
}: {
  roles: Role[];
  traceBase: string;
  suggestions: string[];
}) {
  const [input, setInput] = useState("");
  // One hook per role. The hook count is fixed because `roles` comes from
  // `grants.json` at build time and the demo has exactly two identities;
  // a dynamic list would break the rules of hooks.
  const left = usePane(roles[0]);
  const right = usePane(roles[1]);
  const panes = [left, right];
  const busy = panes.some((p) => p.stream.isLoading);

  const send = useCallback(
    (question: string) => {
      const q = question.trim();
      if (!q || busy) return;
      setInput("");
      // Both runs start from the same submit. Separate threads, so neither
      // pane can see what the other fetched.
      for (const p of panes) {
        p.stream.submit({ messages: [{ type: "human", content: q }] });
      }
    },
    [busy, panes],
  );

  return (
    <div className="panel">
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask both identities the same question…"
          aria-label="Question for both identities"
        />
        {busy ? (
          <button
            type="button"
            className="stop"
            onClick={() => panes.forEach((p) => p.stream.stop())}
          >
            Stop
          </button>
        ) : (
          <button type="submit" disabled={!input.trim()}>
            Ask both
          </button>
        )}
      </form>

      <div className="suggestions">
        {suggestions.map((s) => (
          <button key={s} type="button" onClick={() => send(s)} disabled={busy}>
            {s}
          </button>
        ))}
      </div>

      <div className="compare" style={{ marginTop: 18 }}>
        {panes.map((p) => {
          const g = GRANTS[p.role];
          return (
            <section key={p.role}>
              <h3>
                {g.label}
                <span className="sub">
                  {g.withheld.length
                    ? `✗ ${g.withheld.length} corpus withheld`
                    : "all corpora"}
                </span>
              </h3>
              <Transcript
                messages={p.stream.messages}
                loading={p.stream.isLoading}
                error={p.failure}
                emptyHint="waiting for a question…"
              />
              <div className="footer">
                {p.runId ? (
                  <a href={`${traceBase}/r/${p.runId}`} target="_blank" rel="noreferrer">
                    view trace ↗
                  </a>
                ) : (
                  <span>no run yet</span>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
