import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Template Chatbot",
  description: "ADK-powered chatbot with decoupled FastAPI backend",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
