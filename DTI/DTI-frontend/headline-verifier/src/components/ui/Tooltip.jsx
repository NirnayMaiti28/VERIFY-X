export const Tooltip = ({ children, content, position = 'top' }) => {
  const positions = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <div className="relative group inline-block">
      {children}
      <div className={`absolute z-50 whitespace-nowrap px-2.5 py-1.5 bg-background-card border border-border-emphasis text-text-primary text-xs rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none ${positions[position]}`}>
        {content}
      </div>
    </div>
  );
};