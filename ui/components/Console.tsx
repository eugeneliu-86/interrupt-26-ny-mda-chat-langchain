"use client";

/**
 * The single-identity console (ph. 06 §3, §5).
 *
 * `useStream` points at `/api/lg` — the same-origin proxy — and never at the
 * deployment. No API key exists in this file or anywhere it can reach.
 *
 * NOTE WHAT IS ABSENT: `submit` is never called with `context`. The hook
 * accepts it, and passing the role from here would work perfectly and would
 * be WRONG: the proxy overwrites `context` from the httpOnly cookie (§1 rule
 * 2), and the moment the client contributes any part of the role, the role
 * becomes a value the browser sets. This comment exists because otherwise
 * someone will helpfully "fix" the omission.
 */
import { useStream } from "@langchain/langgraph-sdk/react";
import { useCallback, useRef, useState } from "react";

import { proxyUrl } from "@/lib/apiUrl";
import { describeError, isIdentityRejection } from "@/lib/content";
import type { Role } from "@/lib/grants";

export const ASSISTANT_ID = "role-aware-docs-assistant";

import { Transcript } from "./Transcript";

export function Console({
  role,
  traceBase,
  suggestions,
}: {
  role: Role;
  /** `…/projects/p/<id>`, handed down by the server. See TraceLink below. */
  traceBase: string;
  suggestions: string[];
}) {
  const [input, setInput] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const box = useRef<HTMLInputElement>(null);

  const stream = useStream({
    // Absolute, same-origin. The SDK cannot parse a relative apiUrl — see
    // lib/apiUrl.ts. Still this app's own origin; still no key in the browser.
    apiUrl: proxyUrl(),
    assistantId: ASSISTANT_ID,
    // No apiKey. The proxy holds it; a key here would be in the bundle.
    onCreated: (run) => {
      setRunId(run.run_id);
      setFailure(null);
    },
    onError: (err) => setFailure(describeError(err)),
  });

  const send = useCallback(
    (question: string) => {
      const q = question.trim();
      if (!q || stream.isLoading) return;
      setFailure(null);
      setInput("");
      stream.submit({ messages: [{ type: "human", content: q }] });
      box.current?.focus();
    },
    [stream],
  );

  const rejection = failure !== null && isIdentityRejection(failure);

  return (
    <div className="panel">
      <Transcript
        messages={stream.messages}
        loading={stream.isLoading}
        error={
          rejection
            ? "This run was rejected: no identity was selected. " +
              "(You should never see this through the UI — it means the " +
              "proxy did not attach a role.)"
            : failure
        }
        emptyHint={`Ask something as ${role}. Watch which corpus it reaches for.`}
      />

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          ref={box}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the documentation a question…"
          aria-label="Question"
        />
        {stream.isLoading ? (
          <button type="button" className="stop" onClick={() => stream.stop()}>
            Stop
          </button>
        ) : (
          <button type="submit" disabled={!input.trim()}>
            Ask
          </button>
        )}
      </form>

      <div className="suggestions">
        {suggestions.map((s) => (
          <button key={s} type="button" onClick={() => send(s)} disabled={stream.isLoading}>
            {s}
          </button>
        ))}
      </div>

      <div className="footer">
        <TraceLink base={traceBase} runId={runId} />
        <span>
          thread{" "}
          <code>{stream.values && runId ? "active" : "new on next question"}</code>
        </span>
      </div>
    </div>
  );
}

/**
 * The evidence link, for the skeptic in the room.
 *
 * WHY THIS IS A STRING CONCATENATION AND NOT A LOOKUP. The LangGraph
 * `run_id` **is** the LangSmith root run id and its trace id — measured
 * against the deployment in ph. 05, not assumed. So the trace URL is
 * knowable the instant the run is created, with no second request and no
 * race against the trace becoming queryable.
 *
 * The project half of the URL is handed down from the server (§5): the
 * browser has no environment of its own to assemble a LangSmith URL from,
 * and it should not be guessing one.
 */
function TraceLink({ base, runId }: { base: string; runId: string | null }) {
  if (!runId) return <span>no run yet</span>;
  return (
    <a href={`${base}/r/${runId}`} target="_blank" rel="noreferrer">
      view trace ↗
    </a>
  );
}
