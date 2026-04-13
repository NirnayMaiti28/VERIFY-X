import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';

const SAMPLES = [
  "NASA confirmed the discovery of a parallel universe where time runs backwards.",
  "Eating dark chocolate every day reduces the risk of heart disease by 50%.",
  "The Eiffel Tower shrinks by about 6 inches during the winter due to thermal contraction.",
  "New AI model successfully passed the bar exam in all 50 US states."
];

export const SampleClaimsSection = () => {
  return (
    <section className="py-20 bg-background-primary">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-text-primary">Try an Example</h2>
          <p className="text-text-secondary mt-4">Select a sample headline below to see the verifier in action.</p>
        </div>

        <div className="flex flex-col gap-4">
          {SAMPLES.map((claim, index) => (
            <Link
              key={index}
              to="/verify"
              state={{ claim }} 
              className="group flex items-center justify-between p-5 bg-background-card hover:bg-background-hover border border-border-default hover:border-accent-blue/50 rounded-xl transition-all duration-200"
            >
              <span className="text-text-primary font-medium pr-4 line-clamp-1">{claim}</span>
              <ArrowUpRight className="h-5 w-5 text-text-muted group-hover:text-accent-blue shrink-0 transition-colors" />
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
};