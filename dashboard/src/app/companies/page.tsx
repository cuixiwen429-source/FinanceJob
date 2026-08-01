"use client";

import { useEffect, useState } from "react";
import { Building2, ExternalLink, Search } from "lucide-react";
import { API_BASE as API } from "@/lib/api";

interface Company { name:string; company_type:string; career_url:string; ats_type:string; is_active:number; }

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch(API+"/companies").then(r=>r.json()).then(setCompanies).catch(()=>{});
  }, []);

  const filtered = companies.filter(c=>!search||c.name.includes(search)||c.company_type.includes(search));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">🏢 公司库</h1>
        <button onClick={()=>fetch(API+"/companies").then(r=>r.json()).then(setCompanies)} className="text-xs text-slate-500 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full">🔄 刷新</button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"/>
        <input type="text" placeholder="搜索公司..." value={search} onChange={e=>setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"/>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b bg-slate-50">
            <th className="text-left px-4 py-3 font-semibold text-slate-600">公司</th>
            <th className="text-left px-4 py-3 font-semibold text-slate-600">类型</th>
            <th className="text-left px-4 py-3 font-semibold text-slate-600">ATS</th>
            <th className="text-right px-4 py-3 font-semibold text-slate-600">操作</th>
          </tr></thead>
          <tbody>
            {filtered.map(c=>(
              <tr key={c.name} className="border-b hover:bg-slate-50">
                <td className="px-4 py-3"><div className="flex items-center gap-2"><Building2 className="w-4 h-4 text-slate-400"/><span className="font-medium text-slate-700">{c.name}</span></div></td>
                <td className="px-4 py-3 text-slate-500">{c.company_type}</td>
                <td className="px-4 py-3"><span className="text-xs bg-slate-100 px-2 py-0.5 rounded">{c.ats_type}</span></td>
                <td className="px-4 py-3 text-right">
                  <a href={c.career_url.startsWith("http")?c.career_url:`https://${c.career_url}`} target="_blank" className="text-blue-500 hover:text-blue-700 text-xs"><ExternalLink className="w-3.5 h-3.5 inline"/> 官网</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400 text-center">共 {filtered.length} 家企业（120家金融企业官网库）</p>
    </div>
  );
}
