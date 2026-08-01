"use client";

import { FileText, Download, Eye, RefreshCw } from "lucide-react";

export default function ResumePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">📝 简历管理</h1>

      {/* Base Resume */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">📄 基础简历</h3>
        <div className="flex items-center gap-4">
          <FileText className="w-10 h-10 text-blue-500" />
          <div className="flex-1">
            <div className="font-medium text-slate-700">resume_base.md</div>
            <div className="text-xs text-slate-400">Markdown · 华东师大金融硕士 · 2028届</div>
          </div>
          <button className="px-3 py-1.5 text-xs bg-slate-100 rounded-lg hover:bg-slate-200">
            <Eye className="w-3 h-3 inline mr-1" />预览
          </button>
        </div>
      </div>

      {/* Tailored Resumes */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-4">🎯 AI 定制简历</h3>
        <div className="space-y-3">
          {[
            { job: "中信证券·行研实习生", score: 85, date: "2026-07-27", path: "resume_1.pdf" },
            { job: "腾讯·投资分析实习生", score: 82, date: "2026-07-27", path: "resume_2.pdf" },
            { job: "中金公司·研究部实习生", score: 80, date: "2026-07-27", path: "resume_3.pdf" },
          ].map((r, i) => (
            <div key={i} className="flex items-center gap-4 p-3 bg-slate-50 rounded-lg">
              <div className="w-8 h-8 rounded bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-sm">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-700 truncate">{r.job}</div>
                <div className="text-xs text-slate-400">
                  Critic 评分: {r.score}/100 · {r.date}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">PDF</span>
                <button className="p-1.5 hover:bg-slate-200 rounded">
                  <Download className="w-3.5 h-3.5 text-slate-500" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Regenerate */}
      <div className="card p-5 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-700">🔄 批量生成</h3>
          <p className="text-xs text-slate-400 mt-1">对所有 "强烈推荐 + 推荐投递" 岗位生成定制简历</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white text-sm rounded-lg hover:bg-slate-700">
          <RefreshCw className="w-4 h-4" />
          python main.py tailor
        </button>
      </div>
    </div>
  );
}
