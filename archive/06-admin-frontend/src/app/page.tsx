"use client";

import React, { useState } from 'react';
import {
  ShieldCheck, AlertTriangle, ShieldAlert, Info, Clock, Check, X, Pencil,
  ArrowLeft, FileText, Send
} from 'lucide-react';

// Using types defined in the system
type RiskLevel = 'low' | 'medium' | 'high';
type PostStatus = 'draft' | 'pending_review' | 'approved' | 'rejected' | 'expired' | 'published';

interface AIGeneratedPost {
  id: string;
  title: string;
  content: string;
  recommendation: string | null;
  vertical: string | null;
  priority_score: number | null;
  risk_level: RiskLevel | null;
  status: PostStatus;
  pattern_id: string | null;
  manual_source_text: string | null;
  submitted_by_user_id: string | null;
  moderated_by: string | null;
  created_at: string;
}

const pendingPosts: AIGeneratedPost[] = [
  {
    id: 'p1', 
    title: 'Meta усилила блокировки Gambling-аккаунтов, EU', 
    content: 'Скриншот из чата "Арбитраж 18+", переслал аналитик',
    vertical: 'Gambling · EU',
    risk_level: 'high', 
    priority_score: 92, 
    recommendation: 'Сократить экспозицию в Gambling EU на 15-20% до стабилизации',
    status: 'pending_review',
    pattern_id: null,
    manual_source_text: 'Скриншот из чата "Арбитраж 18+", переслал аналитик',
    submitted_by_user_id: 'analyst_ivan',
    moderated_by: null,
    created_at: new Date(Date.now() - 61 * 3600000).toISOString(),
  },
  {
    id: 'p2', 
    title: 'TikTok обновил алгоритм модерации для Crypto-креативов', 
    content: 'Ссылка: t.me/cryptotraffic/44201',
    vertical: 'Crypto · Global',
    risk_level: 'medium', 
    priority_score: 64, 
    recommendation: 'Протестировать новые форматы креативов перед масштабированием',
    status: 'pending_review',
    pattern_id: null,
    manual_source_text: 'Ссылка: t.me/cryptotraffic/44201',
    submitted_by_user_id: 'analyst_ivan',
    moderated_by: null,
    created_at: new Date(Date.now() - 12 * 3600000).toISOString(),
  },
  {
    id: 'p3', 
    title: 'Рост конкуренции в Nutra LATAM от новых команд', 
    content: 'Пост на форуме, переслан вручную',
    vertical: 'Nutra · LATAM',
    risk_level: 'low', 
    priority_score: 31, 
    recommendation: 'Мониторить CPA по офферу, пока не требует действий',
    status: 'pending_review',
    pattern_id: null,
    manual_source_text: 'Пост на форуме, переслан вручную',
    submitted_by_user_id: 'analyst_sveta',
    moderated_by: null,
    created_at: new Date(Date.now() - 3 * 3600000).toISOString(),
  },
];

const historyPosts: AIGeneratedPost[] = [
  { 
    id: 'h1', 
    title: 'Google Ads ужесточил политику для Crypto EU', 
    content: '',
    vertical: 'Crypto · EU', 
    risk_level: 'high', 
    priority_score: 80,
    recommendation: '',
    status: 'published', // approved = published
    pattern_id: null,
    manual_source_text: '',
    submitted_by_user_id: '',
    moderated_by: 'analyst_sveta',
    created_at: new Date().toISOString(),
  },
  { 
    id: 'h2', 
    title: 'Слух о новых лимитах на вывод в одной из платёжек', 
    content: '',
    vertical: 'Gambling · Global', 
    risk_level: 'medium', 
    priority_score: 50,
    recommendation: '',
    status: 'rejected', 
    pattern_id: null,
    manual_source_text: '',
    submitted_by_user_id: '',
    moderated_by: 'analyst_ivan',
    created_at: new Date().toISOString(),
  },
];

const riskStyles = { high: 'bg-red-50 text-red-700 border-red-200', medium: 'bg-amber-50 text-amber-700 border-amber-200', low: 'bg-green-50 text-green-700 border-green-200' };
const riskIcon = { high: ShieldAlert, medium: AlertTriangle, low: Info };

