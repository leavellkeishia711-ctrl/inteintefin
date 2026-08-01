"use client";

import React from 'react';
import { Card } from '@/components/ui/Card';
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

const cashGapData = [
  { day: 'День 1', spend: 0, booked: 0, actual: 0 },
  { day: 'День 7', spend: 7, booked: 9, actual: 0 },
  { day: 'День 14', spend: 14, booked: 18, actual: 0 },
  { day: 'День 21', spend: 21, booked: 27, actual: 0 },
  { day: 'День 28', spend: 28, booked: 36, actual: 0 },
  { day: 'День 29', spend: 29, booked: 37, actual: 32 },
  { day: 'День 35', spend: 35, booked: 45, actual: 32 },
  { day: 'День 40', spend: 40, booked: 52, actual: 42 },
  { day: 'День 45', spend: 45, booked: 60, actual: 42 },
];

const lifecycleData = [
  { week: 'Нед 1', spend: 3.5, profit: -0.2 },
  { week: 'Нед 2', spend: 4.2, profit: 0.3 },
  { week: 'Нед 3', spend: 9.0, profit: 2.0 },
  { week: 'Нед 4', spend: 15.0, profit: 4.7 },
  { week: 'Нед 5', spend: 21.0, profit: 6.5 },
  { week: 'Нед 6', spend: 21.0, profit: 3.0 },
  { week: 'Нед 7', spend: 18.0, profit: 0.8 },
  { week: 'Нед 8', spend: 12.0, profit: -0.6 },
];

