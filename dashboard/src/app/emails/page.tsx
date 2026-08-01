"use client";

import { useEffect, useState } from "react";
import {
  Mail, Send, FileText, CheckCircle, XCircle, Clock, Link, Shield,
  RefreshCw, Settings, LogIn, AlertTriangle, Trash2, Copy, ExternalLink,
} from "lucide-react";
import { cn, API_BASE as API } from "@/lib/api";


// ── Types ──
interface EmailConfig {
  address: string; smtp: string; port: number; provider: string; connected: boolean;
  auth_code_set: boolean; daily_limit: number; rate_per_min: number;
}
interface Job {
  id: string; company: string; title: string; composite_score: number;
  decision: string; recruiter_email: string; tailored_resume_path: string; status: string;
}
interface EmailLog {
  id: number; job_id: string; recipient_email: string; subject: string;
  status: string; sent_at: string | null; error_message: string;
}

// ── Page ──
export default function EmailsPage() {
  const [tab, setTab] = useState<"connect" | "queue" | "history">("connect");
  const [config, setConfig] = useState<EmailConfig>({
    address: "", smtp: "smtp.qq.com", port: 465, provider: "qq",
    connected: false, auth_code_set: false, daily_limit: 400, rate_per_min: 10,
  });
  const [inputEmail, setInputEmail] = useState("");
  const [inputAuthCode, setInputAuthCode] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const [pendingJobs, setPendingJobs] = useState<Job[]>([]);
  const [logs, setLogs] = useState<EmailLog[]>([]);
  const [sending, setSending] = useState<string | null>(null);
  const [sendResults, setSendResults] = useState<Record<string, { ok: boolean; msg: string }>>({});

  // Load config on mount
  useEffect(() => {
    fetch(API + "/email-config")
      .then((r) => r.json())
      .then((c) => {
        setConfig(c);
        setInputEmail(c.address || "");
        if (c.auth_code_set) setInputAuthCode("••••••••••••••••");
      })
      .catch(() => {});
    loadData();
  }, []);

  const loadData = () => {
    Promise.all([
      fetch(API + "/jobs").then((r) => r.json()),
      fetch(API + "/email-logs").then((r) => r.json()),
    ])
      .then(([j, l]) => {
        setPendingJobs(
          (j || []).filter(
            (jj: Job) => jj.recruiter_email && !["applied", "replied", "interview", "offer", "rejected"].includes(jj.status)
          )
        );
        setLogs(l || []);
      })
      .catch(() => {});
  };

  // ── Connect ──
  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(API + "/test-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inputEmail, auth_code: inputAuthCode }),
      });
      const data = await res.json();
      setTestResult({ ok: data.success, msg: data.success ? "✅ 连接成功！QQ邮箱 SMTP 工作正常" : `❌ ${data.error}` });
      if (data.success) {
        setConfig({ ...config, address: inputEmail, connected: true, auth_code_set: true });
      }
    } catch (e: any) {
      setTestResult({ ok: false, msg: `❌ 连接失败: ${e.message}` });
    }
    setTesting(false);
  };

  const saveConfig = async () => {
    const res = await fetch(API + "/email-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: inputEmail, auth_code: inputAuthCode }),
    });
    const data = await res.json();
    if (data.success) {
      setConfig({ ...config, address: inputEmail, connected: true, auth_code_set: true });
      setTestResult({ ok: true, msg: "✅ 配置已保存" });
    }
  };

  // ── Send ──
  const sendOne = async (job: Job) => {
    setSending(job.id);
    try {
      const res = await fetch(API + "/send-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          to: job.recruiter_email,
          job_id: job.id,
          company: job.company,
          title: job.title,
          resume_path: job.tailored_resume_path,
        }),
      });
      const data = await res.json();
      setSendResults({ ...sendResults, [job.id]: { ok: data.success, msg: data.success ? "✅ 已发送" : data.error } });
      if (data.success) {
        setPendingJobs(pendingJobs.filter((j) => j.id !== job.id));
      }
    } catch (e: any) {
      setSendResults({ ...sendResults, [job.id]: { ok: false, msg: e.message } });
    }
    setSending(null);
    loadData();
  };

  const sendAll = async () => {
    for (const job of pendingJobs.slice(0, 5)) {
      await sendOne(job);
      await new Promise((r) => setTimeout(r, 2000)); // 2s interval for QQ rate limit
    }
    loadData();
  };

  // ── Stats ──
  const todaySent = logs.filter((l) => l.status === "sent" && l.sent_at?.startsWith(new Date().toISOString().slice(0, 10))).length;
  const queueCount = pendingJobs.filter((j) => j.recruiter_email).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">📧 邮箱管理中心</h1>
          <p className="text-sm text-slate-500 mt-1">
            {config.connected
              ? `${config.address} · ${config.provider.toUpperCase()} · 已连接`
              : "未连接 · 请先登录QQ邮箱"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadData} className="text-xs text-slate-500 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full">
            <RefreshCw className="w-3 h-3 inline mr-1" />刷新
          </button>
        </div>
      </div>

      {/* Status Bar */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "今日已发", value: todaySent, icon: Send, color: "text-emerald-600 bg-emerald-50" },
          { label: "待投递", value: queueCount, icon: Clock, color: "text-blue-600 bg-blue-50" },
          { label: "总记录", value: logs.length, icon: FileText, color: "text-slate-600 bg-slate-50" },
          { label: "连接状态", value: config.connected ? "已连接" : "未连接", icon: config.connected ? CheckCircle : XCircle, color: config.connected ? "text-emerald-600 bg-emerald-50" : "text-rose-600 bg-rose-50" },
        ].map((s) => (
          <div key={s.label} className="card p-4 flex items-center gap-3">
            <s.icon className={cn("w-8 h-8 p-1.5 rounded-lg", s.color)} />
            <div>
              <div className="text-xl font-bold text-slate-700">{s.value}</div>
              <div className="text-xs text-slate-400">{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1 w-fit">
        {[
          { k: "connect", l: "🔐 登录邮箱", icon: LogIn },
          { k: "queue", l: `📤 投递队列 (${queueCount})`, icon: Send },
          { k: "history", l: "📜 发送记录", icon: FileText },
        ].map((t) => (
          <button
            key={t.k}
            onClick={() => setTab(t.k as any)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg font-medium transition-all",
              tab === t.k ? "bg-white text-slate-800 shadow-sm" : "text-slate-500 hover:text-slate-700"
            )}
          >
            <t.icon className="w-4 h-4" /> {t.l}
          </button>
        ))}
      </div>

      {/* ── Tab: Connect ── */}
      {tab === "connect" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Login Form */}
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center">
                <Mail className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-slate-800">QQ邮箱登录</h3>
                <p className="text-xs text-slate-400">使用SMTP授权码连接</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-600">QQ邮箱地址</label>
                <div className="relative mt-1">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="email"
                    value={inputEmail}
                    onChange={(e) => setInputEmail(e.target.value)}
                    placeholder="your_qq_number@qq.com"
                    className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-slate-600">SMTP 授权码</label>
                <div className="relative mt-1">
                  <Shield className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="password"
                    value={inputAuthCode}
                    onChange={(e) => setInputAuthCode(e.target.value)}
                    placeholder="16位授权码（非QQ密码）"
                    className="w-full pl-9 pr-4 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent font-mono"
                  />
                </div>
              </div>

              {config.connected && (
                <div className="flex items-center gap-2 p-3 bg-emerald-50 rounded-xl text-sm text-emerald-700">
                  <CheckCircle className="w-4 h-4" /> 已连接 — {config.address}
                </div>
              )}

              {testResult && (
                <div className={cn("p-3 rounded-xl text-sm", testResult.ok ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700")}>
                  {testResult.msg}
                </div>
              )}

              <div className="flex items-center gap-3">
                <button
                  onClick={testConnection}
                  disabled={testing || !inputEmail || !inputAuthCode}
                  className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {testing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Link className="w-4 h-4" />}
                  {testing ? "测试中..." : "测试连接"}
                </button>
                <button
                  onClick={saveConfig}
                  disabled={!inputEmail || !inputAuthCode}
                  className="flex items-center gap-2 px-5 py-2.5 bg-slate-800 text-white text-sm font-medium rounded-xl hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Settings className="w-4 h-4" /> 保存配置
                </button>
              </div>
            </div>
          </div>

          {/* QQ 授权码获取指南 */}
          <div className="card p-6">
            <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
              📖 如何获取QQ邮箱授权码？
            </h3>
            <div className="space-y-3">
              {[
                { step: "1", text: "登录 QQ邮箱网页版", sub: "https://mail.qq.com" },
                { step: "2", text: "点击顶部「设置」→「账户」", sub: "" },
                { step: "3", text: "找到「POP3/IMAP/SMTP服务」", sub: "下滑到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」" },
                { step: "4", text: "开启「IMAP/SMTP服务」", sub: "如果未开启，点击开启（可能需要短信验证）" },
                { step: "5", text: "点击「生成授权码」", sub: "按提示发送短信后，会显示16位授权码" },
                { step: "6", text: "复制授权码粘贴到左侧", sub: "授权码仅显示一次，请立即保存" },
              ].map((s) => (
                <div key={s.step} className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl">
                  <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                    {s.step}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-slate-700">{s.text}</div>
                    {s.sub && <div className="text-xs text-slate-400 mt-0.5">{s.sub}</div>}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-3 bg-amber-50 rounded-xl text-xs text-amber-700">
              ⚠️ <strong>重要:</strong> 授权码 ≠ QQ密码。授权码是QQ邮箱为第三方客户端生成的专用密码，格式如: <code className="bg-amber-100 px-1 rounded">abcdefghijklmnop</code>
            </div>
            <a
              href="https://mail.qq.com"
              target="_blank"
              className="mt-4 flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800"
            >
              <ExternalLink className="w-3.5 h-3.5" /> 打开QQ邮箱网页版
            </a>
          </div>
        </div>
      )}

      {/* ── Tab: Queue ── */}
      {tab === "queue" && (
        <div className="space-y-4">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-700">
                📤 待投递队列 ({pendingJobs.filter((j) => j.recruiter_email).length} 个)
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">QQ邮箱限制: {config.rate_per_min}封/分钟 · 日限额{config.daily_limit}封</span>
                {queueCount > 0 && config.connected && (
                  <button
                    onClick={sendAll}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
                  >
                    <Send className="w-3 h-3" /> 批量发送 (前5封)
                  </button>
                )}
              </div>
            </div>

            {!config.connected && (
              <div className="flex items-center gap-2 p-4 bg-amber-50 rounded-xl text-sm text-amber-700 mb-4">
                <AlertTriangle className="w-4 h-4" /> 请先在「登录邮箱」页面连接QQ邮箱
              </div>
            )}

            <div className="space-y-2">
              {pendingJobs.filter((j) => j.recruiter_email).length === 0 ? (
                <div className="text-sm text-slate-400 text-center py-8">
                  🎉 所有有邮箱的岗位都已投递完毕
                </div>
              ) : (
                pendingJobs
                  .filter((j) => j.recruiter_email)
                  .sort((a, b) => b.composite_score - a.composite_score)
                  .map((job) => {
                    const result = sendResults[job.id];
                    const isSending = sending === job.id;
                    return (
                      <div
                        key={job.id}
                        className={cn(
                          "flex items-center gap-3 p-3 rounded-xl transition-all",
                          result
                            ? result.ok
                              ? "bg-emerald-50"
                              : "bg-rose-50"
                            : "bg-slate-50 hover:bg-slate-100"
                        )}
                      >
                        <Mail className={cn("w-4 h-4 shrink-0", result ? (result.ok ? "text-emerald-500" : "text-rose-500") : "text-slate-400")} />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-slate-700 truncate">
                            {job.company} — {job.title}
                          </div>
                          <div className="text-xs text-slate-400 flex items-center gap-2">
                            <span>{job.recruiter_email}</span>
                            <span className={cn("px-1.5 py-0.5 rounded text-xs font-medium",
                              job.decision === "强烈推荐" ? "text-emerald-600 bg-emerald-50" : "text-blue-600 bg-blue-50"
                            )}>
                              {job.decision}
                            </span>
                            <span className="font-bold">{job.composite_score}分</span>
                          </div>
                          {result && (
                            <div className={cn("text-xs mt-1", result.ok ? "text-emerald-600" : "text-rose-600")}>
                              {result.msg}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => sendOne(job)}
                          disabled={isSending || !config.connected}
                          className={cn(
                            "px-3 py-1.5 text-xs font-medium rounded-lg transition-all shrink-0",
                            config.connected
                              ? "bg-emerald-600 text-white hover:bg-emerald-700"
                              : "bg-slate-200 text-slate-500"
                          )}
                        >
                          {isSending ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : config.connected ? (
                            "📤 发送"
                          ) : (
                            "📝 草稿"
                          )}
                        </button>
                      </div>
                    );
                  })
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: History ── */}
      {tab === "history" && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">📜 发送记录 ({logs.length})</h3>
          {logs.length === 0 ? (
            <div className="text-sm text-slate-400 text-center py-8">暂无发送记录</div>
          ) : (
            <div className="space-y-1">
              {logs.map((log) => (
                <div key={log.id} className="flex items-center gap-3 p-2.5 text-sm rounded-lg hover:bg-slate-50">
                  <span>
                    {log.status === "sent" ? (
                      <CheckCircle className="w-4 h-4 text-emerald-500" />
                    ) : log.status === "failed" ? (
                      <XCircle className="w-4 h-4 text-rose-500" />
                    ) : (
                      <Clock className="w-4 h-4 text-amber-500" />
                    )}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="text-slate-700 truncate block">{log.subject || log.recipient_email}</span>
                    {log.error_message && (
                      <span className="text-xs text-rose-500">{log.error_message}</span>
                    )}
                  </span>
                  <span className="text-xs text-slate-400 w-20 text-right">
                    {log.status === "sent" ? log.sent_at?.slice(11, 16) || "" : log.status === "failed" ? "失败" : "草稿"}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div className="mt-4 p-3 bg-slate-50 rounded-xl text-xs text-slate-500">
            📊 QQ邮箱每日发送限额约 500 封 · 建议工作日 8:30-9:00 批量发送 · 同一邮箱7天内不重复发送
          </div>
        </div>
      )}
    </div>
  );
}
