import { useState, useEffect } from 'react';
import { Loader2, Terminal } from 'lucide-react';

const STATUS_MESSAGES = [
  'Fetching live sources...',
  'Computing agreement signal...',
  'Querying Ollama for verdict...',
  'Scoring confidence factors...',
  'Preparing structured output...'
];

export const LoadingState = () => {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % STATUS_MESSAGES.length);
    }, 2200);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full p-8 md:p-12 bg-background-card rounded-xl border border-border-default shadow-sm flex flex-col items-center justify-center min-h-[300px] animate-in fade-in duration-300">
      <div className="relative flex items-center justify-center mb-6">
        <div className="absolute inset-0 bg-accent-blue/20 blur-xl rounded-full animate-pulse" />
        <div className="h-16 w-16 bg-background-secondary border border-border-emphasis rounded-full flex items-center justify-center relative z-10 shadow-inner">
          <Loader2 className="h-8 w-8 text-accent-blue animate-spin" />
        </div>
      </div>

      <div className="flex flex-col items-center gap-2 text-center">
        <div className="flex items-center gap-2 text-sm font-mono text-accent-blue bg-accent-blue/10 px-3 py-1 rounded border border-accent-blue/20">
          <Terminal className="h-4 w-4" />
          <span>Verification in progress</span>
        </div>

        <h3 className="text-xl font-semibold text-text-primary mt-2 transition-opacity duration-300">
          {STATUS_MESSAGES[messageIndex]}
        </h3>

        <p className="text-sm text-text-muted mt-1 max-w-sm">
          We are checking trusted sources and building an explainable verdict. This can take up to 60 seconds.
        </p>
      </div>

      <div className="w-full max-w-xs h-1.5 bg-background-secondary rounded-full mt-8 overflow-hidden border border-border-dim">
        <div className="h-full bg-accent-blue w-full animate-[loading_2s_ease-in-out_infinite] origin-left" />
      </div>
    </div>
  );
};
