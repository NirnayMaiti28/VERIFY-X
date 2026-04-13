import { getVerdictConfig } from '../../utils/verdictUtils';
import { Badge } from '../ui/Badge';

export const VerdictBadge = ({ verdict }) => {
  const config = getVerdictConfig(verdict);
  return (
    /* REFACTORED BADGE HERE */
    <Badge 
      variant="custom" 
      className={`uppercase tracking-wider ${config.bg} ${config.color} ${config.border}`}
    >
      {config.label}
    </Badge>
  );
};