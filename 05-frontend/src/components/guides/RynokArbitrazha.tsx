"use client";

import React from 'react';
import { Card } from '@/components/ui/Card';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

const growthData = [
  { year: '2024', value: 13 },
  { year: '2025', value: 16 },
  { year: '2026', value: 20 },
  { year: '2027', value: 26 },
  { year: '2028', value: 30 },
  { year: '2029', value: 34 },
  { year: '2030', value: 38 },
];

export default function RynokArbitrazha() {
  return (
    <article className="pb-24">
      {/* HERO BLOCK - FULL BLEED IN (FULLWIDTH) LAYOUT */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-800 text-slate-100 pt-16 pb-12 px-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-teal-300 font-bold mb-4">
            <div className="w-2 h-2 rounded-full bg-teal-300" />
            FinanceIntel · справочный материал 02
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold leading-tight tracking-tight mb-6 max-w-3xl">
            Рынок на $24.7 млрд, который до сих пор считает деньги в Excel
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mb-10">
            Performance-маркетинг и арбитраж трафика — один из немногих крупных рынков, где нет ни одного финансового инструмента, заточенного именно под него. Вот из чего состоит этот рынок и почему это окно возможностей.
          </p>

          {/* HERO CHART (Stacked Bar) */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-sm">
            <div className="mb-6">
              <h3 className="text-base font-bold text-white m-0">Из чего состоит рынок performance-маркетинга</h3>
              <p className="text-sm text-slate-400 mt-1">Доля affiliate-бюджета по вертикалям, 2026</p>
            </div>
            
            <div className="w-full h-12 flex rounded-md overflow-hidden mb-6">
              <div style={{ width: '38%' }} className="bg-teal-700 h-full"></div>
              <div style={{ width: '22%' }} className="bg-emerald-600 h-full"></div>
              <div style={{ width: '15%' }} className="bg-teal-300 h-full"></div>
              <div style={{ width: '9%' }} className="bg-indigo-600 h-full"></div>
              <div style={{ width: '4%' }} className="bg-amber-600 h-full"></div>
              <div style={{ width: '12%' }} className="bg-slate-700 h-full"></div>
            </div>

            <div className="flex flex-wrap gap-x-6 gap-y-3 text-xs text-slate-300">
              <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-sm bg-teal-700" />eCommerce 38%</span>
              <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-sm bg-emerald-600" />iGaming 22%</span>
              <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-sm bg-teal-300" />Финансы 15%</span>
              <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-sm bg-indigo-600" />B2B SaaS 9%</span>
              <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-sm bg-amber-600" />Crypto 4%</span>
              <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-sm bg-slate-700" />Другое 12%</span>
            </div>
          </div>
        </div>
      </div>

      {/* ARTICLE CONTENT */}
      <div className="max-w-4xl mx-auto px-8 pt-12 flex gap-16">
        
        {/* TOC - hidden on mobile */}
        <nav className="hidden lg:block w-52 shrink-0 sticky top-8 self-start text-sm">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-4">Содержание</div>
          <div className="flex flex-col gap-1 border-l-2 border-slate-200">
            {['Размер рынка', 'Вертикали: пропорции', 'Gambling крупным планом', 'Crypto крупным планом', 'Nutra крупным планом', 'Кто на этом рынке', 'Риски рынка', 'Уже платят за инструменты', 'Что это значит для рынка (TAM)'].map((title, i) => (
              <a key={i} href={`#s${i+1}`} className="text-slate-600 hover:text-teal-700 hover:border-teal-700 border-l-2 -ml-[2px] border-transparent py-1.5 pl-4 transition-colors">
                0{i+1} · {title}
              </a>
            ))}
          </div>
        </nav>

        {/* MAIN TEXT */}
        <div className="flex-1 text-slate-700 space-y-16">
          
          <section id="s1" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">01</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Размер рынка</h2>
            <p className="mb-4">
              Важно сразу разделить два разных числа, которые часто путают. Одно — сам <strong>affiliate-канал</strong> (сколько рекламодатели платят партнёрам за результат): $19.6 млрд в 2025, $24.7 млрд в 2026 (+26% год к году). Второе — <strong>софтверный слой</strong> вокруг него (трекеры, платформы управления партнёрками, антифрод): $22.58 млрд в 2025, $23.84 млрд в 2026, с прогнозом $35.7 млрд к 2033 году. FinanceIntel относится ко второй категории — но растёт вместе с первой, потому что чем больше денег проходит через канал, тем больше нужен контроль над ними.
            </p>
            
            <Card className="my-6 p-6">
              <div className="mb-4">
                <h4 className="text-base font-bold text-slate-900 m-0">Траектория роста affiliate-канала</h4>
                <p className="text-sm text-slate-500 m-0">Млрд $, консенсус нескольких источников (диапазон между отчётами — 10-15%)</p>
              </div>
              
              <div className="h-[260px] w-full text-xs mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={growthData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                    <XAxis dataKey="year" stroke="#64748B" tick={{fill: '#64748B'}} axisLine={false} tickLine={false} />
                    <YAxis stroke="#64748B" tick={{fill: '#64748B'}} axisLine={false} tickLine={false} tickFormatter={(val) => `$${val}B`} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#fff', border: '1px solid #E2E8F0', borderRadius: '8px', color: '#1E293B', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      itemStyle={{ color: '#1E293B' }}
                      formatter={(val) => [`$${val}B`, 'Объём рынка']}
                    />
                    <Area type="monotone" dataKey="value" stroke="#0E9F6E" strokeWidth={2.5} fill="rgba(14,159,110,0.12)" dot={{ r: 3.5, fill: '#0E9F6E', strokeWidth: 0 }} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </section>

          <section id="s2" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">02</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Вертикали: пропорции рынка</h2>
            <p className="mb-4">
              eCommerce формально крупнейшая доля — но это не значит, что там больше всего денег на одного участника. iGaming (22%) при вдвое меньшей доле рынка генерирует сопоставимый или больший заработок на одного активного байера, потому что выплаты на порядок выше, а конкуренция концентрированнее. То же с Crypto — всего 4% рынка, но именно там средний чек и volatility выше всего.
            </p>

            <div className="overflow-x-auto my-6 rounded-xl border border-slate-200 shadow-sm">
              <table className="w-full text-sm text-left bg-white">
                <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Вертикаль</th>
                    <th className="px-4 py-3">Доля affiliate-бюджета</th>
                    <th className="px-4 py-3">Характер выплат</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">eCommerce</td><td className="px-4 py-3">38%</td><td className="px-4 py-3">Низкий чек, высокий объём, RevShare редко</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">iGaming</td><td className="px-4 py-3">22%</td><td className="px-4 py-3">Высокий чек, RevShare с LTV на месяцы-годы</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Финансовые услуги</td><td className="px-4 py-3">15%</td><td className="px-4 py-3">Средний-высокий чек, строгий комплаенс</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">B2B SaaS</td><td className="px-4 py-3">9%</td><td className="px-4 py-3">Длинный цикл, низкая частота конверсий</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Crypto / prop-trading</td><td className="px-4 py-3">4%</td><td className="px-4 py-3">Высокая волатильность чека и объёма</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Прочее (Nutra, Dating, Sweeps)</td><td className="px-4 py-3">12%</td><td className="px-4 py-3">Высокий scrub, короткий цикл жизни оффера</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section id="s3" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">03</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Gambling крупным планом</h2>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
              {[
                { v: '$107–130 млрд', l: 'Весь рынок онлайн-гемблинга, 2026' },
                { v: '~$5–7 млрд', l: 'Из них — на affiliate-привлечение' },
                { v: '8 000+', l: 'Лицензированных казино/букмекеров конкурируют за трафик' },
                { v: '30%+', l: 'Всех транзакций в iGaming приходят через affiliate-канал' }
              ].map((s, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                  <div className="text-xl font-extrabold text-slate-900">{s.v}</div>
                  <div className="text-xs text-slate-500 mt-1">{s.l}</div>
                </div>
              ))}
            </div>
            
            <p>
              Это единственная крупная вертикаль, где RevShare — норма, а не исключение: байер получает процент от депозитов игрока месяцами и годами после первой конверсии. Именно поэтому атрибуция «какая кампания в итоге привела этого игрока» здесь дороже ошибиться, чем где-либо ещё.
            </p>
          </section>

          <section id="s4" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">04</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Crypto крупным планом</h2>
            <p className="mb-4">
              Самая маленькая по доле (4%) и самая нестабильная по объёму из трёх ключевых вертикалей — бюджеты синхронизированы с рыночными циклами крипторынка сильнее, чем в любой другой нише: ралли — приток новых офферов и бюджетов, спад — резкое сокращение. Для команды это означает, что финансовое планирование здесь требует более короткого горизонта и более консервативного Cash Runway, чем в Gambling или Nutra, где спрос стабильнее по календарю.
            </p>
          </section>

          <section id="s5" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">05</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Nutra крупным планом</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-6">
              {[
                { v: '$500 млрд+', l: 'Весь рынок нутрицевтики (товарный, не только affiliate)' },
                { v: '$30–150', l: 'Типичная CPA-выплата за продажу/trial' },
                { v: '10–30%', l: 'Типичный scrub на заявленных конверсиях' }
              ].map((s, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                  <div className="text-xl font-extrabold text-slate-900">{s.v}</div>
                  <div className="text-xs text-slate-500 mt-1">{s.l}</div>
                </div>
              ))}
            </div>
            
            <p>
              Товарный рынок под Nutra-офферами огромен сам по себе, но именно поэтому конкуренция байеров за один и тот же оффер особенно жёсткая — короткий цикл жизни связки и высокий scrub (см. предыдущую статью, раздел про кассовый разрыв) характерны именно для этой вертикали сильнее остальных.
            </p>
          </section>

          <section id="s6" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">06</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Кто на этом рынке</h2>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
              {[
                { v: '107 179', l: 'Компаний в индустрии Affiliate Networks' },
                { v: '12 млн+', l: 'Активных affiliate-маркетологов в мире' },
                { v: '$80.5 → $151 млрд', l: 'Рынок медиабаинга целиком, 2025 → 2035' },
                { v: 'Top 10% = 90%', l: 'Дохода индустрии концентрируется в узкой группе' }
              ].map((s, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                  <div className="text-xl font-extrabold text-slate-900">{s.v}</div>
                  <div className="text-xs text-slate-500 mt-1">{s.l}</div>
                </div>
              ))}
            </div>
            
            <p>
              Последняя цифра — самая важная для позиционирования продукта. Рынок огромен по количеству участников, но реальные деньги — у меньшинства серьёзных, масштабированных команд. Это не рынок для миллионов одиночек с $50 бюджетом — это рынок, где узкий слой профессиональных команд управляет подавляющей долей оборота, и именно этот слой — целевая аудитория инструмента вроде FinanceIntel, а не длинный хвост новичков.
            </p>
          </section>

          <section id="s7" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">07</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Риски рынка</h2>
            <div className="border-l-4 border-teal-600 bg-teal-50 rounded-r-xl p-5 my-6 text-teal-900 font-semibold">
              $3.4 млрд потеряно на невалидном трафике и фроде в 2025 году — 17.3% всего affiliate-бюджета индустрии.
            </div>
            <p>
              Это не абстрактная цифра «где-то у кого-то» — это прямой аналог того, что мы называли scrub/чарджбек в предыдущей статье, только в масштабе всей индустрии. Регуляторное давление (особенно в Gambling и Crypto) добавляет второй слой риска — правила площадок и юрисдикций меняются быстрее, чем команды успевают адаптироваться вручную, что и есть прямое обоснование для модуля Market Intelligence.
            </p>
          </section>

          <section id="s8" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">08</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Специализация инструментов — норма, а не исключение</h2>
            <p className="mb-4">
              В этой индустрии команда почти всегда уже пользуется целым стеком специализированных инструментов: трекером (Keitaro, Binom, Voluum и похожие — обычно от $100 до нескольких сотен долларов в месяц), антидетект-браузером, прокси, системой клоакинга. Это нормальная, ожидаемая статья расходов профессиональной команды, а не что-то необычное.
            </p>
            <p>
              Но у всех этих инструментов общее ограничение: каждый закрывает одну узкую задачу — трекинг кликов, управление аккаунтами, прохождение модерации. Ни один не считает деньги компании целиком: реальную прибыль, зарплаты команды, риски по вертикалям. Именно этот пробел — а не отсутствие привычки платить за специализированный софт — держит открытым место для финансового инструмента, спроектированного конкретно под эту индустрию.
            </p>
          </section>

          <section id="s9" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">09</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Что это значит для TAM (потолка рынка)</h2>
            <p>
              Если ориентироваться не на весь 12-миллионный хвост, а на профессиональный слой команд с реальной командной структурой (байеры, тимлиды, фармеры) — счёт идёт на десятки тысяч организаций, а не единицы. Даже консервативная доля этого сегмента, готовая платить за специализированный финансовый инструмент по цене одного трекера, — это рынок, измеряемый в сотнях миллионов долларов годовой выручки для категории в целом, не в единицах миллионов.
            </p>
          </section>

          {/* FOOTER */}
          <div className="border-t border-slate-200 pt-8 pb-12 text-sm text-slate-400 text-center">
            FinanceIntel · справочный материал · составлено на основе открытых источников по индустрии performance-маркетинга, 2026
          </div>

        </div>
      </div>
    </article>
  );
}
