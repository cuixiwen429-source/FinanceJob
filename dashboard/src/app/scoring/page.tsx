"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from "recharts";
import { cn, API_BASE as API } from "@/lib/api";

interface Job { id:string;company:string;title:string;job_match_score:number;industry_match_score:number;salary_score:number;career_dev_score:number;composite_score:number;rank:number;decision:string; }


export default function ScoringPage() {
  const [jobs, setJobs] = useState<Job[]>([]);

  useEffect(() => {
    fetch(API+"/jobs/scored").then(r=>r.json()).then(j => setJobs(j.slice(0,8))).catch(()=>{});
  }, []);

  const chartData = jobs.map(j=>({name:j.company.length>5?j.company.slice(0,5)+"…":j.company,岗位匹配:j.job_match_score,行业匹配:j.industry_match_score,薪资:j.salary_score,发展:j.career_dev_score}));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">📊 评分对比</h1>
        <button onClick={()=>fetch(API+"/jobs/scored").then(r=>r.json()).then(j=>setJobs(j.slice(0,8)))} className="text-xs text-slate-500 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full">🔄 刷新</button>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-4">四维评分横向对比</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical" margin={{left:60}}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false}/>
            <XAxis type="number" domain={[0,100]} tick={{fontSize:12}}/>
            <YAxis type="category" dataKey="name" tick={{fontSize:11}} width={60}/>
            <Tooltip/>
            <Bar dataKey="岗位匹配" fill="#3b82f6" stackId="a"/>
            <Bar dataKey="行业匹配" fill="#10b981" stackId="a"/>
            <Bar dataKey="薪资" fill="#f59e0b" stackId="a"/>
            <Bar dataKey="发展" fill="#8b5cf6" stackId="a"/>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">🎯 雷达图</h3>
          {jobs.length>=2 && (
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={[{dim:"岗位匹配",[jobs[0]?.company]:jobs[0]?.job_match_score,[jobs[1]?.company]:jobs[1]?.job_match_score},{dim:"行业匹配",[jobs[0]?.company]:jobs[0]?.industry_match_score,[jobs[1]?.company]:jobs[1]?.industry_match_score},{dim:"薪资",[jobs[0]?.company]:jobs[0]?.salary_score,[jobs[1]?.company]:jobs[1]?.salary_score},{dim:"发展",[jobs[0]?.company]:jobs[0]?.career_dev_score,[jobs[1]?.company]:jobs[1]?.career_dev_score}]}>
                <PolarGrid/><PolarAngleAxis dataKey="dim" tick={{fontSize:11}}/>
                <PolarRadiusAxis domain={[0,100]} tick={{fontSize:10}}/>
                <Radar name={jobs[0]?.company||""} dataKey={jobs[0]?.company||""} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2}/>
                <Radar name={jobs[1]?.company||""} dataKey={jobs[1]?.company||""} stroke="#10b981" fill="#10b981" fillOpacity={0.2}/>
              </RadarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">🏆 综合排名</h3>
          {jobs.map((j,i)=>(
            <div key={j.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50">
              <span className={cn("text-lg font-bold w-6",i<3?"text-amber-500":"text-slate-400")}>{j.rank||i+1}</span>
              <div className="flex-1 min-w-0"><div className="text-sm font-medium text-slate-700 truncate">{j.company}</div><div className="text-xs text-slate-400">{j.title}</div></div>
              <span className={cn("text-xs px-2 py-0.5 rounded-full",j.decision==="强烈推荐"?"text-emerald-600 bg-emerald-50":"text-blue-600 bg-blue-50")}>{j.decision}</span>
              <span className="text-lg font-bold text-slate-700 w-10 text-right">{j.composite_score}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-4">⚖️ 评分公式</h3>
        <div className="bg-slate-800 text-emerald-400 rounded-lg p-4 font-mono text-sm">Composite = JMS×0.40 + IMS×0.25 + SS×0.15 + CDS×0.20 + Adjustments</div>
        <div className="grid grid-cols-4 gap-3 mt-4">
          {[{l:"岗位匹配(JMS)",w:"40%",c:"text-blue-600"},{l:"行业匹配(IMS)",w:"25%",c:"text-emerald-600"},{l:"薪资评分(SS)",w:"15%",c:"text-amber-600"},{l:"发展前景(CDS)",w:"20%",c:"text-purple-600"}].map(d=>(
            <div key={d.l} className="text-center p-3 bg-slate-50 rounded-lg"><div className="text-xs text-slate-400">{d.l}</div><div className={cn("text-lg font-bold",d.c)}>{d.w}</div></div>
          ))}
        </div>
      </div>
    </div>
  );
}
