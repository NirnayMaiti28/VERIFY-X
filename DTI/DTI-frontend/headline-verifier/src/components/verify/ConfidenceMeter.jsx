export const ConfidenceMeter = ({ confidence }) => {
  // Ensure we display 0.0-1.0 as 0-100%
  const percentage = Math.round((confidence || 0) * 100);

  return (
    <div className="flex flex-col gap-1.5 w-full">
      <div className="flex justify-between items-center text-xs font-semibold">
        <span className="text-text-secondary uppercase tracking-wide">Confidence Score</span>
        <span className="text-accent-blue">{percentage}%</span>
      </div>
      <div className="h-2 w-full bg-background-secondary rounded-full overflow-hidden">
        <div
          className="h-full bg-accent-blue transition-all duration-1000 ease-out rounded-full"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};