export default function EkonomikaMediabainga() {
  return (
    <article className="pb-24">
      {/* HERO BLOCK - FULL BLEED IN (FULLWIDTH) LAYOUT */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-800 text-slate-100 pt-16 pb-12 px-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-teal-300 font-bold mb-4">
            <div className="w-2 h-2 rounded-full bg-teal-300" />
            FinanceIntel · справочный материал
          </div>
          <h1 className="text-3xl md:text-5xl font-extrabold leading-tight tracking-tight mb-6 max-w-3xl">
            Почему на бумаге вы в плюсе, а денег на счету нет
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mb-10">
            Экономика медиабаинга устроена так, что расход — ежедневный и мгновенный, а доход — отложенный, урезанный и неопределённый. Разрыв между этими двумя фактами и есть главная финансовая опасность отрасли.
          </p>

          {/* HERO CHART */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-sm">
            <div className="flex flex-wrap justify-between items-start gap-4 mb-4">
              <div>
                <h3 className="text-base font-bold text-white m-0">Кассовый разрыв: 45 дней одной связки</h3>
                <p className="text-sm text-slate-400 mt-1">Потрачено vs заработано «на бумаге» vs реально получено на счёт</p>
              </div>
            </div>
            
            <div className="h-[300px] mt-4 w-full text-xs">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cashGapData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="day" stroke="#7A8794" tick={{fill: '#7A8794'}} axisLine={false} tickLine={false} />
                  <YAxis stroke="#7A8794" tick={{fill: '#7A8794'}} axisLine={false} tickLine={false} tickFormatter={(val) => `$${val}k`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1E293B', border: 'none', borderRadius: '8px', color: '#F8FAFC' }}
                    itemStyle={{ color: '#F8FAFC' }}
                  />
                  <Legend wrapperStyle={{ paddingTop: '10px' }} />
                  <Area type="stepAfter" dataKey="actual" name="Получено на счёт" stroke="#0E9F6E" strokeWidth={2.5} fill="rgba(14,159,110,0.15)" />
                  <Line type="monotone" dataKey="booked" name="Заработано (booked)" stroke="#7FD9CC" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                  <Line type="monotone" dataKey="spend" name="Расход (кумулятивно)" stroke="#C0392B" strokeWidth={2.5} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            
            <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl p-3 mt-4 text-sm text-red-200">
              <span className="shrink-0">⚠</span>
              С 1 по 29 день расход уже реален и растёт каждый день, а на счёт не пришло ни цента — все 29 дней компания финансирует рекламу из собственного кармана, даже если связка прибыльна «на бумаге».
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
            {['Юнит-экономика связки', 'Кассовый разрыв', 'Структура расходов', 'Вертикали: в чём разница', 'Компенсация команды', 'Жизненный цикл связки', 'Метрики для управления', 'Почему обычный учёт не подходит'].map((title, i) => (
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
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Юнит-экономика связки</h2>
            <p className="mb-4">
              «Связка» (bundle) — это оффер + гео + креатив + источник трафика, самая мелкая единица, на которой можно посчитать прибыльность. Базовая механика простая: покупаем клики/показы на источнике трафика, часть посетителей конвертируется в целевое действие (депозит, лид, покупка), партнёрская сеть платит за это действие.
            </p>
            
            <div className="border-l-4 border-teal-600 bg-teal-50 rounded-r-xl p-5 my-6 text-teal-900 font-semibold">
              Потратили $15 000 на трафик → получили 5 конверсий по $4 000 каждая → заработали $20 000 → чистая прибыль $5 000, ROI 33%.
            </div>

            <h3 className="text-lg font-bold text-slate-900 mt-8 mb-3">Базовые формулы</h3>
            <div className="space-y-2 mb-4">
              <div className="inline-block bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm mr-2 mb-2">
                ROI = (Revenue − Spend) / Spend × 100%
              </div>
              <div className="inline-block bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm mr-2 mb-2">
                ROAS = Revenue / Spend
              </div>
              <div className="inline-block bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm mr-2 mb-2">
                CPA = Spend / Число конверсий
              </div>
            </div>
            <p>
              Условно прибыльной связка считается уже при ROI от 15–20% — но это «бумажная» прибыльность в момент клика. Реальная прибыльность становится известна только после того, как партнёрская сеть подтвердит и оплатит конверсии — а это отдельная история (раздел 02).
            </p>
          </section>

          <section id="s2" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">02</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Кассовый разрыв — главный финансовый риск отрасли</h2>
            <p className="mb-4">
              Партнёрские сети не платят мгновенно. Между «конверсия произошла» и «деньги на счету» стоит hold period — окно, в течение которого сеть проверяет трафик на фрод, дубликаты и чарджбеки. Дальше — цикл выплат (Net-7/15/30/60), который определяет, как часто вообще происходит расчёт.
            </p>

            <div className="overflow-x-auto my-6 rounded-xl border border-slate-200 shadow-sm">
              <table className="w-full text-sm text-left bg-white">
                <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Тип цикла</th>
                    <th className="px-4 py-3">Типичный срок</th>
                    <th className="px-4 py-3">Hold на первый цикл</th>
                    <th className="px-4 py-3">Комментарий</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Net-30 (стандарт)</td><td className="px-4 py-3">30 дней</td><td className="px-4 py-3">30 дней</td><td className="px-4 py-3">Дефолтные условия у большинства сетей</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Net-15</td><td className="px-4 py-3">15 дней</td><td className="px-4 py-3">30 дней на старте</td><td className="px-4 py-3">Доступен при устойчивом объёме</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Net-7</td><td className="px-4 py-3">7 дней</td><td className="px-4 py-3">30 дней на старте</td><td className="px-4 py-3">Обычно есть минимальный порог за период (от $500)</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Weekly / Net-5</td><td className="px-4 py-3">Еженедельно</td><td className="px-4 py-3">30 дней на старте</td><td className="px-4 py-3">Топ-уровень, доступен проверенным аккаунтам</td></tr>
                </tbody>
              </table>
            </div>

            <h3 className="text-lg font-bold text-slate-900 mt-8 mb-3">Хуже, чем задержка: сумма приходит меньше, чем казалось</h3>
            <p className="mb-4">Есть два механизма, которые режут «бумажную» цифру до того, как она станет реальными деньгами:</p>
            
            <div className="overflow-x-auto my-6 rounded-xl border border-slate-200 shadow-sm">
              <table className="w-full text-sm text-left bg-white">
                <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Механизм</th>
                    <th className="px-4 py-3">Что происходит</th>
                    <th className="px-4 py-3">Типичный масштаб</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Scrub</td><td className="px-4 py-3">Рекламодатель частично дисквалифицирует засчитанные конверсии, не всегда объясняя, какие именно</td><td className="px-4 py-3">10–30% в iGaming и nutra</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Clawback / чарджбек</td><td className="px-4 py-3">Полный откат уже показанной выплаты — из-за возврата, фрод-флага или дубля</td><td className="px-4 py-3">Индивидуально, но регулярно</td></tr>
                </tbody>
              </table>
            </div>
            
            <p>
              Отсюда практическое правило отрасли: значение имеет не то, что показывает дашборд партнёрки в моменте, а число «booked минус reversed» через 30 дней. Это ровно то число, ради которого в FinanceIntel считается Cash Flow и Cash Runway отдельно от P&L.
            </p>
          </section>

          <section id="s3" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">03</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Структура расходов команды</h2>
            <p className="mb-4">
              Рекламный бюджет — крупнейшая статья, но далеко не единственная. Полная структура расходов медиабаинговой команды:
            </p>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
              {[
                { v: '~70–85%', l: 'Рекламный расход (spend)' },
                { v: '~8–15%', l: 'Зарплаты и бонусы команды' },
                { v: '~3–6%', l: 'Инфраструктура: трекеры, антидетект, прокси' },
                { v: '~2–5%', l: 'Аккаунты: фарм, покупка, прогрев' }
              ].map((s, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                  <div className="text-xl font-extrabold text-slate-900">{s.v}</div>
                  <div className="text-xs text-slate-500 mt-1">{s.l}</div>
                </div>
              ))}
            </div>
            
            <p>
              Инфраструктурная статья включает трекеры (Keitaro, Binom, Voluum), антидетект-браузеры для управления множеством аккаунтов, прокси (mobile/residential/datacenter) и системы клоакинга для прохождения модерации рекламных площадок — это не «опционально», а необходимая часть стека для работы в высокорисковых вертикалях.
            </p>
          </section>

          <section id="s4" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">04</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Вертикали: в чём разница</h2>
            <p className="mb-4">
              Gambling, Crypto и Nutra объединяет статус «высокорисковых» у рекламных платформ — но экономически это три разных бизнеса.
            </p>

            <Card className="my-6 p-6">
              <h4 className="text-base font-bold text-slate-900 m-0">Типичный hold period по вертикали</h4>
              <p className="text-sm text-slate-500 mb-6">Дней от конверсии до подтверждения выплаты</p>
              
              {/* CUSTOM DIV-BASED HOLD PERIOD CHART */}
              <div className="relative w-full max-w-2xl mx-auto h-40">
                {/* Grid Lines */}
                <div className="absolute inset-y-0 left-[20%] border-l border-slate-200"></div>
                <div className="absolute inset-y-0 left-[35%] border-l border-slate-100"></div>
                <div className="absolute inset-y-0 left-[50%] border-l border-slate-100"></div>
                <div className="absolute inset-y-0 left-[65%] border-l border-slate-100"></div>
                <div className="absolute inset-y-0 left-[80%] border-l border-slate-100"></div>
                <div className="absolute inset-y-0 left-[95%] border-l border-slate-100"></div>
                
                {/* Labels */}
                <div className="absolute bottom-0 left-[20%] -translate-x-1/2 text-xs text-slate-400">0д</div>
                <div className="absolute bottom-0 left-[65%] -translate-x-1/2 text-xs text-slate-400">30д</div>
                <div className="absolute bottom-0 left-[95%] -translate-x-1/2 text-xs text-slate-400">50д</div>

                {/* Bars */}
                {/* Gambling: 30-45 days. 0 days = 20%, 30 days = 65% (1.5% per day) */}
                {/* 30 days = left: 65%. 45 days = left: 87.5%. Width = 22.5% */}
                <div className="absolute top-2 left-0 w-full flex items-center">
                  <div className="w-[20%] text-sm font-semibold text-slate-900">Gambling</div>
                  <div className="absolute left-[65%] w-[22.5%] h-6 bg-teal-700 rounded-md"></div>
                  <div className="absolute left-[89%] text-xs text-slate-500">30–45 дней</div>
                </div>

                {/* Nutra: 25-35 days. 25 days = 20% + 25*1.5 = 57.5%. 35 days = 20% + 35*1.5 = 72.5%. Width = 15% */}
                <div className="absolute top-12 left-0 w-full flex items-center">
                  <div className="w-[20%] text-sm font-semibold text-slate-900">Nutra</div>
                  <div className="absolute left-[57.5%] w-[15%] h-6 bg-teal-700 rounded-md"></div>
                  <div className="absolute left-[74%] text-xs text-slate-500">25–35 дней</div>
                </div>

                {/* Crypto: 14-30 days. 14 days = 20% + 14*1.5 = 41%. 30 days = 65%. Width = 24% */}
                <div className="absolute top-22 left-0 w-full flex items-center" style={{ top: '88px' }}>
                  <div className="w-[20%] text-sm font-semibold text-slate-900">Crypto</div>
                  <div className="absolute left-[41%] w-[24%] h-6 bg-teal-700 rounded-md"></div>
                  <div className="absolute left-[66.5%] text-xs text-slate-500">14–30 дней</div>
                </div>
              </div>
            </Card>

            <div className="overflow-x-auto my-6 rounded-xl border border-slate-200 shadow-sm">
              <table className="w-full text-sm text-left bg-white">
                <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3"></th>
                    <th className="px-4 py-3">Gambling</th>
                    <th className="px-4 py-3">Crypto</th>
                    <th className="px-4 py-3">Nutra</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">Модель</td>
                    <td className="px-4 py-3">RevShare от депозита</td>
                    <td className="px-4 py-3">CPA / RevShare</td>
                    <td className="px-4 py-3">CPA / гибрид</td>
                  </tr>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">Горизонт LTV</td>
                    <td className="px-4 py-3">Месяцы-годы, повторные депозиты</td>
                    <td className="px-4 py-3">Разово-средне</td>
                    <td className="px-4 py-3">В основном разово</td>
                  </tr>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">Scrub/чарджбек</td>
                    <td className="px-4 py-3"><span className="inline-block px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">Высокий</span></td>
                    <td className="px-4 py-3"><span className="inline-block px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-700">Средний</span></td>
                    <td className="px-4 py-3"><span className="inline-block px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">Высокий</span></td>
                  </tr>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">Прохождение модерации креативов с 1-й попытки</td>
                    <td className="px-4 py-3">Низкое, нужен клоакинг</td>
                    <td className="px-4 py-3">Среднее</td>
                    <td className="px-4 py-3">10–30%</td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <p>
              Важное следствие для команды: RevShare в гемблинге означает, что прибыль от одного и того же игрока может поступать месяцами — это тянет за собой отдельную задачу атрибуции («какой байер и какая кампания привели этого игрока изначально»), которой нет в nutra с его разовыми покупками.
            </p>
          </section>

          <section id="s5" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">05</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Компенсация команды</h2>
            <p className="mb-4">
              Экономика ролей внутри команды устроена так, что почти вся переменная часть завязана на реальную (а не бумажную) прибыль — именно поэтому кассовый разрыв из раздела 02 напрямую влияет на то, когда команда физически может получить зарплату.
            </p>
            
            <div className="overflow-x-auto my-6 rounded-xl border border-slate-200 shadow-sm">
              <table className="w-full text-sm text-left bg-white">
                <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Роль</th>
                    <th className="px-4 py-3">Модель</th>
                    <th className="px-4 py-3">На чём завязана переменная часть</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Медиабайер</td><td className="px-4 py-3">Оклад + % от прибыли</td><td className="px-4 py-3">Net Campaign Profit его связок</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Тимлид</td><td className="px-4 py-3">Оклад + % (override)</td><td className="px-4 py-3">Прибыль всей команды</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Фармер</td><td className="px-4 py-3">Фикс + квота</td><td className="px-4 py-3">Число подготовленных аккаунтов/месяц</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Креатив/монтаж</td><td className="px-4 py-3">Фикс или сдельно</td><td className="px-4 py-3">Объём и утверждённые единицы</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section id="s6" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">06</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Жизненный цикл связки</h2>
            <p className="mb-4">
              Прибыль связки не растёт линейно вслед за бюджетом — у каждой связки есть фаза теста, масштабирования и выгорания, и решение «когда убивать» — одно из самых дорогих в отрасли.
            </p>
            
            <Card className="my-6 p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h4 className="text-base font-bold text-slate-900 m-0">Расход и прибыль связки по неделям</h4>
                  <p className="text-sm text-slate-500 m-0">Test → Scale → Decline на условном примере</p>
                </div>
              </div>
              
              <div className="h-[250px] w-full text-xs mt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={lifecycleData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                    <XAxis dataKey="week" stroke="#64748B" tick={{fill: '#64748B'}} axisLine={false} tickLine={false} />
                    <YAxis stroke="#64748B" tick={{fill: '#64748B'}} axisLine={false} tickLine={false} tickFormatter={(val) => `$${val}k`} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#fff', border: '1px solid #E2E8F0', borderRadius: '8px', color: '#1E293B', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      itemStyle={{ color: '#1E293B' }}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                    <Area type="monotone" dataKey="profit" name="Прибыль" stroke="#0E9F6E" strokeWidth={2.5} fill="rgba(14,159,110,0.15)" />
                    <Line type="monotone" dataKey="spend" name="Расход" stroke="#C0392B" strokeWidth={2.5} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
            
            <p>
              На неделях 3–5 бюджет и прибыль растут вместе — это окно масштабирования. С недели 6 прибыль начинает падать быстрее, чем расход: креатив «выгорает» (CTR падает, CPM растёт), но команда часто продолжает лить бюджет по инерции ещё 1–2 недели после точки, где сигнал уже был очевиден. Это ровно то место, где Decision Recommendation Engine должен подавать сигнал раньше человека.
            </p>
          </section>

          <section id="s7" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">07</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Метрики для управления</h2>
            
            <div className="overflow-x-auto my-6 rounded-xl border border-slate-200 shadow-sm">
              <table className="w-full text-sm text-left bg-white">
                <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Метрика</th>
                    <th className="px-4 py-3">Формула</th>
                    <th className="px-4 py-3">Что показывает</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">ROI</td><td className="px-4 py-3">(Revenue−Spend)/Spend</td><td className="px-4 py-3">Прибыльность относительно вложений</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">ROAS</td><td className="px-4 py-3">Revenue/Spend</td><td className="px-4 py-3">Возврат на каждый потраченный доллар</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">CPA</td><td className="px-4 py-3">Spend/Конверсии</td><td className="px-4 py-3">Цена одного целевого действия</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">EPC</td><td className="px-4 py-3">Revenue/Клики</td><td className="px-4 py-3">Доход с одного клика</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Cash Runway</td><td className="px-4 py-3">Баланс/Средний дневной расход</td><td className="px-4 py-3">Сколько дней компания протянет без новых поступлений</td></tr>
                  <tr className="hover:bg-slate-50"><td className="px-4 py-3 font-semibold text-slate-900">Payroll-to-Revenue</td><td className="px-4 py-3">Выплаты/Revenue</td><td className="px-4 py-3">Доля выручки, уходящая на команду</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section id="s8" className="scroll-mt-8">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-sm font-extrabold text-teal-700 tabular-nums">08</span>
            </div>
            <h2 className="text-2xl font-extrabold text-slate-900 mb-4 tracking-tight">Почему обычный учёт не подходит</h2>
            <p className="mb-4">
              Классический бухгалтерский P&L признаёт доход в момент начисления, а не в момент поступления денег — для большинства бизнесов эта разница некритична. В медиабаинге эти два момента могут быть разнесены на 30–60 дней и отличаться по сумме на 10–30% из-за scrub — то есть сам P&L систематически лжёт о состоянии бизнеса, если его не дополнить отдельным взглядом на реальное движение денег.
            </p>
            <p className="mb-4">
              Отсюда прямая связь с архитектурой FinanceIntel: P&L и Cash Flow — не два представления одних данных, а два разных, оба обязательных вопроса — «прибыльны ли мы на бумаге» и «хватит ли денег дожить до момента, когда бумажная прибыль станет настоящей». Payroll привязан к прибыли по кампаниям, а не к обороту, ровно потому что оборот в этой индустрии — это цифра, которой нельзя доверять до конца hold-периода.
            </p>
          </section>

          {/* FOOTER */}
          <div className="border-t border-slate-200 pt-8 pb-12 text-sm text-slate-400 text-center">
            FinanceIntel · справочный материал · составлено на основе открытых источников по CPA-индустрии, 2026
          </div>

        </div>
      </div>
    </article>
  );
}
