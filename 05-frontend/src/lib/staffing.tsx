"use client";

/**
 * Р’РёРґРёРјРѕСЃС‚СЊ С„СѓРЅРєС†РёРѕРЅР°Р»Р° РїРѕ РЅР°Р»РёС‡РёСЋ СЂРѕР»РµР№ РІ РєРѕРјРїР°РЅРёРё.
 *
 * РџСЂР°РІРёР»Рѕ (СЃРј. MVP.md, В«РђРґР°РїС‚РёРІРЅС‹Р№ РёРЅС‚РµСЂС„РµР№СЃ РїРѕ СЃРѕСЃС‚Р°РІСѓ РєРѕРјР°РЅРґС‹В»):
 * РµСЃР»Рё РІ РєРѕРјРїР°РЅРёРё РЅРµС‚ СЃРѕС‚СЂСѓРґРЅРёРєРѕРІ СЃ РѕРїСЂРµРґРµР»С‘РЅРЅРѕР№ СЂРѕР»СЊСЋ вЂ” РІРµСЃСЊ С„СѓРЅРєС†РёРѕРЅР°Р»
 * РїРѕРґ СЌС‚Сѓ СЂРѕР»СЊ СЃРєСЂС‹С‚. РџРѕСЏРІРёР»СЃСЏ СЃРѕС‚СЂСѓРґРЅРёРє вЂ” СЂР°Р·РґРµР» РїРѕСЏРІР»СЏРµС‚СЃСЏ СЃР°Рј.
 *
 * Р’ РґРµРјРѕ СЃРѕСЃС‚Р°РІ РєРѕРјР°РЅРґС‹ РїРµСЂРµРєР»СЋС‡Р°РµС‚СЃСЏ РІСЂСѓС‡РЅСѓСЋ РІ РќР°СЃС‚СЂРѕР№РєР°С… Рё С…СЂР°РЅРёС‚СЃСЏ
 * РІ localStorage. РќР° СЂРµР°Р»СЊРЅРѕРј Р±СЌРєРµРЅРґРµ РёСЃС‚РѕС‡РЅРёРє вЂ” COUNT(*) РїРѕ users
 * СЃ РіСЂСѓРїРїРёСЂРѕРІРєРѕР№ РїРѕ staff_role РІРЅСѓС‚СЂРё compunknown_id.
 */

import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { StaffRole } from './constants';

const STORAGE_KEY = 'financeintel.staffing.v1';

/** Р”РµС„РѕР»С‚ РґРµРјРѕ-РєРѕРјРїР°РЅРёРё: РµСЃС‚СЊ РІСЃРµ СЂРѕР»Рё, С‡С‚РѕР±С‹ Р±С‹Р»Рѕ С‡С‚Рѕ РїРѕРєР°Р·Р°С‚СЊ. */
const DEFAULT_STAFFING: Record<StaffRole, boolean> = {
  media_buyer: true,
  team_lead: true,
  farmer: true,
  processor: true,
  creative: true,
};

interface StaffingContextValue {
  /** Р•СЃС‚СЊ Р»Рё РІ РєРѕРјРїР°РЅРёРё С…РѕС‚СЏ Р±С‹ РѕРґРёРЅ СЃРѕС‚СЂСѓРґРЅРёРє СЃ СЌС‚РѕР№ СЂРѕР»СЊСЋ. */
  has: (role: StaffRole) => boolean;
  staffing: Record<StaffRole, boolean>;
  toggleRole: (role: StaffRole, present: boolean) => void;
  /** Р—Р°РіСЂСѓР·РёР»СЃСЏ Р»Рё СЃРѕСЃС‚Р°РІ РёР· localStorage (РґРѕ СЌС‚РѕРіРѕ СЂРµРЅРґРµСЂРёРј РґРµС„РѕР»С‚). */
  ready: boolean;
}

const StaffingContext = createContext<StaffingContextValue | null>(null);

export const StaffingProvider = ({ children }: { children: React.ReactNode }) => {
  const [staffing, setStaffing] = useState<Record<StaffRole, boolean>>(DEFAULT_STAFFING);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<Record<StaffRole, boolean>>;
        // eslint-disable-next-line react-hooks/exhaustive-deps
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setStaffing({ ...DEFAULT_STAFFING, ...parsed });
      }
    } catch {
      // повреждённое значение игнорируем, остаётся дефолт
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReady(true);
  }, []);

  const toggleRole = (role: StaffRole, present: boolean) => {
    setStaffing((prev) => {
      const next = { ...prev, [role]: present };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // РїСЂРёРІР°С‚РЅС‹Р№ СЂРµР¶РёРј вЂ” РїСЂРѕСЃС‚Рѕ РЅРµ СЃРѕС…СЂР°РЅСЏРµРј
      }
      return next;
    });
  };

  const value = useMemo<StaffingContextValue>(
    () => ({
      staffing,
      ready,
      has: (role: StaffRole) => staffing[role] ?? false,
      toggleRole,
    }),
    [staffing, ready],
  );

  return <StaffingContext.Provider value={value}>{children}</StaffingContext.Provider>;
};

export const useStaffing = () => {
  const ctx = useContext(StaffingContext);
  if (!ctx) throw new Error('useStaffing must be used within StaffingProvider');
  return ctx;
};

/**
 * РћР±С‘СЂС‚РєР° РґР»СЏ СѓСЃР»РѕРІРЅРѕРіРѕ СЂРµРЅРґРµСЂР° Р±Р»РѕРєР° РїРѕРґ СЂРѕР»СЊ.
 * РќРёС‡РµРіРѕ РЅРµ СЂРµРЅРґРµСЂРёС‚, РµСЃР»Рё СЂРѕР»Рё РІ РєРѕРјРїР°РЅРёРё РЅРµС‚.
 */
export const IfRole = ({ role, children }: { role: StaffRole; children: React.ReactNode }) => {
  const { has } = useStaffing();
  return has(role) ? <>{children}</> : null;
};



