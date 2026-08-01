import type { Metadata } from "next";
import Sidebar from "@/components/layout/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinanceJob — 金融求职看板",
  description: "全自动金融求职投递系统 · 崔曦文 · 2028届",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="bg-slate-50 min-h-screen">
        <Sidebar />
        <main className="pl-56 min-h-screen">
          <div className="max-w-7xl mx-auto px-6 py-6">{children}</div>
        </main>
      </body>
    </html>
  );
}
