export const ConfidenceBreakdownPanel = ({ breakdown }) => {
  if (!breakdown) return null;

  const rows = [
    { key: 'llm', label: 'LLM' },
    { key: 'agreement', label: 'Agreement' },
    { key: 'consistency', label: 'Consistency' },
    { key: 'credibility', label: 'Credibility' },
    { key: 'diversity', label: 'Diversity' },
  ];

  return (
    <div className="p-5 bg-background-secondary rounded-xl border border-border-dim animate-in fade-in duration-500">
      <h3 className="text-sm font-bold text-text-primary uppercase tracking-wide mb-4">Confidence Breakdown</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rows.map((row) => {
          const value = Math.max(0, Math.min(1, Number(breakdown[row.key] || 0)));
          const pct = Math.round(value * 100);
          return (
            <div key={row.key} className="flex flex-col gap-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-text-secondary">{row.label}</span>
                <span className="text-text-primary font-semibold">{pct}%</span>
              </div>
              <div className="h-2 w-full bg-background-primary rounded-full overflow-hidden border border-border-dim">
                <div className="h-full bg-accent-blue transition-all duration-700" style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
