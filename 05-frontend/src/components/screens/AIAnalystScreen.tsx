"use client";

import { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Sparkles, Send } from 'lucide-react';
import api from '@/lib/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

export default function AIAnalystScreen() {
  const t = useTranslations('ai');
  const locale = useLocale();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await api.post<{ content?: string }>('/api/v1/chat', { message: userMsg, locale });
      setMessages(prev => [...prev, { role: 'assistant', text: res.content || t('notConnected') }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', text: t('notConnected') }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-160px)] max-w-3xl mx-auto">
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 pr-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400">
            <Sparkles size={32} className="mb-3 text-indigo-300" />
            <p className="text-sm">{t('disclaimer')}</p>
            <p className="text-xs mt-2">{t('placeholder')}</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0 mr-2 mt-0.5">
                <Sparkles size={14} />
              </div>
            )}
            <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
              m.role === 'user'
                ? 'bg-teal-600 text-white rounded-br-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
            }`}>
              {m.text}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0 mr-2 mt-0.5">
              <Sparkles size={14} />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-2.5 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }} />
              <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }} />
              <span className="text-xs text-gray-400 ml-2">{t('thinking')}</span>
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-gray-200 pt-4 flex items-center gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={t('placeholder')}
          className="flex-1 border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-teal-400"
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
          className="bg-teal-600 text-white p-2.5 rounded-lg hover:bg-teal-700 transition-colors shrink-0 disabled:opacity-50"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}

