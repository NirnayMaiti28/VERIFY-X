import { ShieldAlert } from 'lucide-react';

export const Footer = () => {
  return (
    <footer className="border-t border-border-dim bg-background-primary py-8 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-6">
        
        {/* Brand & Copyright */}
        <div className="flex flex-col gap-1 text-center md:text-left">
          <span className="text-sm font-semibold text-text-primary">Headline Verifier</span>
          <span className="text-xs text-text-muted">
            © {new Date().getFullYear()} Open Source Fact-Checking
          </span>
        </div>

        {/* Disclaimer Box */}
        <div className="flex items-start gap-3 max-w-lg text-xs text-text-secondary bg-background-secondary p-3 rounded-lg border border-border-dim">
          <ShieldAlert className="h-5 w-5 text-verdict-uncertain shrink-0 mt-0.5" />
          <p leading-relaxed="true">
            <strong className="text-text-primary">Disclaimer:</strong> This tool utilizes experimental NLP models and automated web scraping. Verdicts and confidence scores are for informational purposes only and may not be entirely accurate. Always cross-reference critical claims with trusted sources.
          </p>
        </div>

      </div>
    </footer>
  );
};