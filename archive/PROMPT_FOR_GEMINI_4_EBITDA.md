# Промпт для Gemini №4 — EBITDA / EBIT / EBT в P&L

> ВАЖНО: прочитай AGENTS.md перед написанием кода. Next.js 16.2.10 — ломающие изменения. Читай `node_modules/next/dist/docs/` перед использованием любого API фреймворка.

---

## Контекст

Проект **FinanceIntel**, путь: `c:\Users\fylht\Desktop\Стартапы\SaaS финансовый менеджмент для медиабаинговых компаний`.
Фронтенд: `05-frontend/` (Next.js 16, React 19, next-intl 4, Tailwind 4, recharts, lucide-react).
Документация: `02-product-docs/`.

Прочитай перед работой:
- `05-frontend/src/components/screens/PnLScreen.tsx` — экран P&L (уже есть расширение партнёрок с холдами)
- `05-frontend/src/lib/mockData.ts` — `pnlData`
- `02-product-docs/DB_SCHEMA.md` — таблицы `transactions`, категории расходов

---

## Задача: добавить каскад EBITDA → EBIT → EBT → Net Profit

### Почему это важно для медиабаинга

Для медиабаинговой компании финансовая структура выглядит так:

```
Revenue (Выручка)
  − Ad Spend (рекламный бюджет — прямая переменная себестоимость)
= Gross Profit (Валовая прибыль)          ← показывает, сколько зарабатывает
                                             сам трафик до команды и инфраструктуры

  − Salaries & Payroll (зарплаты)
  − Consumables (прокси, карты, антидетект) ← расходники тоже операционные, не капитальные
  − Infrastructure & Software
  − Operational
= EBITDA                                   ← операционная эффективность бизнеса
                                             ДО амортизации, процентов и налогов

  − D&A (Depreciation & Amortization)      ← амортизация ПО и оборудования
= EBIT (Operating Profit)                  ← «сколько зарабатывает операция»

  − Interest Expense                       ← проценты по займам на покрытие кэш-гэпа
                                             (реальная боль: потратил сейчас, получил через Net-30)
= EBT (Earnings Before Tax)

  − Income Tax
= Net Profit (Чистая прибыль)
```

Ключевой момент для медиабаинга: **Gross Profit показывает эффективность трафика**, EBITDA — **эффективность бизнеса в целом**. Без этого разделения непонятно — компания теряет деньги на трафике или на раздутом штате/инфраструктуре.

---

### Задача 1. Обновить мок-данные `mockData.ts`

Добавить в `pnlData` недостающие статьи. Числа должны образовывать логичный каскад.

**Расходы — расширить список:**
- Существующие: `Ad spend 640k`, `Salaries 145k`, `Infrastructure 32k`, `Operational 43k`
- Добавить отдельную строку `Consumables` (расходники: прокси, карты, антидетект) — по данным статьи «Экономика медиабаинга» это 2–5% от оборота. Взять ~2.5% от Revenue. Примерно $31k.
- Добавить `Depreciation & Amortization` — у медиабаинга D&A минимальна (в основном амортизация лицензий). Примерно $4–5k.
- Добавить `Interest Expense` — проценты по кредитной линии на покрытие кэш-гэпа (пока закладываем $8k, это реальная статья для компаний с Net-30).
- Добавить `Income Tax` — упрощённо 15% от EBT.

Убедись, что все числа сходятся в каскад. Проверь арифметику вручную перед записью в файл.

Добавить `category` для новых статей: `consumables`, `depreciation`, `interest`, `tax`.

**Доходы — не менять.**

### Задача 2. Добавить расчёт каскада в `PnLScreen.tsx`

Рассчитывать все уровни из данных:

