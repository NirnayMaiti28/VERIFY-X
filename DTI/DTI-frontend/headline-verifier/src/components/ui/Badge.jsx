export const Badge = ({ children, variant = 'default', className = '' }) => {
  const variants = {
    default: "bg-background-secondary text-text-secondary border-border-default",
    blue: "bg-accent-blue/10 text-accent-blue border-accent-blue/20",
    success: "bg-verdict-true/10 text-verdict-true border-verdict-true/30",
    custom: "", // Added this to allow completely custom color injection
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
};