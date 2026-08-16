/**
 * SectionRegistry — Defines which sections are applicable for each report context.
 *
 * Each section declares:
 *   id:          unique identifier
 *   label:       sidebar navigation label
 *   icon:        lucide icon component
 *   isApplicable(ctx): returns true if the section should render for this context
 *
 * The sidebar is built dynamically from applicable sections only.
 * Sections that are not applicable are never rendered — no empty cards, no whitespace.
 */
import {
  LayoutDashboard, TrendingUp, DollarSign, ShieldAlert,
  MapPin, LogOut, FileText,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ReportContext } from './ReportContext';
import { isEndUser } from './ReportContext';

export interface SectionDef {
  id: string;
  label: string;
  icon: LucideIcon;
  isApplicable: (ctx: ReportContext) => boolean;
}

export const SECTIONS: SectionDef[] = [
  {
    id: 'summary',
    label: 'Executive Summary',
    icon: LayoutDashboard,
    isApplicable: () => true,
  },
  {
    id: 'returns',
    label: 'Expected Returns',
    icon: TrendingUp,
    isApplicable: (ctx) => !isEndUser(ctx),
  },
  {
    id: 'valuation',
    label: 'Valuation',
    icon: DollarSign,
    isApplicable: (ctx) => !isEndUser(ctx),
  },
  {
    id: 'risk',
    label: 'Risk Analysis',
    icon: ShieldAlert,
    isApplicable: () => true,
  },
  {
    id: 'market',
    label: 'Market & Location',
    icon: MapPin,
    isApplicable: (ctx) => !isEndUser(ctx),
  },
  {
    id: 'exit',
    label: 'Exit Strategy',
    icon: LogOut,
    isApplicable: (ctx) => !isEndUser(ctx),
  },
  {
    id: 'evidence',
    label: 'Evidence Quality',
    icon: FileText,
    isApplicable: () => true,
  },
];

export function getApplicableSections(ctx: ReportContext): SectionDef[] {
  // If backend report contract exists, ONLY render what it explicitly allows.
  // The frontend never infers which cards to display — it obeys the backend contract.
  if (ctx.reportContract) {
    const allowed = new Set(ctx.reportContract.visible_sections);
    return SECTIONS.filter(s => allowed.has(s.id));
  }
  // Fallback: use legacy isApplicable logic (for when backend contract is not yet available)
  return SECTIONS.filter(s => s.isApplicable(ctx));
}
