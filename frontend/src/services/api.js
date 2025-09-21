// services/api.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000 ,
});

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log('Making request to:', config.url);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'An unexpected error occurred';

    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      if (status === 503) {
        message = 'Service unavailable. Please try again later.';
      } else if (status === 429 || data?.error?.includes('quota')) {
        message = `You exceeded your current quota. Please check your plan and billing details. For more information: https://ai.google.dev/gemini-api/docs/rate-limits.`;
      } else if (data?.message) {
        message = data.message;
      } else if (data?.error) {
        message = data.error;
      } else {
        message = `Request failed with status ${status}`;
      }
    } else if (error.request) {
      message = 'No response received from server. Please check your connection.';
    } else {
      message = error.message;
    }

    console.error('API Error:', message);
    return Promise.reject({ ...error, message });
  }
);

export const financeAPI = {
  // Health check
  healthCheck: async () => {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      throw new Error('API is not available');
    }
  },

  // Upload bank statement
  uploadStatement: async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return api.post('/upload-statement', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    });
  },

  // Categorize transactions
    categorizeTransactions: async (transactions) => {
    const response = await api.get('/categorize-transactions');
    return response;
  },

  // categorizeTransactions: async (transactions) => {
  //   const response = await api.post('/categorize-transactions',{transactions});
  //   return response;
  // },


  // Generate insights
  generateInsights: async () => {
    return api.get('/generate-insights');
  },
};

export default api;
