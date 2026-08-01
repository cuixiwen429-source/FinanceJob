"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Briefcase, Target, BarChart3, Star,
  FileText, Send, Building2, Settings, ChevronLeft, TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/stores/app";

const navItems = [
  { href: "/", label: "总览", icon: LayoutDashboard },
  { href: "/jobs", label: "岗位看板", icon: Briefcase },
  { href: "/scoring", label: "评分对比", icon: BarChart3 },
  { href: "/reputation", label: "公司口碑", icon: Star },
  { href: "/resume", label: "简历管理", icon: FileText },
  { href: "/tracker", label: "投递追踪", icon: Target },
  { href: "/emails", label: "邮件管理", icon: Send },
  { href: "/companies", label: "公司库", icon: Building2 },
  { href: "/settings", label: "设置", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);

  return (
    <aside
      className={cn(
        "sidebar fixed left-0 top-0 h-screen z-40 flex flex-col transition-all duration-300",
        sidebarOpen ? "w-56" : "w-16"
      )}
    >
      <div className="flex items-center gap-3 px-4 h-16 border-b border-slate-700/50">
        <TrendingUp className="w-6 h-6 text-emerald-400 shrink-0" />
        {sidebarOpen && (
          <span className="text-white font-bold text-sm tracking-wide">
            FinanceJob
          </span>
        )}
      </div>

      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                active
                  ? "bg-slate-700/80 text-white font-medium"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/50"
              )}
            >
              <Icon className="w-5 h-5 shrink-0" />
              {sidebarOpen && <span>{label}</span>}
              {active && sidebarOpen && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 py-3 border-t border-slate-700/50">
        <div className={cn("flex items-center gap-2 text-xs text-slate-500", !sidebarOpen && "justify-center")}>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          {sidebarOpen && "2028届 · 崔曦文"}
        </div>
      </div>
    </aside>
  );
}
