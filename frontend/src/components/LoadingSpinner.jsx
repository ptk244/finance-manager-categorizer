// components/LoadingSpinner.jsx
import React from 'react';
import { motion } from 'framer-motion';

const LoadingSpinner = ({ message = "Processing...", size = "default" }) => {
  const spinnerSize = {
    small: "w-6 h-6",
    default: "w-8 h-8", 
    large: "w-12 h-12"
  };

  return (
    <div className="flex flex-col items-center justify-center space-y-4">
      <motion.div
        className={`${spinnerSize[size]} border-4 border-blue-200 border-t-blue-600 rounded-full`}
        animate={{ rotate: 360 }}
        transition={{ 
          duration: 1, 
          repeat: Infinity, 
          ease: "linear" 
        }}
      />
      
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="text-gray-600 text-sm font-medium"
      >
        {message}
      </motion.p>
    </div>
  );
};

export default LoadingSpinner;