import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Role-aware documentation assistant",
  description:
    "One deployed agent. Two simulated identities. Different tool surfaces.",
};

/**
 * Set the theme BEFORE the first paint.
 *
 * Without this the page renders dark, React hydrates, an effect reads
 * localStorage, and a light-mode viewer sees a dark flash on every
 * navigation. Running during head parsing means the attribute is already on
 * `<html>` when the first pixel is drawn.
 *
 * Dark is the default, so an unset or unreadable store needs no branch.
 */
const SET_THEME = `try{var t=localStorage.getItem("demo-theme");if(t==="light")document.documentElement.dataset.theme="light"}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SET_THEME }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
