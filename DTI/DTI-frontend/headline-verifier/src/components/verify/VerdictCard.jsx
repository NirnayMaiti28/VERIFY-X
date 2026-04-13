import { VerdictBadge } from './VerdictBadge';
import { ConfidenceMeter } from './ConfidenceMeter';

export const VerdictCard = ({ claim, verdict, confidence, summary, conflictingSources }) => {

  return (
    <div className="p-6 md:p-8 bg-background-card rounded-xl border border-border-default shadow-sm flex flex-col gap-6 animate-in slide-in-from-bottom-2 duration-500">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-bold text-text-muted uppercase tracking-widest">Analyzed Claim</span>
          <h2 className="text-xl md:text-2xl font-bold text-text-primary leading-snug">
            "{claim}"
          </h2>
        </div>
        <div className="shrink-0 flex flex-col items-end gap-2">
          <VerdictBadge verdict={verdict} />
          <p className="text-right text-sm text-text-secondary">{Math.round(confidence * 100)}%</p>
          {conflictingSources ? (
            <span className="text-xs font-semibold px-2 py-1 rounded-full bg-verdict-misleading/15 text-verdict-misleading border border-verdict-misleading/40">
              Conflicting Sources
            </span>
          ) : null}
        </div>
      </div>

      {summary ? (
        <p className="text-sm text-text-secondary leading-relaxed border-l-2 border-accent-blue pl-3">
          {summary}
        </p>
      ) : null}
      
      <div className="pt-4 border-t border-border-dim">
        <ConfidenceMeter confidence={confidence} />
      </div>
    </div>
  );
};