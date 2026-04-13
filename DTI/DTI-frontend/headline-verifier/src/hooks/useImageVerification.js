import { useMutation } from '@tanstack/react-query';
import { verifyImage } from '../api/verifyApi';

export const useImageVerification = () => {
  return useMutation({
    mutationFn: ({ file, claim }) => verifyImage(file, claim),
    onError: (error) => {
      if (import.meta.env.DEV) {
        console.error('Image verification failed:', error);
      }
    },
  });
};
