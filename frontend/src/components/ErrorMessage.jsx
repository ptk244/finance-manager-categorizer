// components/ErrorMessage.jsx
import React from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, RefreshCw } from 'lucide-react';

const ErrorMessage = ({ 
  message = "Something went wrong", 
  onRetry, 
  showRetry = true 
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-red-50 border border-red-200 rounded-xl p-6 text-center"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1, type: "spring" }}
        className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4"
      >
        <AlertCircle className="w-8 h-8 text-red-600" />
      </motion.div>
      
      <h3 className="text-lg font-semibold text-red-900 mb-2">
        Oops! Something went wrong
      </h3>
      
      <p className="text-red-700 mb-4">
        {message}
      </p>
      
      {showRetry && onRetry && (
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onRetry}
          className="inline-flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Try Again</span>
        </motion.button>
      )}
    </motion.div>
  );
};

export default ErrorMessage;