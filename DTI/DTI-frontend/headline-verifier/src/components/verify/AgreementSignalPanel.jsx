import { useMemo, useState } from 'react';
import { Scale, ChevronDown, ChevronUp } from 'lucide-react';

export const AgreementSignalPanel = ({ signal, conflicting }) => {
  const [isOpen, setIsOpen] = useState(true);

  const text = useMemo(() => {
    if (!signal) return '';
    return `${signal.support_count || 0} source(s) support, ${signal.refute_count || 0} refute, ${signal.neutral_count || 0} neutral.`;
  }, [signal]);

  if (!signal) return null;

  return (
    <div className="bg-background-card rounded-xl border border-border-default overflow-hidden animate-in fade-in duration-500">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-5 flex items-center justify-between hover:bg-background-hover transition-colors focus:outline-none"
      >
        <div className="flex items-center gap-3">
          <Scale className="h-5 w-5 text-accent-blue" />
          <div className="flex flex-col items-start">
            <span className="text-sm font-bold text-text-primary">Agreement Signal</span>
            <span className="text-xs text-text-muted">{text}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {conflicting ? (
            <span className="text-[10px] font-semibold px-2 py-1 rounded-full bg-verdict-misleading/15 text-verdict-misleading border border-verdict-misleading/40">
              Conflict
            </span>
          ) : null}
          {isOpen ? <ChevronUp className="h-4 w-4 text-text-muted" /> : <ChevronDown className="h-4 w-4 text-text-muted" />}
        </div>
      </button>

      {isOpen ? (
        <div className="px-5 pb-5 border-t border-border-dim pt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-background-secondary border border-border-dim">
            <p className="text-text-muted">Support</p>
            <p className="text-text-primary text-lg font-bold">{signal.support_count || 0}</p>
          </div>
          <div className="p-3 rounded-lg bg-background-secondary border border-border-dim">
            <p className="text-text-muted">Refute</p>
            <p className="text-text-primary text-lg font-bold">{signal.refute_count || 0}</p>
          </div>
          <div className="p-3 rounded-lg bg-background-secondary border border-border-dim">
            <p className="text-text-muted">Neutral</p>
            <p className="text-text-primary text-lg font-bold">{signal.neutral_count || 0}</p>
          </div>
          <div className="p-3 rounded-lg bg-background-secondary border border-border-dim">
            <p className="text-text-muted">Contradiction</p>
            <p className="text-text-primary text-lg font-bold">{signal.explicit_contradiction ? 'Yes' : 'No'}</p>
          </div>
        </div>
      ) : null}
    </div>
  );
};
