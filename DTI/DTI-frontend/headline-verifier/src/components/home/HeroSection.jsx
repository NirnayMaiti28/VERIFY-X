import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { Badge } from '../ui/Badge';

export const HeroSection = () => {
  return (
    <section className="relative overflow-hidden py-20 sm:py-32 flex flex-col items-center text-center px-4">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-accent-blue/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="relative z-10 max-w-4xl mx-auto flex flex-col items-center gap-6">
        <Badge variant="default" className="gap-2 px-3 py-1 mb-4 text-sm font-normal">
          <ShieldCheck className="h-4 w-4 text-verdict-true" />
          <span>Powered by Retrieval + Ollama + Explainable Scoring</span>
        </Badge>

        <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight text-text-primary">
          Verify the <span className="text-accent-blue">News</span>.<br />
          Trust the <span className="text-text-muted">Evidence</span>.
        </h1>

        <p className="max-w-2xl text-lg sm:text-xl text-text-secondary leading-relaxed mt-4">
          Instantly validate claims with a transparent pipeline: live retrieval, agreement signals, LLM reasoning, and confidence breakdown.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mt-8">
          <Link
            to="/verify"
            className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-accent-blue hover:bg-accent-blue-dim text-white rounded-lg font-semibold transition-colors duration-200"
          >
            Start Verifying <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </div>
    </section>
  );
};
