"use client";

/**
 * Light / dark, with dark as the default.
 *
 * Dark is the default because the demo is projected in a dark room. The
 * choice is remembered in `localStorage` and applied to `<html data-theme>`,
 * which every CSS rule reads through tokens — so one attribute swaps the
 * whole UI.
 *
 * WHY THE INITIAL VALUE IS READ IN AN EFFECT AND NOT DURING RENDER. The
 * server has no idea what this browser chose, so rendering the stored theme
 * directly would produce markup that disagrees with the server's and React
 * would complain about a hydration mismatch. The real work of avoiding a
 * flash is done *before* React exists, by the inline script in `layout.tsx`:
 * it sets the attribute during head parsing, so the first paint is already
 * correct. This component only catches up with what that script decided.
 */
import { useEffect, useState } from "react";

export const THEME_KEY = "demo-theme";

type Theme = "dark" | "light";

function current(): Theme {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => setTheme(current()), []);

  function flip() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // Private browsing, or storage disabled. The toggle still works for
      // this page view; it just will not be remembered. Not worth failing.
    }
  }

  const goingTo = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      className="themetoggle"
      onClick={flip}
      aria-label={`Switch to ${goingTo} mode`}
      title={`Switch to ${goingTo} mode`}
    >
      <span aria-hidden>{theme === "dark" ? "☀" : "☾"}</span>
    </button>
  );
}
