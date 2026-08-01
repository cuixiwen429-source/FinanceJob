"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Search, MapPin, Briefcase, TrendingUp, X, Sparkles,
  ChevronLeft, ChevronRight, Loader2, ExternalLink, SlidersHorizontal,
} from "lucide-react";
import { API, fetchJSON, Job, Stats, AiAnalysis, decisionBadge, scoreColor } from "@/lib/api";

const PAGE_SIZE = 24;
const SORT_OPTIONS: Record<string, string> = {
  "composite_score DESC": "综合评分",
  "job_match_score DESC": "岗位匹配",
  "salary_monthly_est DESC": "薪资",
  "scraped_at DESC": "最新发布",
  "company ASC": "公司名",
};

export default function HomePage() {
  // Data
  const [stats, setStats] = useState<Stats>({ total: 0, new: 0, scored: 0, applied: 0, replied: 0, interview: 0, offer: 0, strong_recommend: 0, recommend: 0 });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters — comma-separated fuzzy keywords
  const [search, setSearch] = useState("");
  const [selIndustry, setSelIndustry] = useState("");
  const [selCompanyType, setSelCompanyType] = useState("");
  const [selLocation, setSelLocation] = useState("");
  const [selDecision, setSelDecision] = useState<string[]>([]);
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [minScore, setMinScore] = useState("");
  const [sort, setSort] = useState("composite_score DESC");
  const [page, setPage] = useState(0);

  const DECISIONS = ["强烈推荐", "推荐投递", "可投递", "建议跳过"];

  // Detail panel
  const [selected, setSelected] = useState<Job | null>(null);
  const [ai, setAi] = useState<AiAnalysis | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");

  // Mobile filter toggle
  const [showFilters, setShowFilters] = useState(false);

  const loadData = useCallback(async () => {
    try { setStats(await fetchJSON("/stats")); } catch {}
  }, []);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (selIndustry) params.set("industry", selIndustry);
      if (selCompanyType) params.set("company_type", selCompanyType);
      if (selLocation) params.set("location", selLocation);
      if (selDecision.length) params.set("decision", selDecision.join(","));
      if (remoteOnly) params.set("remote", "1");
      if (minScore) params.set("min_score", minScore);
      params.set("order", sort);
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(page * PAGE_SIZE));

      const data = await fetchJSON(`/jobs?${params.toString()}`);
      setJobs(data.jobs);
      setTotal(data.total);
    } catch {}
    setLoading(false);
  }, [search, selIndustry, selCompanyType, selLocation, selDecision, remoteOnly, minScore, sort, page]);

  useEffect(() => { loadData(); }, []);
  useEffect(() => { loadJobs(); }, [loadJobs]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const analyzeWithAI = async (job: Job) => {
    setAiLoading(true); setAiError(""); setAi(null);
    try {
      const res = await fetch(`${API}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: job.id }),
      });
      const data = await res.json();
      if (data.error) { setAiError(data.error); } else { setAi(data); }
    } catch { setAiError("AI 分析失败"); }
    setAiLoading(false);
  };

  const clearFilters = () => {
    setSearch(""); setSelIndustry(""); setSelCompanyType(""); setSelLocation("");
    setSelDecision([]); setRemoteOnly(false); setMinScore(""); setSort("composite_score DESC"); setPage(0);
  };
  const hasFilters = search || selIndustry || selCompanyType || selLocation || selDecision.length || remoteOnly || minScore;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-30">
        <div className="max-w-[1440px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold text-slate-800">
                <Briefcase className="inline w-5 h-5 mr-1.5 text-blue-600" />
                FinanceJob
              </h1>
              <span className="text-xs text-slate-400">金融求职智能看板</span>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <StatBadge label="岗位总数" value={stats.total} color="text-slate-600" />
              <StatBadge label="已评分" value={stats.scored} color="text-blue-600" />
              <StatBadge label="强烈推荐" value={stats.strong_recommend} color="text-emerald-600" />
              <StatBadge label="推荐投递" value={stats.recommend} color="text-indigo-600" />
            </div>
          </div>
        </div>
      </header>

      {/* Filter bar */}
      <div className="bg-white border-b">
        <div className="max-w-[1440px] mx-auto px-4 py-2.5">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Search */}
            <div className="relative flex-1 min-w-[160px] max-w-[280px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}
                placeholder="搜索公司、岗位、行业..."
                className="w-full pl-8 pr-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>

            {/* Mobile filter toggle */}
            <button onClick={() => setShowFilters(!showFilters)}
                    className="md:hidden flex items-center gap-1 text-xs px-3 py-1.5 border rounded-lg text-slate-500">
              <SlidersHorizontal className="w-3 h-3" /> 筛选
            </button>

            <div className={`${showFilters ? 'flex' : 'hidden'} md:flex items-center gap-2 flex-wrap`}>
              {/* Industry — fuzzy keyword input */}
              <input
                value={selIndustry} onChange={e => { setSelIndustry(e.target.value); setPage(0); }}
                placeholder="行业（逗号分隔）"
                className="w-36 px-2 py-1.5 text-xs border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
              {/* Company type — fuzzy keyword input */}
              <input
                value={selCompanyType} onChange={e => { setSelCompanyType(e.target.value); setPage(0); }}
                placeholder="公司类型（逗号分隔）"
                className="w-40 px-2 py-1.5 text-xs border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
              {/* Location — fuzzy keyword input */}
              <input
                value={selLocation} onChange={e => { setSelLocation(e.target.value); setPage(0); }}
                placeholder="地点（逗号分隔）"
                className="w-36 px-2 py-1.5 text-xs border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
              />

              {/* Decision — clickable multi-select chips */}
              <div className="flex items-center gap-0.5">
                {DECISIONS.map(d => (
                  <button key={d} onClick={() => {
                    setSelDecision(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);
                    setPage(0);
                  }}
                  className={`text-[10px] px-1.5 py-1 rounded-full border transition-colors whitespace-nowrap
                    ${selDecision.includes(d) ? 'bg-blue-100 border-blue-400 text-blue-700' : 'bg-white text-slate-500 hover:bg-slate-50'}`}>
                    {d}
                  </button>
                ))}
              </div>

              <label className={`flex items-center gap-1.5 text-xs cursor-pointer select-none px-2 py-1.5 border rounded-lg
                                ${remoteOnly ? 'bg-blue-50 border-blue-300' : 'hover:bg-slate-50'}`}>
                <input type="checkbox" checked={remoteOnly} onChange={e => { setRemoteOnly(e.target.checked); setPage(0); }}
                       className="w-3 h-3" />
                仅远程
              </label>

              <input type="number" value={minScore} onChange={e => { setMinScore(e.target.value); setPage(0); }}
                     placeholder="最低分" min="0" max="100"
                     className="w-16 px-2 py-1.5 text-xs border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200" />

              <select value={sort} onChange={e => { setSort(e.target.value); setPage(0); }}
                      className="text-xs px-2 py-1.5 border rounded-lg bg-white text-slate-600">
                {Object.entries(SORT_OPTIONS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>

              {hasFilters && (
                <button onClick={clearFilters} className="text-xs text-red-500 hover:underline px-2 py-1.5 whitespace-nowrap">
                  清除筛选
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-[1440px] mx-auto px-4 py-4">
        {/* Results info */}
        <div className="flex items-center justify-between mb-3 text-xs text-slate-500">
          <span>共 {total} 个岗位</span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
                    className="p-1 rounded hover:bg-slate-200 disabled:opacity-30"><ChevronLeft className="w-4 h-4" /></button>
            <span className="px-2">{page + 1} / {Math.max(1, totalPages)}</span>
            <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
                    className="p-1 rounded hover:bg-slate-200 disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
          </div>
        </div>

        {/* Job grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin mr-2" /> 加载中...
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-20 text-slate-400">没有匹配的岗位</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {jobs.map(job => (
              <JobCard key={job.id} job={job} onClick={() => { setSelected(job); setAi(null); setAiError(""); }} />
            ))}
          </div>
        )}
      </div>

      {/* Detail panel (slide-in) */}
      {selected && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30 animate-fade-in" onClick={() => setSelected(null)} />
          <div className="relative w-full max-w-lg bg-white h-full overflow-y-auto animate-slide-in shadow-xl">
            {/* Panel header */}
            <div className="sticky top-0 bg-white border-b px-5 py-3 flex items-center justify-between z-10">
              <h2 className="font-semibold text-slate-800 truncate pr-4">{selected.company}</h2>
              <button onClick={() => setSelected(null)} className="p-1 rounded hover:bg-slate-100">
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>

            <div className="p-5 space-y-5">
              {/* Basic info */}
              <div>
                <h3 className="text-lg font-medium text-slate-800 mb-2">{selected.title}</h3>
                <div className="flex flex-wrap gap-2 text-xs">
                  <Tag>{selected.industry || "未知行业"}</Tag>
                  <Tag>{selected.company_type || "未知类型"}</Tag>
                  <Tag><MapPin className="w-3 h-3 inline mr-0.5" />{selected.is_remote ? "远程" : selected.location || "未知"}</Tag>
                  {selected.salary_raw && <Tag>{selected.salary_raw}</Tag>}
                  {selected.salary_monthly_est && <Tag>~{selected.salary_monthly_est}元/月</Tag>}
                </div>
                {selected.apply_url && (
                  <a href={selected.apply_url} target="_blank" rel="noreferrer"
                     className="inline-flex items-center gap-1 mt-2 text-xs text-blue-600 hover:underline">
                    <ExternalLink className="w-3 h-3" /> 投递链接
                  </a>
                )}
              </div>

              {/* Score bars */}
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" /> 四维评分
                  <span className={`text-lg font-bold ml-auto ${scoreColor(selected.composite_score)}`}>
                    {selected.composite_score?.toFixed(0)}
                  </span>
                </h4>
                <div className="space-y-2">
                  <ScoreRow label="岗位匹配" score={selected.job_match_score} />
                  <ScoreRow label="行业匹配" score={selected.industry_match_score} />
                  <ScoreRow label="薪资分析" score={selected.salary_score} />
                  <ScoreRow label="职业发展" score={selected.career_dev_score} />
                </div>
                {selected.decision && (
                  <span className={`inline-block mt-3 text-xs px-2.5 py-1 rounded-full font-medium ${decisionBadge(selected.decision)}`}>
                    {selected.decision}
                  </span>
                )}
              </div>

              {/* JD */}
              {selected.jd_clean && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-2">岗位描述</h4>
                  <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line max-h-60 overflow-y-auto bg-slate-50 rounded-lg p-3">
                    {selected.jd_clean}
                  </p>
                </div>
              )}

              {/* Detailed analysis JSON */}
              {selected.job_match_detail && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-2">详细分析</h4>
                  <div className="text-xs text-slate-500 space-y-1 bg-slate-50 rounded-lg p-3">
                    {selected.job_match_detail?.matched_keywords && (
                      <p>匹配关键词: {selected.job_match_detail.matched_keywords?.join?.(", ") || "-"}</p>
                    )}
                    {selected.industry_match_detail?.rationale && (
                      <p>行业判断: {selected.industry_match_detail.rationale}</p>
                    )}
                    {selected.salary_detail?.level && (
                      <p>薪资水平: {selected.salary_detail.level}</p>
                    )}
                    {selected.reasoning && <p className="text-slate-600">{selected.reasoning}</p>}
                  </div>
                </div>
              )}

              {/* AI Analysis */}
              <div className="border-t pt-4">
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-500" /> AI 深度分析
                </h4>
                {!ai && !aiLoading && !aiError && (
                  <button onClick={() => analyzeWithAI(selected)}
                          className="w-full py-2.5 text-sm font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors flex items-center justify-center gap-2">
                    <Sparkles className="w-4 h-4" /> DeepSeek AI 分析此岗位
                  </button>
                )}
                {aiLoading && (
                  <div className="flex items-center gap-2 text-sm text-slate-500 py-4">
                    <Loader2 className="w-4 h-4 animate-spin" /> AI 分析中...
                  </div>
                )}
                {aiError && (
                  <div className="text-sm text-red-500 bg-red-50 rounded-lg p-3">
                    {aiError === "AI not configured (set DEEPSEEK_API_KEY in .env)"
                      ? "AI 未配置，请在 .env 中设置 DEEPSEEK_API_KEY"
                      : aiError}
                  </div>
                )}
                {ai && (
                  <div className="space-y-3 animate-fade-in">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">匹配度</span>
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all ${ai.fit_score >= 70 ? 'bg-emerald-500' : ai.fit_score >= 50 ? 'bg-amber-500' : 'bg-red-400'}`}
                             style={{ width: `${ai.fit_score}%` }} />
                      </div>
                      <span className="text-sm font-bold text-slate-700">{ai.fit_score}</span>
                    </div>
                    {ai.company_brief && <p className="text-xs text-slate-600 bg-slate-50 rounded-lg p-2.5">{ai.company_brief}</p>}
                    {ai.salary_analysis && <p className="text-xs text-slate-600">{ai.salary_analysis}</p>}
                    {ai.pros?.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-emerald-600 mb-1">优势</p>
                        <ul className="text-xs text-slate-600 space-y-1">
                          {ai.pros.map((p, i) => <li key={i} className="flex gap-1"><span className="text-emerald-400">+</span> {p}</li>)}
                        </ul>
                      </div>
                    )}
                    {ai.cons?.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-red-500 mb-1">风险</p>
                        <ul className="text-xs text-slate-600 space-y-1">
                          {ai.cons.map((p, i) => <li key={i} className="flex gap-1"><span className="text-red-400">-</span> {p}</li>)}
                        </ul>
                      </div>
                    )}
                    {ai.skill_gaps?.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-amber-600 mb-1">需补强技能</p>
                        <div className="flex flex-wrap gap-1">
                          {ai.skill_gaps.map((s, i) => (
                            <span key={i} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">{s}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {ai.advice && <p className="text-xs text-slate-700 bg-blue-50 rounded-lg p-2.5">{ai.advice}</p>}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ── */

function StatBadge({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="text-center">
      <div className={`text-base font-bold ${color}`}>{value}</div>
      <div className="text-[10px] text-slate-400">{label}</div>
    </div>
  );
}

function JobCard({ job, onClick }: { job: Job; onClick: () => void }) {
  return (
    <div onClick={onClick}
         className="bg-white rounded-xl border p-4 cursor-pointer hover:shadow-md hover:border-blue-200 transition-all group">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-800 truncate">{job.company}</h3>
          <p className="text-xs text-slate-500 truncate mt-0.5">{job.title}</p>
        </div>
        <span className={`text-sm font-bold ml-2 ${scoreColor(job.composite_score)}`}>
          {job.composite_score?.toFixed(0)}
        </span>
      </div>
      <div className="flex flex-wrap gap-1 mb-2.5">
        <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
          <MapPin className="w-2.5 h-2.5 inline mr-0.5" />{job.is_remote ? "远程" : job.location || "-"}
        </span>
        {job.salary_raw && <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{job.salary_raw}</span>}
        {job.industry && <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded truncate max-w-[120px]">{job.industry}</span>}
      </div>
      <div className="flex items-center justify-between">
        {job.decision && (
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${decisionBadge(job.decision)}`}>
            {job.decision}
          </span>
        )}
        <span className="text-[10px] text-slate-400">{job.company_type}</span>
      </div>
    </div>
  );
}

function ScoreRow({ label, score }: { label: string; score: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-500 w-16">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${score >= 70 ? 'bg-emerald-400' : score >= 55 ? 'bg-blue-400' : 'bg-amber-400'}`}
             style={{ width: `${Math.min(100, score || 0)}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-600 w-8 text-right">{score?.toFixed(0)}</span>
    </div>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{children}</span>;
}
