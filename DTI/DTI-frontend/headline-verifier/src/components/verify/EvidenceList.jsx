import { useState, useMemo } from 'react';
import { EvidenceCard } from './EvidenceCard';
import { BookOpen, Filter, ArrowDownWideNarrow } from 'lucide-react';

export const EvidenceList = ({ sources = [] }) => {
  const [sortBy, setSortBy] = useState('relevance');
  const [filterCredibility, setFilterCredibility] = useState('All');

  const uniqueCredibility = useMemo(() => {
    const values = sources.map((s) => s.credibility).filter(Boolean);
    return ['All', ...new Set(values)];
  }, [sources]);

  const filteredAndSorted = useMemo(() => {
    let result = [...sources];

    if (filterCredibility !== 'All') {
      result = result.filter((s) => s.credibility === filterCredibility);
    }

    return result.sort((a, b) => {
      if (sortBy === 'relevance') {
        const rank = { High: 3, Medium: 2, Low: 1 };
        return (rank[b.credibility] || 0) - (rank[a.credibility] || 0);
      }
      return (a.title || '').localeCompare(b.title || '');
    });
  }, [sources, sortBy, filterCredibility]);

  if (!sources || sources.length === 0) {
    return (
      <div className="p-8 text-center bg-background-card rounded-xl border border-border-default border-dashed animate-in fade-in duration-500 delay-300 fill-mode-both">
        <BookOpen className="h-8 w-8 text-text-muted mx-auto mb-3 opacity-50" />
        <p className="text-text-secondary text-sm">No sources retrieved</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-500 delay-300 fill-mode-both">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-text-muted" />
          Source Evidence ({sources.length})
        </h3>

        <div className="flex items-center gap-3">
          <div className="relative flex items-center">
            <Filter className="h-3.5 w-3.5 text-text-muted absolute left-2.5" />
            <select
              value={filterCredibility}
              onChange={(e) => setFilterCredibility(e.target.value)}
              className="pl-8 pr-8 py-1.5 bg-background-secondary border border-border-default rounded-lg text-xs font-medium text-text-primary focus:outline-none focus:border-accent-blue appearance-none cursor-pointer"
            >
              {uniqueCredibility.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </div>

          <div className="relative flex items-center">
            <ArrowDownWideNarrow className="h-3.5 w-3.5 text-text-muted absolute left-2.5" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="pl-8 pr-8 py-1.5 bg-background-secondary border border-border-default rounded-lg text-xs font-medium text-text-primary focus:outline-none focus:border-accent-blue appearance-none cursor-pointer"
            >
              <option value="relevance">Highest Credibility</option>
              <option value="title">Title A-Z</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredAndSorted.map((item, idx) => (
          <EvidenceCard key={idx} evidence={item} />
        ))}
      </div>

      {filteredAndSorted.length === 0 && (
        <div className="p-8 text-center bg-background-secondary rounded-xl border border-border-dim col-span-full">
          <p className="text-text-secondary text-sm">No sources match the selected filter.</p>
        </div>
      )}
    </div>
  );
};
