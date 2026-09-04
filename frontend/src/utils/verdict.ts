// ─── VERIFY-X 2.0 — Verdict Utilities ───

import type { VerdictType } from '../types/verification';

export const VERDICT_CONFIG: Record<
  VerdictType,
  { label: string; color: string; bgColor: string; borderColor: string; icon: string }
> = {
  TRUE: {
    label: 'TRUE',
    color: '#10b981',
    bgColor: 'rgba(16, 185, 129, 0.1)',
    borderColor: 'rgba(16, 185, 129, 0.3)',
    icon: '✓',
  },
  FALSE: {
    label: 'FALSE',
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.1)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
    icon: '✗',
  },
  MISLEADING: {
    label: 'MISLEADING',
    color: '#f59e0b',
    bgColor: 'rgba(245, 158, 11, 0.1)',
    borderColor: 'rgba(245, 158, 11, 0.3)',
    icon: '⚠',
  },
  PARTIALLY_TRUE: {
    label: 'PARTIALLY TRUE',
    color: '#3b82f6',
    bgColor: 'rgba(59, 130, 246, 0.1)',
    borderColor: 'rgba(59, 130, 246, 0.3)',
    icon: '◐',
  },
  NOT_ENOUGH_INFORMATION: {
    label: 'INSUFFICIENT EVIDENCE',
    color: '#6b7280',
    bgColor: 'rgba(107, 114, 128, 0.1)',
    borderColor: 'rgba(107, 114, 128, 0.3)',
    icon: '?',
  },
};

export function getVerdictConfig(verdict: VerdictType) {
  return VERDICT_CONFIG[verdict] || VERDICT_CONFIG.NOT_ENOUGH_INFORMATION;
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
}

export function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
