export const VERDICT_CONFIG = {
  True: {
    color: 'text-verdict-true',
    bg: 'bg-verdict-true/10',
    border: 'border-verdict-true/30',
    label: 'True',
  },
  False: {
    color: 'text-verdict-false',
    bg: 'bg-verdict-false/10',
    border: 'border-verdict-false/30',
    label: 'False',
  },
  Misleading: {
    color: 'text-verdict-misleading',
    bg: 'bg-verdict-misleading/10',
    border: 'border-verdict-misleading/30',
    label: 'Misleading',
  },
  'Not Enough Information': {
    color: 'text-verdict-nei',
    bg: 'bg-verdict-nei/10',
    border: 'border-verdict-nei/30',
    label: 'Not Enough Information',
  },
};

export const getVerdictConfig = (verdict) => {
  return VERDICT_CONFIG[verdict] || VERDICT_CONFIG['Not Enough Information'];
};
