import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 0,
  headers: { 'Content-Type': 'application/json' },
});

export const verifyHeadline = async (claim) => {
  try {
    const response = await apiClient.post('/api/v1/verify', { claim });
    return response.data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response) {
      throw err.response.data;
    }
    throw err;
  }
};

export const verifyImage = async (file, claim = null) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (claim) {
      formData.append('claim', claim);
    }
    
    const response = await apiClient.post('/api/v1/verify-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  } catch (err) {
    if (axios.isAxiosError(err) && err.response) {
      throw err.response.data;
    }
    throw err;
  }
};