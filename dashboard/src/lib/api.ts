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
}

export interface Stats {
  total: number; new: number; scored: number; applied: number;
  replied: number; interview: number; offer: number;
  strong_recommend: number; recommend: number;
}

export interface FilterOptions {
  industry: string[]; company_type: string[]; location: string[]; decision: string[];
}

export interface AiAnalysis {
  fit_score: number; pros: string[]; cons: string[];
  advice: string; salary_analysis: string; skill_gaps: string[];
  company_brief: string;
}

export async function fetchJSON(path: string) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export function decisionBadge(d: string) {
  const m: Record<string, string> = {
    "强烈推荐": "bg-emerald-100 text-emerald-700",
    "推荐投递": "bg-blue-100 text-blue-700",
    "可投递": "bg-amber-100 text-amber-700",
    "建议跳过": "bg-gray-100 text-gray-500",
  };
  return m[d] || "bg-gray-100 text-gray-500";
}

export function scoreColor(s: number) {
  if (s >= 75) return "text-emerald-600";
  if (s >= 60) return "text-blue-600";
  if (s >= 45) return "text-amber-600";
  return "text-gray-400";
}
