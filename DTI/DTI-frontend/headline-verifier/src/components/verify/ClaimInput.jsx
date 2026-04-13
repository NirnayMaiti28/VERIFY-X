import { useState, useEffect } from 'react';
import { Search } from 'lucide-react';
import { Button } from '../ui/Button';

export const ClaimInput = ({ initialClaim = '', onSubmit, isLoading }) => {
  const [claim, setClaim] = useState(initialClaim);
  const maxLength = 500;

  useEffect(() => {
    setClaim(initialClaim);
  }, [initialClaim]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (claim.trim() && !isLoading) {
      onSubmit(claim.trim());
    }
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3">
      <div className="relative flex flex-col bg-background-card border border-border-default focus-within:border-accent-blue rounded-xl transition-colors duration-200 shadow-sm overflow-hidden">
        
        <textarea
          value={claim}
          onChange={(e) => setClaim(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={maxLength}
          placeholder="Paste a news headline or claim to verify..."
          disabled={isLoading}
          className="w-full min-h-[120px] p-5 bg-transparent text-text-primary placeholder:text-text-muted resize-none focus:outline-none disabled:opacity-50"
          autoFocus
        />
        
        <div className="flex items-center justify-between px-5 py-3 bg-background-secondary/50 border-t border-border-dim">
          <div className="text-xs text-text-muted flex items-center gap-4">
            <span className={`${claim.length >= maxLength ? 'text-verdict-false' : ''}`}>
              {claim.length} / {maxLength}
            </span>
            <span className="hidden sm:inline-flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 rounded bg-background-hover border border-border-default font-mono text-[10px]">Ctrl</kbd> + <kbd className="px-1.5 py-0.5 rounded bg-background-hover border border-border-default font-mono text-[10px]">Enter</kbd> to submit
            </span>
          </div>
          
          {/* REFACTORED BUTTON HERE */}
          <Button 
            type="submit" 
            disabled={!claim.trim()} 
            isLoading={isLoading}
          >
            {!isLoading && <Search className="h-4 w-4" />}
            {isLoading ? 'Analyzing...' : 'Verify'}
          </Button>
        </div>

      </div>
    </form>
  );
};