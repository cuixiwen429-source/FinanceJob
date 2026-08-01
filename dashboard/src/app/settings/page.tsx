"use client";

import { Settings, Key, Mail, Sliders, Shield } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-slate-800">⚙️ 设置</h1>

      {/* AI */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Key className="w-4 h-4 text-blue-500" />
          <h3 className="text-sm font-semibold text-slate-700">AI 接口</h3>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-slate-400">Provider:</span> DeepSeek</div>
          <div><span className="text-slate-400">Model:</span> deepseek-chat</div>
          <div className="col-span-2"><span className="text-slate-400">API Key:</span> ********</div>
        </div>
      </div>

      {/* Email */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Mail className="w-4 h-4 text-emerald-500" />
          <h3 className="text-sm font-semibold text-slate-700">邮件投递</h3>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-slate-400">Provider:</span> 163邮箱</div>
          <div><span className="text-slate-400">速率:</span> 10封/分钟</div>
          <div><span className="text-slate-400">日限额:</span> 400封</div>
          <div><span className="text-slate-400">定时:</span> 工作日 8:30</div>
        </div>
      </div>

      {/* Scoring */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Sliders className="w-4 h-4 text-purple-500" />
          <h3 className="text-sm font-semibold text-slate-700">评分阈值</h3>
        </div>
        <div className="space-y-3">
          {[
            { label: "🟢 强烈推荐", value: "≥ 75分", desc: "自动简历改写 + 优先自动投递" },
            { label: "🔵 推荐投递", value: "60 - 74分", desc: "自动简历改写 + 自动投递" },
            { label: "🟡 可投递", value: "45 - 59分", desc: "简历改写 + .eml 草稿人工审核" },
            { label: "⚪ 建议跳过", value: "< 45分", desc: "归档，7天自动清理" },
          ].map((t) => (
            <div key={t.label} className="flex items-center justify-between p-2 bg-slate-50 rounded">
              <div>
                <span className="text-sm font-medium text-slate-700">{t.label}</span>
                <p className="text-xs text-slate-400">{t.desc}</p>
              </div>
              <span className="text-sm font-bold text-slate-600">{t.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Blacklist */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-4 h-4 text-rose-500" />
          <h3 className="text-sm font-semibold text-slate-700">黑名单</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {["外包", "外派", "单休", "大小周", "996", "销售", "客服", "催收", "保险代理", "管培生"].map(
            (kw) => (
              <span key={kw} className="text-xs bg-rose-50 text-rose-600 px-2 py-1 rounded-full">
                🚫 {kw}
              </span>
            )
          )}
        </div>
      </div>
    </div>
  );
}
