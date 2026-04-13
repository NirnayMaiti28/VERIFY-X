import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"
GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _env_float(name, default):
	value = os.getenv(name)
	if value is None:
		return float(default)

	try:
		return float(value)
	except (TypeError, ValueError):
		return float(default)


def _env_int(name, default):
	value = os.getenv(name)
	if value is None:
		return int(default)

	try:
		return int(value)
	except (TypeError, ValueError):
		return int(default)


VERDICT_TRUE_THRESHOLD = _env_float("VERDICT_TRUE_THRESHOLD", 0.45)
VERDICT_FALSE_THRESHOLD = _env_float("VERDICT_FALSE_THRESHOLD", 0.40)
VERDICT_UNVERIFIED_CAP = _env_float("VERDICT_UNVERIFIED_CAP", 0.50)
VERDICT_ABSTAIN_MIN_CONFIDENCE = _env_float("VERDICT_ABSTAIN_MIN_CONFIDENCE", 0.25)

RETRIEVAL_TIME_BUDGET_SECONDS = _env_int("RETRIEVAL_TIME_BUDGET_SECONDS", 14)

# NHTM (Hybrid Truth Scoring Model) parameters
NHTM_BETA = _env_float("NHTM_BETA", 0.8)            # source reliability exponent
NHTM_GAMMA = _env_float("NHTM_GAMMA", 0.6)           # consensus exponent
NHTM_LAMBDA = _env_float("NHTM_LAMBDA", 1.5)         # contradiction dampening exponent
NHTM_DECAY_RATE = _env_float("NHTM_DECAY_RATE", 0.005)  # exponential time decay α
NHTM_PRIOR = _env_float("NHTM_PRIOR", 0.5)           # Bayesian prior P(T)