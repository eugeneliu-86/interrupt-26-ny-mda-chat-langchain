import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Role-aware documentation assistant",
  description:
    "One deployed agent. Two simulated identities. Different tool surfaces.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
