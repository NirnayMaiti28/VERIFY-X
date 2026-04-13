import { useState } from 'react';
import { Info, ChevronDown, ChevronUp } from 'lucide-react';

export const ExplanationBlock = ({ explanation }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Guard: if no explanation provided, render nothing
  if (!explanation) return null;

  const LIMIT = 300;
  const isLong = explanation.length > LIMIT;
  const displayText = !isLong || isExpanded ? explanation : `${explanation.substring(0, LIMIT)}...`;

  return (
    <div className="p-5 bg-background-secondary rounded-xl border border-border-dim animate-in fade-in duration-500 delay-100 fill-mode-both">
      <div className="flex items-start gap-3">
        <Info className="h-5 w-5 text-text-muted mt-0.5 shrink-0" />
        <div className="flex flex-col gap-2 w-full">
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-wide">Reasoning</h3>
          <p className="text-sm text-text-secondary leading-relaxed">
            {displayText}
          </p>
          {isLong && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="inline-flex items-center gap-1 text-xs font-semibold text-accent-blue hover:text-accent-blue-dim self-start transition-colors mt-1"
            >
              {isExpanded ? (
                <>Show less <ChevronUp className="h-3 w-3" /></>
              ) : (
                <>Read full explanation <ChevronDown className="h-3 w-3" /></>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};