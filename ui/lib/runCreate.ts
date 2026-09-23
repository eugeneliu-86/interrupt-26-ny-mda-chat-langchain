/**
 * Which request paths start a run (ph. 06 §2).
 *
 * Extracted from the proxy route so the test and the route share ONE
 * definition. A test that restated the pattern would pass while the route
 * used a different one, which is the precise failure this file prevents —
 * and the consequence of a missed shape is subtle: the run goes out with no
 * `context`, fails closed (C1), and presents as "the agent rejected me" with
 * nothing pointing at the regex.
 *
 * The shapes the LangGraph SDK issues:
 *
 *     POST /threads/{id}/runs           background run
 *     POST /threads/{id}/runs/stream    what `useStream` uses
 *     POST /threads/{id}/runs/wait      the e2e suite
 *     POST /runs                        stateless variants — the SDK will use
 *     POST /runs/stream                 these when no thread is created
 *     POST /runs/wait
 *
 * Deliberately NOT matched: `/threads/{id}/runs/{run_id}` and its
 * `/join`, `/cancel` and `/stream` sub-paths. Those act on a run that already
 * exists and carry no context to rewrite; matching them would try to parse a
 * body that is not there.
 */
export const RUN_CREATE = /^\/(?:threads\/[^/]+\/)?runs(?:\/(?:stream|wait))?$/;
