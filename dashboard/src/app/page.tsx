"use client";

import { useEffect, useState } from "react";
import { Briefcase, Target, Send, Trophy, TrendingUp, Star, Mail, Clock, MapPin } from "lucide-react";
import { cn } from "@/lib/api";

interface Stats { total:number; new:number; scored:number; applied:number; replied:number; interview:number; offer:number; strong_recommend:number; recommend:number; }
interface Job { id:string; company:string; title:string; composite_score:number; decision:string; rank:number; location:string; is_remote:boolean; }

const API = "/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats>({ total:0,new:0,scored:0,applied:0,replied:0,interview:0,offer:0,strong_recommend:0,recommend:0 });
  const [top, setTop] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(API+"/stats").then(r=>r.json()),
      fetch(API+"/jobs/high-priority").then(r=>r.json())
    ]).then(([s,j]) => { setStats(s); setTop(j.slice(0,6)); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const cards = [
    { label:"新发现", value:stats.new, icon:Clock, color:"text-purple-600 bg-purple-50" },
    { label:"已评分", value:stats.scored, icon:Target, color:"text-blue-600 bg-blue-50" },
    { label:"已投递", value:stats.applied, icon:Send, color:"text-emerald-600 bg-emerald-50" },
    { label:"面试中", value:stats.interview, icon:TrendingUp, color:"text-amber-600 bg-amber-50" },
    { label:"Offer", value:stats.offer, icon:Trophy, color:"text-rose-600 bg-rose-50" },
    { label:"强烈推荐", value:stats.strong_recommend, icon:Star, color:"text-emerald-600 bg-emerald-50" },
    { label:"推荐投递", value:stats.recommend, icon:Send, color:"text-blue-600 bg-blue-50" },
    { label:"已回复", value:stats.replied, icon:Mail, color:"text-indigo-600 bg-indigo-50" },
  ];

  if (loading) return <div className="flex items-center justify-center h-64 text-slate-400">加载中...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">📊 求职总览</h1>
          <p className="text-sm text-slate-500 mt-1">2028届 · 崔曦文 · 华东师范大学金融硕士 · {stats.total}个岗位</p>
        </div>
        <button onClick={() => {Promise.all([fetch(API+"/stats").then(r=>r.json()),fetch(API+"/jobs/high-priority").then(r=>r.json())]).then(([s,j])=>{setStats(s);setTop(j.slice(0,6));})}}
                className="text-xs text-slate-500 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full transition-colors">
          🔄 刷新数据
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map(c => (
          <div key={c.label} className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500 font-medium">{c.label}</span>
              <c.icon className={cn("w-4 h-4 p-0.5 rounded", c.color)} />
            </div>
            <div className="text-2xl font-bold text-slate-700">{c.value}</div>
          </div>
        ))}
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-4">📋 投递管道</h3>
        <div className="flex items-center gap-0 text-center">
          {[{l:"新发现",v:stats.new,c:"bg-purple-500"},{l:"已评分",v:stats.scored,c:"bg-blue-500"},{l:"已投递",v:stats.applied,c:"bg-emerald-500"},{l:"已回复",v:stats.replied,c:"bg-amber-500"},{l:"面试中",v:stats.interview,c:"bg-orange-500"},{l:"Offer",v:stats.offer,c:"bg-rose-500"}].map((s,i)=>(
            <div key={s.l} className="flex-1"><div className={cn("w-full h-2 rounded mb-2 opacity-20",s.c)} style={{opacity:0.2+i*0.12}}/><div className="text-xl font-bold text-slate-700">{s.v}</div><div className="text-xs text-slate-400 mt-1">{s.l}</div></div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">🎯 决策分布</h3>
          {[{l:"🟢 强烈推荐",v:stats.strong_recommend,c:"bg-emerald-500"},{l:"🔵 推荐投递",v:stats.recommend,c:"bg-blue-500"},{l:"🟡 可投递",v:Math.max(0,stats.scored-stats.strong_recommend-stats.recommend),c:"bg-amber-500"}].map(d=>(
            <div key={d.l} className="mb-3"><div className="flex justify-between text-sm mb-1"><span>{d.l}</span><span className="font-semibold">{d.v}</span></div><div className="progress-bar"><div className={cn("progress-fill",d.c)} style={{width:stats.scored>0?`${(d.v/stats.scored)*100}%`:"0%"}}/></div></div>
          ))}
        </div>

        <div className="card p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">🏆 高分岗位 TOP 6</h3>
          <div className="space-y-2">
            {top.map((j,i) => (
              <div key={j.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-50 transition-colors">
                <span className={cn("text-lg font-bold w-6",i<3?"text-amber-500":"text-slate-400")}>{j.rank||i+1}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-700 truncate">{j.company}</div>
                  <div className="text-xs text-slate-400 truncate">{j.title}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium",
                    j.decision==="强烈推荐"?"text-emerald-600 bg-emerald-50":"text-blue-600 bg-blue-50")}>{j.decision}</span>
                  <span className="text-sm text-slate-400 flex items-center gap-0.5"><MapPin className="w-3 h-3"/>{j.is_remote?"🌐远程":j.location}</span>
                  <span className="text-lg font-bold text-slate-700 w-10 text-right">{j.composite_score}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card p-5 flex items-center gap-3 flex-wrap">
        <span className="text-sm text-slate-500">⚡ 终端命令:</span>
        {["python3 main.py scan","python3 main.py score","python3 main.py tailor","python3 main.py send","python3 main.py status"].map(c=>(
          <code key={c} className="text-xs bg-slate-800 text-emerald-400 px-3 py-1.5 rounded-md font-mono cursor-pointer hover:bg-slate-700" onClick={()=>navigator.clipboard?.writeText(c)}>{c}</code>
        ))}
      </div>
    </div>
  );
}
