import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

export const Button = forwardRef(({ 
  children, 
  className = '', 
  variant = 'primary', 
  size = 'md', 
  isLoading = false, 
  disabled, 
  ...props 
}, ref) => {
  const baseStyles = "inline-flex items-center justify-center font-medium transition-colors focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed rounded-lg";
  
  const variants = {
    primary: "bg-accent-blue hover:bg-accent-blue-dim text-white",
    secondary: "bg-background-secondary hover:bg-background-hover text-text-primary border border-border-default",
    danger: "bg-verdict-false hover:bg-verdict-false/80 text-white",
    ghost: "hover:bg-background-hover text-text-secondary hover:text-text-primary"
  };
  
  const sizes = {
    sm: "text-xs px-3 py-1.5 gap-1.5",
    md: "text-sm px-5 py-2 gap-2",
    lg: "text-base px-8 py-3 gap-2"
  };

  return (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
});

Button.displayName = 'Button';