```ts
const revenue = totalIncome                           // $1,245k
const adSpend = expenses.find(e => e.category === 'ad_spend').value  // $640k
const grossProfit = revenue - adSpend                 // $605k
const grossMargin = grossProfit / revenue * 100       // 48.6%

const opex = expenses.filter(e =>
  ['salary','infra','operational','consumables'].includes(e.category)
).reduce(...)
const ebitda = grossProfit - opex                     // ~$385k
const ebitdaMargin = ebitda / revenue * 100           // ~30.9%

const da = expenses.find(e => e.category === 'depreciation').value
const ebit = ebitda - da

const interest = expenses.find(e => e.category === 'interest').value
const ebt = ebit - interest

const tax = expenses.find(e => e.category === 'tax').value
const netProfit = ebt - tax
const netMargin = netProfit / revenue * 100
```

Всё вычисляется динамически из данных — не хардкодить суммы.

### Задача 3. Отобразить каскад в UI

**Блок 1 — KPI-плитки сверху.** Расширить с 4 до 6–7 плиток (или сделать два ряда):
`Revenue` | `Gross Profit` | `EBITDA` | `EBIT` | `EBT` | `Net Profit` | и маржи для ключевых уровней.

Цвет Net Profit: зелёный если > 0, красный если < 0.

**Блок 2 — Каскадный (waterfall) вид P&L.** Это главное изменение — вместо двух колонок «Доходы / Расходы» показать вертикальный каскад:

```
Revenue                              $1,245k  100%
  − Ad Spend                         (640k)
──────────────────────────────────────────────────
= Gross Profit                        $605k   48.6%   ← визуальный разделитель

  − Salaries                          (145k)
  − Consumables                        (31k)
  − Infrastructure                     (32k)
  − Operational                        (43k)
──────────────────────────────────────────────────
= EBITDA                              $354k   28.4%   ← с маржей

  − D&A                                 (4k)
──────────────────────────────────────────────────
= EBIT                                $350k   28.1%

  − Interest                            (8k)
──────────────────────────────────────────────────
= EBT                                 $342k   27.5%

  − Tax                                (51k)
──────────────────────────────────────────────────
= Net Profit                          $291k   23.4%
```

Реализовать как таблицу или список с визуальными разделителями. **Не recharts** — это текстовый каскад, не нужен граф. Индентация для промежуточных статей. Маржа (%) показывается только у уровней (Gross Profit, EBITDA, EBIT, EBT, Net Profit), а не у каждой статьи расходов.

Строки со скобками `(−)` — красноватый цвет (`text-red-600` или `text-gray-500`). Итоговые строки — жирные, с разделителем.

**Блок 3 — Партнёрки (уже есть, не трогать).** Раскрытие строки Partner payouts из промпта №3. Убедись, что не сломано.

**Блок 4 — Пояснения под каскадом.** Три коротких пояснения:
- Что такое Gross Profit и зачем: «показывает прибыльность трафика до учёта операционных затрат»
- Что такое EBITDA: «операционная прибыль бизнеса до D&A, процентов и налогов — используется для сравнения с другими компаниями»
- Про D&A и Interest: «у медиабаинговых компаний D&A обычно мала; Interest может быть существенным при кредитовании рекламного бюджета (кэш-гэп Net-30)»

### Задача 4. DB_SCHEMA.md

В `02-product-docs/DB_SCHEMA.md`, в разделе `transactions`, расширить список категорий в комментарии к полю `category`:
```
category: ad_spend | salary | infra | tax | payout | consumables | depreciation | interest | other
```

Добавить в раздел «Производные метрики» формулы каскада (как выше, кратко).

Добавить примечание: «для корректного EBITDA consumables должны учитываться отдельной статьёй, а не входить в ad_spend или operational».

### Задача 5. i18n

В `messages/en.json` и `messages/ru.json` секция `pnl`:
- `grossProfit`, `grossMargin`, `ebitda`, `ebitdaMargin`, `ebit`, `ebit_label`, `ebt`, `netMargin`
- `consumables`, `depreciation`, `interestExpense`, `incomeTax`
- Подписи-пояснения для блока 4

### Задача 6. Сборка

`npm run build` без ошибок. Отчёт: что изменил, результат сборки, арифметическая проверка каскада с числами.
