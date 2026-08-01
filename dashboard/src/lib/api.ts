/** API 数据获取 — 从 Python 后端 SQLite 读取 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const API_BASE = "/api";

export interface JobData {
  id: string;
  platform: string;
  title: string;
  company: string;
  company_type: string;
  industry: string;
  location: string;
  is_remote: boolean;
  salary_raw: string;
  salary_monthly_est: number | null;
  jd_clean: string;
  recruiter_email: string;
  apply_url: string;
  composite_score: number;
  rank: number;
  percentile: number;
  decision: string;
  job_match_score: number;
  industry_match_score: number;
  salary_score: number;
  career_dev_score: number;
  adjustments: string;
  reputation: string | null;
  status: string;
  reasoning: string;
  tailored_resume_path: string;
  cover_letter: string;
  scraped_at: string;
}

export interface StatsData {
  total: number;
  new: number;
  scored: number;
  applied: number;
  replied: number;
  interview: number;
  offer: number;
  strong_recommend: number;
  recommend: number;
}

async function fetchAPI(path: string) {
  try {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// 在 API 后端启动前，使用静态示例数据
function mockStats(): StatsData {
  return {
    total: 0, new: 0, scored: 0, applied: 0,
    replied: 0, interview: 0, offer: 0,
    strong_recommend: 0, recommend: 0,
  };
}

// 决策标签颜色
export function decisionColor(decision: string): string {
  switch (decision) {
    case "强烈推荐": return "text-emerald-600 bg-emerald-50";
    case "推荐投递": return "text-blue-600 bg-blue-50";
    case "可投递": return "text-amber-600 bg-amber-50";
    case "建议跳过": return "text-gray-400 bg-gray-50";
    default: return "text-gray-500 bg-gray-50";
  }
}

export function decisionEmoji(decision: string): string {
  switch (decision) {
    case "强烈推荐": return "🟢";
    case "推荐投递": return "🔵";
    case "可投递": return "🟡";
    default: return "⚪";
  }
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    new: "新发现", scored: "已评分", resume_ready: "简历就绪",
    applied: "已投递", replied: "已回复", interview: "面试中",
    offer: "Offer", rejected: "已拒绝", archived: "已归档",
  };
  return labels[status] || status;
}

export function scoreBar(score: number): { width: string; color: string } {
  if (score >= 75) return { width: `${score}%`, color: "bg-emerald-500" };
  if (score >= 60) return { width: `${score}%`, color: "bg-blue-500" };
  if (score >= 45) return { width: `${score}%`, color: "bg-amber-500" };
  return { width: `${score}%`, color: "bg-gray-300" };
}
