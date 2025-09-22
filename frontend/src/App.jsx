import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, 
  BarChart3, 
  Brain, 
  CheckCircle, 
  TrendingUp,
  Wallet,
  PieChart,
  FileText
} from 'lucide-react';

// Components
import FileUpload from './components/FileUpload';
import TransactionList from './components/TransactionList';
import InsightsPanel from './components/InsightsPanel';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import { 
  CategoryPieChart, 
  CategoryBarChart, 
  MonthlyTrendChart,
  DailySpendingChart 
} from './components/Charts';

// Services
import { financeAPI } from './services/api';

// Utils
import { 
  formatCurrency, 
  calculateCategoryTotals, 
} from './utils/helpers';
function App() {
  // State management
  const [currentStep, setCurrentStep] = useState('upload');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [transactions, setTransactions] = useState([]);
  const [categorizedTransactions, setCategorizedTransactions] = useState([]);
  const [categorySummary, setCategorySummary] = useState({});
  
  const [insights, setInsights] = useState(null);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [apiHealthy, setApiHealthy] = useState(null);

  // Steps configuration
  const steps = [
    { id: 'upload', title: 'Upload', icon: Upload, description: 'Upload your bank statement' },
    { id: 'categorize', title: 'Categorize', icon: BarChart3, description: 'AI categorizes transactions' },
    { id: 'insights', title: 'Insights', icon: Brain, description: 'Generate financial insights' },
    { id: 'results', title: 'Results', icon: CheckCircle, description: 'View your financial overview' },
  ];

  // Check API health on mount
  useEffect(() => {
    checkApiHealth();
  }, []);

  const checkApiHealth = async () => {
    try {
      await financeAPI.healthCheck();
      setApiHealthy(true);
    } catch (error) {
      setApiHealthy(false);
      console.error('API health check failed:', error);
    }
  };

  // Handle file selection
  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setError('');
    if (file) {
      handleFileUpload(file);
    }
  };

  // Handle file upload
  const handleFileUpload = async (file) => {
    setIsUploading(true);
    setUploadProgress(0);
    setError('');

    try {
      const response = await financeAPI.uploadStatement(file, (progress) => {
        setUploadProgress(progress);
      });

      setTransactions(response.data.transactions);
      setCurrentStep('categorize');
      
      // Auto-start categorization
      setTimeout(() => {
        handleCategorizeTransactions(response.data.transactions);
      }, 1000);

    } catch (error) {
      setError(error.response?.data?.message || 'Failed to upload file. Please try again.');
      setCurrentStep('upload');
      setSelectedFile(null);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  // Handle transaction categorization
  const handleCategorizeTransactions = async (transactions) => {
    setIsProcessing(true);
    setError('');

    try {
      const response = await financeAPI.categorizeTransactions(transactions);
      
      setCategorizedTransactions(response.data.categorized_transactions);
      setCategorySummary(response.data.category_summary);
     
      setCurrentStep('insights');

      // Auto-start insights generation
      setTimeout(() => {
        handleGenerateInsights();
      }, 1000);

    } catch (error) {
      console.log("I am here");
      
      // If AI categorization fails, use basic categorization
      const basicCategorized = transactions.map(transaction => ({
        ...transaction,
        category: 'Uncategorized'
      }));
      
      setCategorizedTransactions(basicCategorized);
      const basicSummary = calculateCategoryTotals(basicCategorized);
      setCategorySummary(basicSummary);
      setCurrentStep('results');
      
      console.warn('AI categorization failed, using basic categorization:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle insights generation
  const handleGenerateInsights = async () => {
    setIsProcessing(true);

    try {
      const response = await financeAPI.generateInsights();
      setInsights(response.data.insights);
      setCurrentStep('results');
    } catch (error) {
      // Continue to results even if insights fail
      setCurrentStep('results');
      console.warn('Insights generation failed:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Reset to start over
  const handleReset = () => {
    setCurrentStep('upload');
    setSelectedFile(null);
    setTransactions([]);
    setCategorizedTransactions([]);
    setCategorySummary({});
    setInsights(null);
    setError('');
    setIsProcessing(false);
    setIsUploading(false);
    setUploadProgress(0);
  };

  // Step Progress Component
  const StepProgress = () => (
    <div className="mb-8">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isActive = step.id === currentStep;
          const isCompleted = steps.findIndex(s => s.id === currentStep) > index;
          const StepIcon = step.icon;

          return (
            <div key={step.id} className="flex flex-col items-center flex-1">
              <div className="flex items-center w-full">
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300
                    ${isCompleted 
                      ? 'bg-green-500 border-green-500 text-white' 
                      : isActive 
                        ? 'bg-blue-500 border-blue-500 text-white'
                        : 'bg-gray-100 border-gray-300 text-gray-400'
                    }
                  `}
                >
                  <StepIcon className="w-5 h-5" />
                </motion.div>
                
                {index < steps.length - 1 && (
                  <div 
                    className={`
                      flex-1 h-0.5 mx-4 transition-all duration-500
                      ${isCompleted ? 'bg-green-500' : 'bg-gray-300'}
                    `}
                  />
                )}
              </div>
              
              <div className="text-center mt-2">
                <p className={`text-sm font-medium ${isActive ? 'text-blue-600' : isCompleted ? 'text-green-600' : 'text-gray-500'}`}>
                  {step.title}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  // Stats Cards Component
  const StatsCards = () => {
  
  // const totalIncome = categorizedTransactions
  //   .filter(t => t.type === "credit")
  //   .reduce((sum, t) => sum + t.amount, 0);

  const lastTransaction = categorizedTransactions[categorizedTransactions.length - 1];
  const totalIncome = lastTransaction.balance;

  const totalExpenses = categorizedTransactions
    .filter(t => t.type === "debit")
    .reduce((sum, t) => sum + t.amount, 0);

  const transactionCount = categorizedTransactions.length;
  const categoryCount = Object.keys(categorySummary).length;

  const stats = [
    { title: "Current Balance", value: formatCurrency(totalIncome), icon: TrendingUp, color: "green" },
    { title: "Total Expenses", value: formatCurrency(totalExpenses), icon: Wallet, color: "red" },
    { title: "Transactions", value: transactionCount.toString(), icon: FileText, color: "blue" },
    { title: "Categories", value: categoryCount.toString(), icon: PieChart, color: "purple" },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {stats.map((stat, index) => {
        const StatIcon = stat.icon;
        return (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="bg-white p-6 rounded-xl card-shadow"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 mb-1">{stat.title}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
              <div
                className={`p-3 rounded-lg ${
                  stat.color === "green"
                    ? "bg-green-100 text-green-600"
                    : stat.color === "red"
                    ? "bg-red-100 text-red-600"
                    : stat.color === "purple"
                    ? "bg-purple-100 text-purple-600"
                    : "bg-blue-100 text-blue-600"
                }`}
              >
                <StatIcon className="w-6 h-6" />
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};


  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <Wallet className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-xl font-bold text-gray-900">
                Finance Manager
              </h1>
            </div>
            
            {currentStep === 'results' && (
              <button
                onClick={handleReset}
                className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              >
                Start Over
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* API Health Warning */}
        {apiHealthy === false && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-xl"
          >
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Brain className="w-5 h-5 text-yellow-600" />
              </div>
              <div>
                <h3 className="font-medium text-yellow-900">Backend API Not Available</h3>
                <p className="text-sm text-yellow-700 mt-1">
                  The AI categorization and insights features require the backend API. 
                  You can still explore the UI with sample data.
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {/* Step Progress */}
        <StepProgress />

        {/* Content based on current step */}
        <AnimatePresence mode="wait">
          {/* Upload Step */}
          {currentStep === 'upload' && (
            <motion.div
              key="upload-step"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="text-center"
            >
              <div className="max-w-3xl mx-auto">
                <h2 className="text-3xl font-bold text-gray-900 mb-4">
                  Upload Your Bank Statement
                </h2>
                <p className="text-lg text-gray-600 mb-8">
                  Get AI-powered insights into your spending patterns and financial habits
                </p>
                
                <FileUpload
                  onFileSelect={handleFileSelect}
                  isUploading={isUploading}
                  uploadProgress={uploadProgress}
                />
                
                {error && (
                  <div className="mt-6">
                    <ErrorMessage 
                      message={error} 
                      onRetry={() => selectedFile && handleFileUpload(selectedFile)}
                    />
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Processing Steps */}
          {(currentStep === 'categorize' || currentStep === 'insights') && (
            <motion.div
              key="processing-step"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="text-center max-w-lg mx-auto"
            >
              <div className="bg-white p-8 rounded-xl card-shadow">
                <LoadingSpinner 
                  message={
                    currentStep === 'categorize' 
                      ? "AI is categorizing your transactions..." 
                      : "Generating personalized insights..."
                  }
                  size="large"
                />
                
                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-700">
                    {currentStep === 'categorize' 
                      ? `Processing ${transactions.length} transactions with AI categorization`
                      : "Analyzing spending patterns and generating recommendations"
                    }
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Results Step */}
          {currentStep === 'results' && (
            <motion.div
              key="results-step"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-8"
            >
              {/* Stats Overview */}
              <StatsCards />

              {/* Charts Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <CategoryPieChart data={categorySummary} />
                <CategoryBarChart data={categorySummary} />
                <MonthlyTrendChart transactions={categorizedTransactions} />
                <DailySpendingChart transactions={categorizedTransactions} />
              </div>

              {/* Insights and Transactions */}
              <div className="grid grid-cols-1  gap-6">
                <div className="xl:col-span-1">
                  <InsightsPanel 
                    insights={insights}
                    transactions={categorizedTransactions}
                    categorySummary={categorySummary}
                  />
                </div>
                <div className="xl:col-span-2">
                  <TransactionList 
                    transactions={categorizedTransactions}
                    categorySummary={categorySummary}
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <p className="text-gray-500">
              Built with React, Tailwind CSS, and AI-powered categorization
            </p>
            <p className="text-sm text-gray-400 mt-2">
              Your financial data is processed securely and never stored permanently
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;