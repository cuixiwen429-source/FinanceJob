import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinanceJob — 金融求职看板",
  description: "AI-powered financial job board",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
