"use client";

/**
 * Rendering the conversation (ph. 06 §5).
 *
 * Three things here are not what a normal chat UI does, and each is load
 * bearing:
 *
 *   1. AI text comes from `textOf`, never from `message.content` directly —
 *      see lib/content.ts for the empty-bubble trap.
 *   2. Tool calls render as chips carrying the CORPUS and the PATH, during
 *      the run. The path is the evidence; a spinner is not.
 *   3. A failure renders as a visible error row. A silent failure is
 *      indistinguishable from a model with nothing to say.
 */
import type { Message } from "@langchain/langgraph-sdk";

import { chipsOf, textOf } from "@/lib/content";

export function Transcript({
  messages,
  error,
  loading,
  emptyHint,
}: {
  messages: Message[];
  error: string | null;
  loading: boolean;
  emptyHint: string;
}) {
  const visible = messages.filter((m) => m.type === "human" || m.type === "ai");

  return (
    <div className="thread">
      {visible.length === 0 && !error && (
        <p className="empty">{emptyHint}</p>
      )}

      {visible.map((m, i) => {
        if (m.type === "human") {
          return (
            <div className="msg human" key={m.id ?? `h${i}`}>
              <div className="who">You</div>
              <div className="body">{textOf(m.content)}</div>
            </div>
          );
        }

        const chips = chipsOf(m);
        const body = textOf(m.content);
        // An AI turn that is only tool calls has no text yet. Render the
        // chips alone rather than an empty bubble — that is the live
        // "it is reading the runbooks right now" moment.
        if (!chips.length && !body) return null;

        return (
          <div className="msg ai" key={m.id ?? `a${i}`}>
            {chips.length > 0 && (
              <div className="chips">
                {chips.map((c) => (
                  <span className={`chip ${c.corpus}`} key={c.id}>
                    <span className="corpus">{c.corpus}</span>
                    <span>{c.action}</span>
                    {c.arg && <span className="arg">{c.arg}</span>}
                  </span>
                ))}
              </div>
            )}
            {body && (
              <>
                <div className="who">Assistant</div>
                <div className="body">{body}</div>
              </>
            )}
          </div>
        );
      })}

      {error && (
        <div className="msg error" role="alert">
          <div className="who">Run failed</div>
          <div className="body">{error}</div>
        </div>
      )}

      {loading && <p className="empty">working&hellip;</p>}
    </div>
  );
}
