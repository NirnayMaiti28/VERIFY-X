import { ExternalLink, Link as LinkIcon } from 'lucide-react';
import { Badge } from '../ui/Badge';

export const EvidenceCard = ({ evidence }) => {
  const { title, snippet, credibility, url } = evidence;

  const credibilityStyle = {
    High: 'text-verdict-true border-verdict-true/40 bg-verdict-true/10',
    Medium: 'text-verdict-misleading border-verdict-misleading/40 bg-verdict-misleading/10',
    Low: 'text-verdict-false border-verdict-false/40 bg-verdict-false/10',
  };

  return (
    <div className="p-5 bg-background-secondary rounded-xl border border-border-dim hover:border-border-emphasis transition-colors flex flex-col gap-3 h-full">
      <div className="flex items-start justify-between gap-4">
        <h4 className="text-sm md:text-base font-semibold text-text-primary line-clamp-2 flex-1">
          {title ?? 'Title unavailable'}
        </h4>
        <Badge variant="custom" className={`font-semibold ${credibilityStyle[credibility] || credibilityStyle.Medium}`}>
          {credibility || 'Medium'}
        </Badge>
      </div>

      <p className="text-sm text-text-secondary line-clamp-3 leading-relaxed flex-1">
        {snippet ?? 'No snippet available'}
      </p>

      <div className="flex items-center justify-end pt-3 mt-4 border-t border-border-dim">
        {url ? (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-bold text-text-primary hover:text-accent-blue transition-colors"
          >
            Read Source <ExternalLink className="h-3.5 w-3.5" />
          </a>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs text-text-muted">
            <LinkIcon className="h-3.5 w-3.5" /> No link
          </span>
        )}
      </div>
    </div>
  );
};
