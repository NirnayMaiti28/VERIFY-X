// ─── VERIFY-X 2.0 — API Service ───

import type {
  FeedbackRequest,
  HealthResponse,
  ModelInfoResponse,
  PaginatedResponse,
  TextVerificationRequest,
  VerificationResponse,
  VerificationSummary,
} from '../types/verification';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_PREFIX = `${API_BASE}/api/v1`;

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, message: string, detail: string = '') {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      body.error || response.statusText,
      body.detail || ''
    );
  }

  return response.json();
}

// ── Verification ──

export async function verifyText(
  data: TextVerificationRequest
): Promise<VerificationResponse> {
  return request<VerificationResponse>(`${API_PREFIX}/verify/text`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function verifyImage(
  file: File,
  context?: string,
  language?: string
): Promise<VerificationResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (context) formData.append('context', context);
  if (language) formData.append('language', language);

  const response = await fetch(`${API_PREFIX}/verify/image`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      body.error || response.statusText,
      body.detail || ''
    );
  }

  return response.json();
}

// ── History ──

export async function getHistory(
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<VerificationSummary>> {
  return request<PaginatedResponse<VerificationSummary>>(
    `${API_PREFIX}/history?page=${page}&page_size=${pageSize}`
  );
}

export async function getVerification(
  requestId: string
): Promise<VerificationResponse> {
  return request<VerificationResponse>(
    `${API_PREFIX}/verification/${requestId}`
  );
}

// ── Feedback ──

export async function submitFeedback(
  data: FeedbackRequest
): Promise<{ feedback_id: string; received: boolean }> {
  return request(`${API_PREFIX}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ── Health ──

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>(`${API_PREFIX}/health`);
}

export async function getModels(): Promise<ModelInfoResponse> {
  return request<ModelInfoResponse>(`${API_PREFIX}/models`);
}

export { ApiError };
