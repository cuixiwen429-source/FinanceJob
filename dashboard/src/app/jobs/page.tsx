"use client";

import { useEffect, useState } from "react";
import { Search, MapPin, Calendar, Mail, ExternalLink } from "lucide-react";
import { cn, API_BASE as API } from "@/lib/api";

interface Job { id:string;platform:string;title:string;company:string;location:string;is_remote:boolean;salary_raw:string;recruiter_email:string;composite_score:number;rank:number;decision:string;job_match_score:number;industry_match_score:number;salary_score:number;career_dev_score:number;status:string;scraped_at:string;jd_clean:string;apply_url:string; }


export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Job|null>(null);

  useEffect(() => {
    fetch(API+"/jobs").then(r=>r.json()).then(j=>{setJobs(j);setLoading(false);}).catch(()=>setLoading(false));
  }, []);

  const filtered = jobs
    .filter(j => filter==="all"||filter==="strong"&&j.decision==="强烈推荐"||filter==="recommend"&&["强烈推荐","推荐投递"].includes(j.decision))
    .filter(j => !search||j.title.includes(search)||j.company.includes(search))
    .sort((a,b)=>b.composite_score-a.composite_score);

  const scoreColor = (s:number) => s>=75?"text-emerald-600 bg-emerald-50":s>=60?"text-blue-600 bg-blue-50":s>=45?"text-amber-600 bg-amber-50":"text-slate-400 bg-slate-50";

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-400">加载岗位数据...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">💼 岗位看板</h1>
          <p className="text-sm text-slate-500 mt-1">{filtered.length} 个岗位 · 按综合评分降序 · 实时数据</p>
        </div>
        <button onClick={()=>fetch(API+"/jobs").then(r=>r.json()).then(setJobs)} className="text-xs text-slate-500 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full">🔄 刷新</button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input type="text" placeholder="搜索公司/岗位..." className="w-full pl-9 pr-4 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
                 value={search} onChange={e=>setSearch(e.target.value)} />
        </div>
        {[{k:"all",l:"全部"},{k:"strong",l:"🟢 强烈推荐"},{k:"recommend",l:"🔵 推荐+"}].map(f=>(
          <button key={f.k} onClick={()=>setFilter(f.k)} className={cn("px-3 py-1.5 text-xs rounded-full font-medium transition-colors",filter===f.k?"bg-slate-800 text-white":"bg-slate-100 text-slate-600 hover:bg-slate-200")}>{f.l}</button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map(job=>(
          <div key={job.id} className="card p-5 hover:shadow-md transition-all cursor-pointer group" onClick={()=>setSelected(job)}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-slate-800 group-hover:text-blue-600">{job.title}</h3>
                <p className="text-sm text-slate-500">{job.company} <span className="text-xs text-slate-300">· {job.platform}</span></p>
              </div>
              <span className={cn("text-xs px-2 py-1 rounded-full font-medium", scoreColor(job.composite_score))}>{job.decision}</span>
            </div>

            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl font-bold text-slate-700">{job.composite_score}</span>
              <span className="text-xs text-slate-400">/100</span>
              <span className="text-xs text-slate-400 ml-auto">#{job.rank} 位</span>
            </div>

            <div className="grid grid-cols-4 gap-2 mb-3">
              {[{l:"岗位匹配",v:job.job_match_score},{l:"行业匹配",v:job.industry_match_score},{l:"薪资",v:job.salary_score},{l:"发展前景",v:job.career_dev_score}].map(d=>(
                <div key={d.l} className="text-center p-1.5 bg-slate-50 rounded">
                  <div className="text-xs text-slate-400">{d.l}</div>
                  <div className="text-sm font-semibold text-slate-600">{d.v}</div>
                </div>
              ))}
            </div>

            <div className="flex items-center gap-3 text-xs text-slate-400">
              <span className="flex items-center gap-1"><MapPin className="w-3 h-3"/>{job.is_remote?"🌐 远程":job.location}</span>
              <span className="flex items-center gap-1"><Calendar className="w-3 h-3"/>{job.scraped_at?.slice(0,10)}</span>
              {job.recruiter_email && <span className="flex items-center gap-1 text-emerald-600"><Mail className="w-3 h-3"/>{job.recruiter_email}</span>}
              {job.apply_url && (
                <a href={job.apply_url} target="_blank" onClick={e=>e.stopPropagation()} className="flex items-center gap-1 text-blue-500 hover:text-blue-700 ml-auto">
                  <ExternalLink className="w-3 h-3"/>来源
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-6" onClick={()=>setSelected(null)}>
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6 shadow-2xl" onClick={e=>e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-800">{selected.title}</h2>
                <p className="text-slate-500">{selected.company} · {selected.platform}</p>
              </div>
              <button onClick={()=>setSelected(null)} className="text-slate-400 hover:text-slate-600 text-xl">&times;</button>
            </div>
            <div className="grid grid-cols-4 gap-4 mb-4">
              {[{l:"岗位匹配",v:selected.job_match_score,c:"text-blue-600"},{l:"行业匹配",v:selected.industry_match_score,c:"text-emerald-600"},{l:"薪资评分",v:selected.salary_score,c:"text-amber-600"},{l:"发展前景",v:selected.career_dev_score,c:"text-purple-600"}].map(d=>(
                <div key={d.l} className="text-center p-3 bg-slate-50 rounded-xl">
                  <div className="text-xs text-slate-400 mb-1">{d.l}</div>
                  <div className={cn("text-2xl font-bold",d.c)}>{d.v}</div>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 mb-4">
              <span className={cn("text-sm px-3 py-1 rounded-full font-medium",scoreColor(selected.composite_score))}>{selected.decision}</span>
              <span className="text-2xl font-bold text-slate-700">{selected.composite_score}</span>
              <span className="text-sm text-slate-400">/100 · #{selected.rank}位</span>
            </div>
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-slate-600 mb-2">📋 岗位描述</h4>
              <p className="text-sm text-slate-600 bg-slate-50 rounded-xl p-4 whitespace-pre-wrap">{selected.jd_clean||"(暂无详细JD)"}</p>
            </div>
            {selected.recruiter_email && <div className="text-sm text-emerald-600 bg-emerald-50 rounded-xl p-3">📧 HR邮箱: {selected.recruiter_email}</div>}
          </div>
        </div>
      )}
    </div>
  );
}
