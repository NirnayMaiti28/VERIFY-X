import { FileText, Globe, Cpu, CheckCircle } from 'lucide-react';

const STEPS = [
  {
    icon: FileText,
    title: '1. Input Claim',
    description: 'Enter a factual claim or headline for verification.'
  },
  {
    icon: Globe,
    title: '2. Retrieve Sources',
    description: 'The system fetches recent coverage from Google News and fallback sources.'
  },
  {
    icon: Cpu,
    title: '3. Analyze Agreement',
    description: 'Agreement and contradiction signals are computed before the claim is sent to Ollama.'
  },
  {
    icon: CheckCircle,
    title: '4. Trust Output',
    description: 'Receive verdict, confidence breakdown, explanation, summary, and linked evidence.'
  }
];

export const HowItWorksSection = () => {
  return (
    <section className="py-20 border-t border-border-dim bg-background-primary">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-text-primary">How the Engine Works</h2>
          <p className="text-text-secondary mt-4 max-w-2xl mx-auto">A transparent, production-ready fact-checking workflow.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {STEPS.map((step, index) => {
            const Icon = step.icon;
            return (
              <div key={index} className="flex flex-col items-center text-center p-6 bg-background-card rounded-xl border border-border-default">
                <div className="h-14 w-14 rounded-full bg-background-secondary border border-border-emphasis flex items-center justify-center mb-6">
                  <Icon className="h-6 w-6 text-accent-blue" />
                </div>
                <h3 className="text-xl font-semibold text-text-primary mb-3">{step.title}</h3>
                <p className="text-text-secondary text-sm leading-relaxed">{step.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
