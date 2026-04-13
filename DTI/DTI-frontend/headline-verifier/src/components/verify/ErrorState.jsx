import { AlertTriangle, Clock, WifiOff, RefreshCcw } from 'lucide-react';
import { Button } from '../ui/Button';

export const ErrorState = ({ error, onRetry }) => {
  const status = error?.response?.status ?? error?.status;
  const detail = error?.response?.data?.detail || error?.message;

  let icon = <AlertTriangle className="h-8 w-8 text-verdict-false" />;
  let title = "Verification Failed";
  let message = detail || error?.detail || "An unexpected error occurred while verifying the claim.";

  if (status === 422) {
    icon = <AlertTriangle className="h-8 w-8 text-verdict-uncertain" />;
    title = "Invalid Claim";
    message = detail || "Please enter a valid claim between 1 and 500 characters.";
  } else if (status === 429) {
    icon = <Clock className="h-8 w-8 text-verdict-uncertain" />;
    title = "Rate Limit Exceeded";
    message = detail || "You have reached the limit of 10 requests per minute. Please wait a moment before trying again.";
  } else if (status === 504 || error?.code === 'ECONNABORTED' || String(message).toLowerCase().includes('timeout')) {
    icon = <Clock className="h-8 w-8 text-verdict-uncertain" />;
    title = "Request Timed Out";
    message = detail || "The verification engine took too long to respond. The claim might be too complex or sources are currently slow.";
  } else if (status === 500) {
    icon = <AlertTriangle className="h-8 w-8 text-verdict-false" />;
    title = "Server Error";
    message = detail || "Verification failed due to a server error. Please try again.";
  } else if (message === 'Network Error') {
    icon = <WifiOff className="h-8 w-8 text-text-muted" />;
    title = "Connection Error";
    message = "Unable to reach the verification servers. Please check your internet connection and try again.";
  }

  return (
    <div className="p-8 md:p-12 text-center bg-background-card rounded-xl border border-border-emphasis flex flex-col items-center animate-in fade-in zoom-in-95 duration-300">
      <div className="h-16 w-16 bg-background-primary rounded-full flex items-center justify-center mb-4 border border-border-dim shadow-sm">
        {icon}
      </div>
      
      <h3 className="text-xl font-bold text-text-primary mb-2">{title}</h3>
      <p className="text-text-secondary max-w-md mx-auto mb-6 text-sm leading-relaxed">{message}</p>
      
      {onRetry && (
        /* REFACTORED BUTTON HERE */
        <Button onClick={onRetry} variant="secondary">
          <RefreshCcw className="h-4 w-4" /> Try Again
        </Button>
      )}
    </div>
  );
};