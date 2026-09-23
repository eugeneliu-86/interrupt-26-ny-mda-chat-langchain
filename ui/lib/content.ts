/**
 * Reading what the model actually said (ph. 06 §5).
 *
 * THE TRAP THIS EXISTS FOR. With `gpt-5.6-luna` an AI message's `content` is
 * not a string. It arrives as a list of blocks:
 *
 *     [{type: "reasoning"}, {type: "function_call"}, {type: "text", text: …}]
 *
 * A renderer that expects a string shows an EMPTY BUBBLE — which reads as
 * "the agent said nothing" rather than as a parsing bug, and cost real time
 * in phase 01 before anyone thought to inspect the payload. The SDK's own
 * `MessageContentComplex` union covers only text and image blocks, so the
 * reasoning and function_call blocks are not merely unhandled, they are
 * untyped: narrowing has to be done defensively rather than by the union.
 *
 * Render the text blocks. Ignore the rest.
 */
import type { Message } from "@langchain/langgraph-sdk";

/** Every `text` block of a message, joined. "" when the model produced none. */
export function textOf(content: Message["content"] | undefined): string {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  const parts: string[] = [];
  for (const block of content as unknown[]) {
    if (typeof block === "string") {
      parts.push(block);
      continue;
    }
    if (block && typeof block === "object") {
      const b = block as Record<string, unknown>;
      if (b.type === "text" && typeof b.text === "string") parts.push(b.text);
    }
  }
  return parts.join("").trim();
}

export interface ToolChip {
  /** `engineeringDocs` — the corpus, which is the enforced half. */
  corpus: string;
  /** `search_docs` | `fetch_doc` */
  action: string;
  /** The page path or the query. The PROOF, and the reason a chip beats a spinner. */
  arg: string;
  id: string;
}

/**
 * Turn an AI message's tool calls into chips.
 *
 * Arguments come from the CALLING side. A `ToolMessage` carries the result
 * and the name but not the arguments, and the arguments are the whole point:
 * "engineeringDocs__fetch_doc resilience-standards" is evidence, while
 * "engineeringDocs__fetch_doc" is a claim.
 */
export function chipsOf(message: Message): ToolChip[] {
  if (message.type !== "ai") return [];
  const calls = (message as { tool_calls?: unknown[] }).tool_calls;
  if (!Array.isArray(calls)) return [];

  const chips: ToolChip[] = [];
  for (const raw of calls) {
    if (!raw || typeof raw !== "object") continue;
    const call = raw as { name?: unknown; args?: unknown; id?: unknown };
    if (typeof call.name !== "string" || !call.name.includes("__")) continue;

    const [corpus, action] = call.name.split("__", 2);
    const args = (call.args ?? {}) as Record<string, unknown>;
    const arg =
      typeof args.path === "string"
        ? args.path
        : typeof args.query === "string"
          ? `"${args.query}"`
          : "";
    chips.push({
      corpus,
      action,
      arg,
      id: typeof call.id === "string" ? call.id : `${corpus}-${action}-${chips.length}`,
    });
  }
  return chips;
}

/**
 * A run that died, if it did.
 *
 * A DEAD RUN ANSWERS HTTP 200. `/runs/wait` returns `{"__error__": …}` with
 * no messages when a tool raises — observed in phase 02. A renderer that
 * trusts the status code shows an empty bubble, which reads as a silent agent
 * rather than as a failure, and is the single worst thing that can happen on
 * stage because it is indistinguishable from the model having nothing to say.
 */
export function errorOf(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const err = (payload as Record<string, unknown>).__error__;
  if (!err) return null;
  if (typeof err === "string") return err;
  const m = (err as Record<string, unknown>).message;
  return typeof m === "string" ? m : JSON.stringify(err);
}

/**
 * Turn whatever `useStream`'s `onError` handed us into one readable line.
 *
 * A run rejected for having no valid role (C1) arrives here, not as a
 * message. Rendering nothing would look broken — and that path should be
 * unreachable through this UI, so when it *does* appear it is reporting a bug
 * in the proxy's RUN_CREATE matching, which is precisely when you want to see
 * it rather than a blank screen.
 */
export function describeError(error: unknown): string {
  if (!error) return "The run failed.";
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  if (typeof error === "object") {
    const e = error as Record<string, unknown>;
    for (const k of ["message", "error", "detail"]) {
      if (typeof e[k] === "string") return e[k] as string;
    }
    return JSON.stringify(error);
  }
  return String(error);
}

/** True when the failure is C1 refusing a run with no usable identity. */
export function isIdentityRejection(text: string): boolean {
  return /requires context\.role|unknown role|no identity selected/i.test(text);
}
