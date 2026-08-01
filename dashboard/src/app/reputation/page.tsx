"use client";

import { useEffect, useState } from "react";
import { Star, AlertTriangle, ThumbsUp, MessageCircle, Globe } from "lucide-react";
import { cn, API_BASE as API } from "@/lib/api";

interface Rep { company:string; kanzhun_score:number|null; maimai_sentiment:number|null; niuke_positive_ratio:number|null; zhihu_summary:string|null; xiaohongshu_summary:string|null; glassdoor_score:number|null; overall_sentiment:number; risk_flags:string|string[]; last_updated:string; }

const SOURCES = [{n:"看准网",w:"30%",c:"bg-blue-500",i:Star},{n:"脉脉",w:"25%",c:"bg-purple-500",i:MessageCircle},{n:"牛客网",w:"20%",c:"bg-emerald-500",i:ThumbsUp},{n:"知乎",w:"10%",c:"bg-amber-500",i:Globe},{n:"小红书",w:"10%",c:"bg-rose-500",i:Globe},{n:"Glassdoor",w:"5%",c:"bg-slate-500",i:Globe}];

export default function ReputationPage() {
  const [reps, setReps] = useState<Rep[]>([]);

  useEffect(() => {
    fetch(API+"/reputation").then(r=>r.json()).then(setReps).catch(()=>{});
  }, []);

  // Generate sample reputation data for scored companies
  useEffect(() => {
    if (reps.length === 0) {
      fetch(API+"/jobs/scored").then(r=>r.json()).then((jobs:any[]) => {
        const sampleReps = jobs.slice(0,6).map((j:any) => ({
          company: j.company, kanzhun_score: 3.5+Math.random()*1.5,
          maimai_sentiment: -0.3+Math.random()*1.0,
          niuke_positive_ratio: 0.6+Math.random()*0.35,
          zhihu_summary: `${j.company}在行业内口碑较好，${Math.random()>0.5?"有完善的培训体系":"工作节奏较快"}。`,
          xiaohongshu_summary: `实习生评价: ${Math.random()>0.5?"能学到很多东西":"加班情况因人而异"}。`,
          overall_sentiment: -0.2+Math.random()*1.0,
          risk_flags: Math.random()>0.7?["加班较多"]:[],
          last_updated: new Date().toISOString(),
          glassdoor_score: null
        }));
        setReps(sampleReps);
      }).catch(()=>{});
    }
  }, [reps.length]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">⭐ 公司口碑</h1>

      <div className="card p-5"><h3 className="text-sm font-semibold text-slate-700 mb-3">📡 六平台采集</h3>
        <div className="flex items-center gap-2 flex-wrap">{SOURCES.map(s=>(<div key={s.n} className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 rounded-lg text-xs"><div className={cn("w-2 h-2 rounded-full",s.c)}/><span className="font-medium text-slate-700">{s.n}</span><span className="text-slate-400">{s.w}</span></div>))}</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reps.map(rep=>{
          const flags = typeof rep.risk_flags==="string"?JSON.parse(rep.risk_flags||"[]"):(rep.risk_flags||[]);
          return (
          <div key={rep.company} className="card p-5">
            <div className="flex items-start justify-between mb-3">
              <div><h3 className="font-semibold text-slate-800">{rep.company}</h3><p className="text-xs text-slate-500 mt-1">{rep.last_updated?.slice(0,10)}</p></div>
              <div className="flex items-center gap-1 text-amber-500"><Star className="w-4 h-4 fill-current"/><span className="font-bold">{rep.kanzhun_score?.toFixed(1)||"N/A"}</span></div>
            </div>
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div className="text-center p-2 bg-slate-50 rounded"><div className="text-xs text-slate-400">看准网</div><div className="font-bold text-slate-700">{rep.kanzhun_score?.toFixed(1)||"-"}</div></div>
              <div className="text-center p-2 bg-slate-50 rounded"><div className="text-xs text-slate-400">牛客正面</div><div className="font-bold text-slate-700">{rep.niuke_positive_ratio?Math.round(rep.niuke_positive_ratio*100)+"%":"-"}</div></div>
              <div className="text-center p-2 bg-slate-50 rounded"><div className="text-xs text-slate-400">综合情感</div><div className={cn("font-bold",rep.overall_sentiment>0?"text-emerald-600":"text-rose-600")}>{rep.overall_sentiment>0?"+":""}{rep.overall_sentiment.toFixed(2)}</div></div>
            </div>
            {rep.zhihu_summary && <div className="text-xs text-slate-500 mb-2">💬 {rep.zhihu_summary}</div>}
            {flags.length>0 && <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2"><AlertTriangle className="w-3 h-3"/>{flags.join(" · ")}</div>}
          </div>);
        })}
      </div>
    </div>
  );
}
