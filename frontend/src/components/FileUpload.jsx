// components/FileUpload.jsx
import React, { useCallback, useState } from 'react';
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { validateFile } from '../utils/helpers';

const FileUpload = ({ onFileSelect, isUploading, uploadProgress }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState('');

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    setError('');

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 1) {
      setError('Please select only one file');
      return;
    }

    const file = files[0];
    handleFileSelection(file);
  }, []);

  const handleFileSelection = (file) => {
    try {
      validateFile(file);
      setSelectedFile(file);
      setError('');
      onFileSelect(file);
    } catch (err) {
      setError(err.message);
      setSelectedFile(null);
    }
  };

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileSelection(file);
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    setError('');
    onFileSelect(null);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <AnimatePresence mode="wait">
        {!selectedFile ? (
          <motion.div
            key="upload-zone"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={`
              relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300
              upload-zone cursor-pointer hover:border-blue-400 hover:bg-blue-50/50
              ${isDragOver ? 'border-blue-500 bg-blue-50 scale-102' : 'border-gray-300'}
              ${error ? 'border-red-300 bg-red-50/50' : ''}
            `}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('fileInput').click()}
          >
            <input
              id="fileInput"
              type="file"
              accept=".csv,.xlsx,.xls,.pdf"
              onChange={handleFileInput}
              className="hidden"
            />
            
            <motion.div
              animate={{ scale: isDragOver ? 1.1 : 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <Upload className={`w-16 h-16 mx-auto mb-4 ${error ? 'text-red-400' : 'text-blue-400'}`} />
            </motion.div>
            
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              Upload Your Bank Statement
            </h3>
            
            <p className="text-gray-500 mb-4">
              Drag and drop your file here, or click to select
            </p>
            
            <div className="text-sm text-gray-400">
              Supports CSV, Excel (XLSX/XLS), and PDF files up to 10MB
            </div>
            
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 flex items-center justify-center text-red-600"
              >
                <AlertCircle className="w-4 h-4 mr-2" />
                {error}
              </motion.div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="file-selected"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-white border border-gray-200 rounded-xl p-6 card-shadow"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <File className="w-6 h-6 text-blue-600" />
                </div>
                
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{selectedFile.name}</h4>
                  <p className="text-sm text-gray-500">
                    {formatFileSize(selectedFile.size)} • {selectedFile.type.split('/')[1].toUpperCase()}
                  </p>
                </div>
              </div>
              
              {!isUploading && (
                <button
                  onClick={removeFile}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              )}
            </div>
            
            {isUploading && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="mt-4"
              >
                <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                  <span>Uploading and processing...</span>
                  <span>{uploadProgress}%</span>
                </div>
                
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                    initial={{ width: 0 }}
                    animate={{ width: `${uploadProgress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </motion.div>
            )}
            
            {uploadProgress === 100 && !isUploading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 flex items-center text-green-600"
              >
                <CheckCircle className="w-4 h-4 mr-2" />
                File uploaded successfully!
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FileUpload;