import { useMutation } from '@tanstack/react-query';
import { verifyHeadline } from '../api/verifyApi';

export const useVerification = () => {
  return useMutation({
    mutationFn: (claim) => verifyHeadline(claim),
    // Optional: Add logging or global error handling here in the future
    onError: (error) => {
      if (import.meta.env.DEV) {
        console.error('Verification failed:', error);
      }
    },
  });
};