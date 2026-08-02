export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5175/api";

export interface Job {
  id: string; platform: string; title: string; company: string;
  company_type: string; industry: string; location: string;
  is_remote: number; salary_raw: string; salary_monthly_est: number | null;
  jd_raw: string; jd_clean: string; recruiter_email: string; apply_url: string;
  composite_score: number; decision: string;
  job_match_score: number; industry_match_score: number;
  salary_score: number; career_dev_score: number;
  job_match_detail?: any; industry_match_detail?: any;
  salary_detail?: any; career_dev_detail?: any;
  adjustments?: any; reputation?: any; reasoning?: string;
  status: string; scraped_at: string;
  // v3: track & tier
  track?: string; tracks?: string[];
  track_label?: string;
  company_tier?: string; company_tier_label?: string;
  company_tier_note?: string;
  ai_reasoning?: string;
}

export interface Stats {
  total: number; new: number; scored: number; applied: number;
  replied: number; interview: number; offer: number;
  strong_recommend: number; recommend: number;
  // v3
  priority?: number; worth?: number; consider?: number; skip?: number;
  track_distribution?: Record<string, number>;
  tier_S?: number; tier_A?: number; tier_B?: number; tier_C?: number;
  tier_unknown?: number;
}

export interface FilterOptions {
  industry: string[]; company_type: string[]; location: string[]; decision: string[];
  // v3
  track?: {id: string; label: string}[];
  company_tier?: {id: string; label: string}[];
}

export interface AiAnalysis {
  fit_score: number; pros: string[]; cons: string[];
  advice: string; salary_analysis: string; skill_gaps: string[];
  company_brief: string;
}

export interface TrackInfo {
  id: string; name: string; description: string;
}

export async function fetchJSON(path: string) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export function decisionBadge(d: string) {
  // v3: 新版四档决策
  const m: Record<string, string> = {
    "优先投": "bg-emerald-100 text-emerald-800 border-emerald-300",
    "值得投": "bg-blue-100 text-blue-800 border-blue-300",
    "可考虑": "bg-amber-100 text-amber-800 border-amber-300",
    "不推荐": "bg-gray-100 text-gray-400 border-gray-200",
    // 兼容旧版
    "强烈推荐": "bg-emerald-100 text-emerald-700",
    "推荐投递": "bg-blue-100 text-blue-700",
    "可投递": "bg-amber-100 text-amber-700",
    "建议跳过": "bg-gray-100 text-gray-500",
  };
  return m[d] || "bg-gray-100 text-gray-500";
}

export function tierBadge(t: string) {
  const m: Record<string, string> = {
    "S": "bg-purple-100 text-purple-800",
    "A": "bg-indigo-100 text-indigo-800",
    "B": "bg-teal-100 text-teal-800",
    "C": "bg-gray-100 text-gray-500",
    "U": "bg-gray-50 text-gray-400",
  };
  return m[t] || "bg-gray-50 text-gray-400";
}

export function scoreColor(s: number) {
  if (s >= 75) return "text-emerald-600";
  if (s >= 60) return "text-blue-600";
  if (s >= 45) return "text-amber-600";
  return "text-gray-400";
}
