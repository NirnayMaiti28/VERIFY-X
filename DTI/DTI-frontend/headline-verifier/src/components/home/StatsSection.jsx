export const StatsSection = () => {
  const STATS = [
    { value: '10,000+', label: 'Trusted Sources Indexed' },
    { value: '< 15s', label: 'Average Verification Time' },
    { value: '6', label: 'Nuanced Verdict Types' },
  ];

  return (
    <section className="py-12 bg-background-secondary border-y border-border-dim">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 divide-y md:divide-y-0 md:divide-x divide-border-emphasis">
          {STATS.map((stat, index) => (
            <div key={index} className="flex flex-col items-center text-center pt-6 md:pt-0 first:pt-0">
              <span className="text-4xl font-black text-text-primary tracking-tight mb-2">{stat.value}</span>
              <span className="text-sm font-medium text-text-muted uppercase tracking-wider">{stat.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};