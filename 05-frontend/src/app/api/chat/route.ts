import { NextResponse } from 'next/server';

// CR-1: This route is a PLACEHOLDER.
// It does NOT generate fake AI responses вЂ” intentionally.
// Real implementation requires FastAPI backend with tool use (function calling)
// that queries PostgreSQL for real compunknown data.
// See OPEN_QUESTIONS.md, section "Critical Risks", CR-1.

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const userMessage = body.message || '';

    const locale = body.locale || 'en';

    // TODO: Forward to FastAPI backend:
    // const response = await fetch(`${BACKEND_URL}/api/v1/chat`, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    //   body: JSON.stringify({ message: userMessage, locale }),
    // });

    // Mock response that respects the requested locale format
    const content = locale === 'ru' 
      ? 'Р‘СЌРєРµРЅРґ AI-Р°РЅР°Р»РёС‚РёРєР° РїРѕРєР° РЅРµ РїРѕРґРєР»СЋС‡РµРЅ. Р­С‚Рѕ Р·Р°РіР»СѓС€РєР° вЂ” СЂРµР°Р»СЊРЅС‹Рµ РѕС‚РІРµС‚С‹ С‚СЂРµР±СѓСЋС‚ Р±СЌРєРµРЅРґР° РЅР° FastAPI СЃ С„СѓРЅРєС†РёРµР№ РІС‹Р·РѕРІР° РёРЅСЃС‚СЂСѓРјРµРЅС‚РѕРІ (tool use) РґР»СЏ Р·Р°РїСЂРѕСЃРѕРІ Рє Р±Р°Р·Рµ РґР°РЅРЅС‹С… РєРѕРјРїР°РЅРёРё. РЎРј. OPEN_QUESTIONS.md, CR-1.'
      : 'AI Analyst backend is not connected yet. This is a placeholder вЂ” real responses require the FastAPI backend with tool use (function calling) to query actual compunknown data from PostgreSQL. See OPEN_QUESTIONS.md, CR-1.';

    return NextResponse.json({
      role: 'assistant',
      content,
      tool_calls_used: null,
    });
  } catch {
    return NextResponse.json(
      { error: 'Failed to process chat message' },
      { status: 500 }
    );
  }
}

