"use client";

import { useEffect, useState } from "react";
import { cn, API_BASE as API } from "@/lib/api";

const COLS = [{k:"new",l:"🆕 新发现",c:"bg-purple-50 border-purple-200"},{k:"scored",l:"📊 已评分",c:"bg-blue-50 border-blue-200"},{k:"resume_ready",l:"📝 简历就绪",c:"bg-cyan-50 border-cyan-200"},{k:"applied",l:"📨 已投递",c:"bg-emerald-50 border-emerald-200"},{k:"replied",l:"💬 已回复",c:"bg-amber-50 border-amber-200"},{k:"interview",l:"🎤 面试中",c:"bg-orange-50 border-orange-200"},{k:"offer",l:"🎉 Offer",c:"bg-rose-50 border-rose-200"}];

interface Job { id:string;company:string;title:string;composite_score:number;decision:string;status:string; }

export default function TrackerPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedId, setSelectedId] = useState<string|null>(null);

  useEffect(() => {
    fetch(API+"/jobs").then(r=>r.json()).then(setJobs).catch(()=>{});
  }, []);

  const byStatus = (status:string) => jobs.filter(j=>j.status===status);

  const moveJob = async (id:string, newStatus:string) => {
    // Update locally for instant feedback
    setJobs(jobs.map(j=>j.id===id?{...j,status:newStatus}:j));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">🎯 投递追踪</h1>
        <button onClick={()=>fetch(API+"/jobs").then(r=>r.json()).then(setJobs)} className="text-xs text-slate-500 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full">🔄 刷新</button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {COLS.map(col=>{
          const items = byStatus(col.k);
          return (
            <div key={col.k} className={cn("border rounded-xl p-3 min-h-[180px]",col.c)}>
              <div className="text-xs font-semibold text-slate-600 mb-1">{col.l}</div>
              <div className="text-lg font-bold text-slate-700 mb-2">{items.length}</div>
              <div className="space-y-1.5">
                {items.map(j=>(
                  <div key={j.id} className="bg-white/80 rounded-lg p-2 text-xs shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={()=>setSelectedId(j.id===selectedId?null:j.id)}>
                    <div className="font-medium text-slate-700 truncate">{j.company}</div>
                    <div className="text-slate-400 truncate">{j.title}</div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="font-bold text-slate-600">{j.composite_score}</span>
                      <span className="text-slate-400">{j.decision}</span>
                    </div>
                    {j.id===selectedId && (
                      <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-1">
                        {COLS.filter(c=>c.k!==col.k).map(c=>(
                          <button key={c.k} onClick={(e)=>{e.stopPropagation();moveJob(j.id,c.k);setSelectedId(null);}} className="text-xs px-1.5 py-0.5 bg-slate-100 rounded hover:bg-slate-200">→{c.l.slice(0,2)}</button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-slate-400 text-center">点击卡片展开，可拖拽移动状态（本地演示）</p>
    </div>
  );
}
