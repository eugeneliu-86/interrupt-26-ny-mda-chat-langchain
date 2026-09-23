/**
 * The same-origin proxy URL, in the form the SDK can actually parse.
 *
 * WHY THIS IS NOT JUST THE STRING "/api/lg". The LangGraph SDK builds every
 * request with
 *
 *     new URL(`${this.apiUrl}${path}`)
 *
 * — one argument, no base. `new URL("/api/lg/threads")` throws
 * `TypeError: Failed to construct 'URL': Invalid URL`, so a relative apiUrl
 * fails on the FIRST request, in the browser, with a message that says
 * nothing about apiUrl. Every run shows "Run failed: Failed to construct
 * 'URL': Invalid URL" and nothing reaches the network tab.
 *
 * This cost a round of testing to find because the whole proxy suite drives
 * the routes over raw HTTP and never constructs an SDK client — the server
 * side was correct the entire time.
 *
 * NOTHING ABOUT THE TRUST BOUNDARY CHANGES. This is still the app's own
 * origin, still the same proxy route, still no key in the browser. Only the
 * spelling of the string differs: absolute instead of relative.
 */

/** The proxy path. One definition, used to build the URL and by the tests. */
export const PROXY_PATH = "/api/lg";

/**
 * During SSR there is no `window`, and `useStream` is constructed on the
 * server before it is ever used. It issues no requests there, so a syntactically
 * valid placeholder is enough — it is replaced on the client's first render.
 * It must still parse, or the SSR pass throws instead of the browser.
 */
const SSR_PLACEHOLDER = `http://ssr.invalid${PROXY_PATH}`;

export function proxyUrl(): string {
  if (typeof window === "undefined") return SSR_PLACEHOLDER;
  return `${window.location.origin}${PROXY_PATH}`;
}
