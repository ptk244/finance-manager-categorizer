// utils/helpers.js

// Currency formatting for INR
export const formatCurrency = (amount, currency = 'INR') => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
  }).format(Math.abs(amount));
};

// Date formatting
export const formatDate = (dateString) => {
  const transaction_date = new Date(dateString);
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(transaction_date);
};

// Generate colors for categories
export const getCategoryColor = (category, index = 0) => {
  const categoryColors = {
    'Income': '#10B981', // Green
    'Transfer': '#6B7280', // Gray
    'Shopping': '#EC4899', // Pink
    'Bills & Utilities': '#F59E0B', // Amber
    'Groceries': '#84CC16', // Lime
    'Food & Dining': '#EF4444', // Red
    'Transportation': '#3B82F6', // Blue
    'Entertainment': '#8B5CF6', // Purple
    'Healthcare': '#06B6D4', // Cyan
    'Education': '#F97316', // Orange
    'Investment': '#14B8A6', // Teal
    'Insurance': '#8B5A2B', // Brown
  };

  const defaultColors = [
    '#8B5CF6', '#06B6D4', '#10B981', '#F59E0B', '#EF4444', 
    '#F97316', '#84CC16', '#3B82F6', '#EC4899', '#6B7280', 
    '#14B8A6', '#8B5A2B'
  ];

  return categoryColors[category] || defaultColors[index % defaultColors.length] || defaultColors[0];
};

// File validation
export const validateFile = (file) => {
  const maxSize = 10 * 1024 * 1024; // 10MB
  const allowedTypes = [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/pdf',
  ];

  if (file.size > maxSize) {
    throw new Error('File size must be less than 10MB');
  }

  if (!allowedTypes.includes(file.type)) {
    throw new Error('Only CSV, Excel, and PDF files are allowed');
  }

  return true;
};

// Calculate percentage
export const calculatePercentage = (value, total) => {
  if (total === 0) return 0;
  return Math.round((Math.abs(value) / Math.abs(total)) * 100);
};

// Get transaction type color
export const getTransactionTypeColor = (amount) => {
  return amount >= 0 ? 'text-green-600' : 'text-red-600';
};

// Truncate text
export const truncateText = (text, maxLength = 30) => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

// Generate month name from transaction_date
export const getMonthName = (dateString) => {
  const transaction_date = new Date(dateString);
  return transaction_date.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
};

// Sort transactions by transaction_date
export const sortTransactionsByDate = (transactions, ascending = false) => {
  return [...transactions].sort((a, b) => {
    const dateA = new Date(a.transaction_date);
    const dateB = new Date(b.transaction_date);
    return ascending ? dateA - dateB : dateB - dateA;
  });
};

// Group transactions by category
export const groupTransactionsByCategory = (transactions) => {
  return transactions.reduce((groups, transaction) => {
    const category = transaction.category || 'Uncategorized';
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(transaction);
    return groups;
  }, {});
};

// Calculate total spending by category - Updated to work with API response
export const calculateCategoryTotals = (transactions) => {
  const categoryTotals = {};
  
  transactions.forEach((transaction) => {
    const category = transaction.category || 'Uncategorized';
    const amount = transaction.amount; // Keep original sign for income/expense distinction
    
    if (!categoryTotals[category]) {
      categoryTotals[category] = 0;
    }
    categoryTotals[category] += amount;
  });
  
  return categoryTotals;
};

// Process API category summary - Convert API format to component format
export const processCategorySummary = (apiCategorySummary) => {
  const processed = {};
  
  Object.entries(apiCategorySummary).forEach(([category, data]) => {
    // Use total_amount from API response, maintain sign for income/expense
    processed[category] = data.total_amount;
  });
  
  return processed;
};

// Format large numbers in Indian style (Lakhs/Crores)
export const formatIndianNumber = (amount) => {
  const absAmount = Math.abs(amount);
  
  if (absAmount >= 10000000) { // 1 Crore
    return `₹${(absAmount / 10000000).toFixed(1)}Cr`;
  } else if (absAmount >= 100000) { // 1 Lakh
    return `₹${(absAmount / 100000).toFixed(1)}L`;
  } else if (absAmount >= 1000) { // 1 Thousand
    return `₹${(absAmount / 1000).toFixed(1)}K`;
  } else {
    return formatCurrency(amount);
  }
};

// Parse transaction amount properly
export const parseTransactionAmount = (transaction) => {
  // Handle both positive and negative amounts properly
  let amount = transaction.amount;
  
  // If transaction type is specified, use it to determine sign
  if (transaction.type) {
    if (transaction.type === 'debit' && amount > 0) {
      amount = -amount; // Debits should be negative
    } else if (transaction.type === 'credit' && amount < 0) {
      amount = Math.abs(amount); // Credits should be positive
    }
  }
  
  return {
    ...transaction,
    amount: amount,
    originalAmount: transaction.amount
  };
};