const SlaTimer = ({ createdAt }: { createdAt: string }) => {
  const hoursAgo = Math.floor((Date.now() - new Date(createdAt).getTime()) / 3600000);
  const remaining = 72 - hoursAgo;
  const urgent = remaining <= 24;
  const critical = remaining <= 6;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${critical ? 'text-red-700' : urgent ? 'text-amber-700' : 'text-gray-500'}`}>
      <Clock size={12} />
      {remaining > 0 ? `осталось ${remaining} ч до авто-протухания` : 'просрочено'}
    </span>
  );
};

const QueueScreen = () => {
  const [tab, setTab] = useState('pending');
  const [selected, setSelected] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);

  if (selected) {
    const p = pendingPosts.find((x) => x.id === selected);
    if (!p) return null;
    const Icon = riskIcon[p.risk_level || 'low'];
    
    return (
      <div className="max-w-2xl mx-auto">
        <button onClick={() => setSelected(null)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-4">
          <ArrowLeft size={14} /> Назад к очереди
        </button>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 relative">
          <div className="flex items-center gap-2 mb-3">
            <div className={`w-8 h-8 rounded-full border flex items-center justify-center ${riskStyles[p.risk_level || 'low']}`}><Icon size={15} /></div>
            <span className={`text-xs font-bold uppercase tracking-wide ${p.risk_level === 'high' ? 'text-red-700' : p.risk_level === 'medium' ? 'text-amber-700' : 'text-green-700'}`}>{p.risk_level} risk</span>
            <span className="text-xs text-gray-400">· {p.vertical} · priority {p.priority_score}</span>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">{p.title}</h2>
          <div className="text-sm text-gray-600 mb-4 leading-relaxed">
            <div className="text-xs text-gray-400 mb-1">
              {p.pattern_id ? 'Сгенерировано автоматически (Stage 4)' : 'Источник (внесён вручную)'}
            </div>
            {p.manual_source_text || p.content} — от {p.submitted_by_user_id || 'AI'}
          </div>
          <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4 mb-5">
            <div className="text-xs text-indigo-600 font-semibold mb-1">Рекомендация AI</div>
            <p className="text-sm text-gray-800">{p.recommendation}</p>
          </div>
          <SlaTimer createdAt={p.created_at} />
          <div className="flex items-center gap-2 mt-5 pt-5 border-t border-gray-100">
            <button className="flex items-center gap-1.5 bg-teal-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-teal-700"><Check size={15} />Одобрить</button>
            <button className="flex items-center gap-1.5 bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:border-gray-300"><Pencil size={15} />Править и одобрить</button>
            <button onClick={() => setShowRejectModal(true)} className="flex items-center gap-1.5 bg-white border border-red-200 text-red-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-50 ml-auto"><X size={15} />Отклонить</button>
          </div>

          {showRejectModal && (
            <div className="absolute top-0 left-0 right-0 bottom-0 bg-white/90 backdrop-blur-sm rounded-xl p-6 flex flex-col justify-center border border-gray-200">
              <h3 className="text-lg font-semibold mb-2">Укажите причину отклонения</h3>
              <textarea 
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="w-full border border-gray-300 rounded-md p-3 text-sm focus:outline-none focus:border-red-500 mb-4"
                rows={3}
                placeholder="Например: Неактуально для нашей модели закупки..."
              />
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowRejectModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-md">Отмена</button>
                <button 
                  disabled={!rejectReason.trim()} 
                  className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-md"
                >
                  Подтвердить отклонение
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-1 mb-5 border-b border-gray-200">
        <button onClick={() => setTab('pending')} className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === 'pending' ? 'border-teal-600 text-teal-700' : 'border-transparent text-gray-500'}`}>
          На проверке ({pendingPosts.length})
        </button>
        <button onClick={() => setTab('history')} className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === 'history' ? 'border-teal-600 text-teal-700' : 'border-transparent text-gray-500'}`}>
          История
        </button>
      </div>

      {tab === 'pending' && (
        <div className="space-y-2">
          {pendingPosts.map((p) => {
            const Icon = riskIcon[p.risk_level || 'low'];
            return (
              <button key={p.id} onClick={() => setSelected(p.id)} className="w-full text-left flex items-start gap-3 p-4 bg-white rounded-xl border border-gray-200 shadow-sm hover:border-teal-300 transition-colors">
                <div className={`w-8 h-8 rounded-full border flex items-center justify-center shrink-0 mt-0.5 ${riskStyles[p.risk_level || 'low']}`}><Icon size={15} /></div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`text-[10px] uppercase font-bold tracking-wide ${p.risk_level === 'high' ? 'text-red-700' : p.risk_level === 'medium' ? 'text-amber-700' : 'text-green-700'}`}>{p.risk_level} risk</span>
                    <span className="text-[10px] text-gray-400">· {p.vertical}</span>
                    <SlaTimer createdAt={p.created_at} />
                  </div>
                  <p className="text-sm font-medium text-gray-900">{p.title}</p>
                </div>
                <div className="text-right shrink-0"><div className="text-xs text-gray-400">priority</div><div className="text-sm font-semibold text-gray-700">{p.priority_score}</div></div>
              </button>
            );
          })}
        </div>
      )}

      {tab === 'history' && (
        <div className="space-y-2">
          {historyPosts.map((p) => (
            <div key={p.id} className="flex items-center gap-3 p-4 bg-white rounded-xl border border-gray-200 shadow-sm">
              <div className={`w-8 h-8 rounded-full border flex items-center justify-center shrink-0 ${riskStyles[p.risk_level || 'low']}`}>
                {p.status === 'published' ? <ShieldCheck size={15} className="text-green-600" /> : <X size={15} className="text-red-600" />}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">{p.title}</p>
                <p className="text-xs text-gray-400">{p.vertical} · {p.status === 'published' ? 'Одобрено' : 'Отклонено'} — {p.moderated_by}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const SourceEntryScreen = () => {
  const [text, setText] = useState('');
  const [vertical, setVertical] = useState('general');
  return (
    <div className="max-w-2xl mx-auto bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center gap-2 mb-1 text-indigo-600 font-semibold text-sm"><FileText size={16} />Новый источник</div>
      <p className="text-xs text-gray-400 mb-5">AI сформирует черновик поста — он попадёт в очередь на проверку, не будет опубликован автоматически.</p>
      <label className="block text-xs text-gray-500 mb-1.5">Вертикаль</label>
      <select value={vertical} onChange={(e) => setVertical(e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:border-teal-400">
        <option value="general">Общерыночная тема (видно всем)</option>
        <option value="gambling">Gambling</option>
        <option value="crypto">Crypto</option>
        <option value="nutra">Nutra</option>
      </select>
      <label className="block text-xs text-gray-500 mb-1.5">Текст источника, ссылка или описание скриншота</label>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={6}
        placeholder="Вставьте текст сообщения, ссылку на новость, или опишите, что видно на скриншоте..."
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-teal-400 mb-4" />
      <button className="flex items-center gap-1.5 bg-teal-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-teal-700">
        <Send size={14} />Сформировать черновик
      </button>
    </div>
  );
};

export default function App() {
  const [view, setView] = useState('queue');
  return (
    <div className="min-h-screen bg-gray-50 font-sans text-sm">
      <header className="h-16 border-b border-gray-200 bg-gray-900 px-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 bg-teal-500 rounded-md" />
          <span className="font-semibold text-white">FinanceIntel — Internal</span>
          <span className="text-[10px] uppercase tracking-wide bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full ml-1">Moderation tool</span>
        </div>
        <div className="w-7 h-7 rounded-full bg-teal-600 text-white flex items-center justify-center text-xs font-semibold">AI</div>
      </header>
      <div className="max-w-5xl mx-auto px-8 py-6">
        <div className="flex items-center gap-1 mb-6">
          <button onClick={() => setView('queue')} className={`px-3 py-1.5 rounded-md text-sm font-medium ${view === 'queue' ? 'bg-teal-50 text-teal-700' : 'text-gray-500 hover:bg-gray-100'}`}>Очередь модерации</button>
          <button onClick={() => setView('source')} className={`px-3 py-1.5 rounded-md text-sm font-medium ${view === 'source' ? 'bg-teal-50 text-teal-700' : 'text-gray-500 hover:bg-gray-100'}`}>Новый источник</button>
        </div>
        {view === 'queue' ? <QueueScreen /> : <SourceEntryScreen />}
      </div>
    </div>
  );
}
