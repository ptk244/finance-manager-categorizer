// components/TransactionList.jsx
import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, 
  Filter, 
  ChevronDown, 
  TrendingUp, 
  TrendingDown,
  Calendar,
  Tag
} from 'lucide-react';
import { formatCurrency, formatDate, getTransactionTypeColor, truncateText, parseTransactionAmount } from '../utils/helpers';

const TransactionList = ({ transactions }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('transaction_date');
  const [sortOrder, setSortOrder] = useState('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Parse transactions to ensure proper amount signs
  const parsedTransactions = useMemo(
    () => transactions.map(t => parseTransactionAmount(t)),
    [transactions]
  );

  // Get unique categories
  const categories = useMemo(() => {
    const cats = ['all', ...new Set(parsedTransactions.map(t => t.category || 'Uncategorized'))];
    return cats;
  }, [parsedTransactions]);

  // Filter and sort transactions
  const filteredTransactions = useMemo(() => {
    let filtered = parsedTransactions.filter(transaction => {
      const matchesSearch = transaction.description
        .toLowerCase()
        .includes(searchTerm.toLowerCase());
      const matchesCategory = selectedCategory === 'all' || 
        (transaction.category || 'Uncategorized') === selectedCategory;
      return matchesSearch && matchesCategory;
    });

    // Sort transactions
    filtered.sort((a, b) => {
      let aValue, bValue;
      switch (sortBy) {
        case 'amount':
          aValue = Math.abs(a.amount);
          bValue = Math.abs(b.amount);
          break;
        case 'description':
          aValue = a.description.toLowerCase();
          bValue = b.description.toLowerCase();
          break;
        case 'category':
          aValue = (a.category || 'Uncategorized').toLowerCase();
          bValue = (b.category || 'Uncategorized').toLowerCase();
          break;
        default:
          aValue = new Date(a.transaction_date);
          bValue = new Date(b.transaction_date);
      }

      if (sortOrder === 'asc') return aValue > bValue ? 1 : -1;
      return aValue < bValue ? 1 : -1;
    });

    return filtered;
  }, [parsedTransactions, searchTerm, selectedCategory, sortBy, sortOrder]);

  // Pagination
  const totalPages = Math.ceil(filteredTransactions.length / itemsPerPage);
  const paginatedTransactions = filteredTransactions.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  return (
    <div className="bg-white rounded-xl shadow overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Transaction History</h2>
            <p className="text-sm text-gray-500 mt-1">{filteredTransactions.length} transactions</p>
          </div>

          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search transactions..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full sm:w-64"
              />
            </div>

            {/* Category Filter */}
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <select
                value={selectedCategory}
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white"
              >
                {categories.map(category => (
                  <option key={category} value={category}>
                    {category === 'all' ? 'All Categories' : category}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
        </div>
      </div>

      {/* Transaction Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('transaction_date')}>
                <div className="flex items-center space-x-1">
                  <Calendar className="w-4 h-4" />
                  <span>Date</span>
                  {sortBy === 'transaction_date' && <ChevronDown className={`w-4 h-4 transition-transform ${sortOrder === 'asc' ? 'rotate-180' : ''}`} />}
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('description')}>
                <div className="flex items-center space-x-1">
                  <span>Description</span>
                  {sortBy === 'description' && <ChevronDown className={`w-4 h-4 transition-transform ${sortOrder === 'asc' ? 'rotate-180' : ''}`} />}
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('category')}>
                <div className="flex items-center space-x-1">
                  <Tag className="w-4 h-4" />
                  <span>Category</span>
                  {sortBy === 'category' && <ChevronDown className={`w-4 h-4 transition-transform ${sortOrder === 'asc' ? 'rotate-180' : ''}`} />}
                </div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('amount')}>
                <div className="flex items-center justify-end space-x-1">
                  <span>Debited Amount</span>
                  {sortBy === 'amount' && <ChevronDown className={`w-4 h-4 transition-transform ${sortOrder === 'asc' ? 'rotate-180' : ''}`} />}
                </div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('amount')}>
                <div className="flex items-center justify-end space-x-1">
                  <span>Credited Amount</span>
                  {sortBy === 'amount' && <ChevronDown className={`w-4 h-4 transition-transform ${sortOrder === 'asc' ? 'rotate-180' : ''}`} />}
                </div>
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => handleSort('amount')}>
                <div className="flex items-center justify-end space-x-1">
                  <span>Amount</span>
                  {sortBy === 'amount' && <ChevronDown className={`w-4 h-4 transition-transform ${sortOrder === 'asc' ? 'rotate-180' : ''}`} />}
                </div>
              </th>
            </tr>
          </thead>

          <tbody className="bg-white divide-y divide-gray-200">
            <AnimatePresence>
              {paginatedTransactions.map((transaction, index) => (
                <motion.tr
                  key={`${transaction.transaction_date}-${transaction.description}-${index}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: index * 0.05 }}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{formatDate(transaction.transaction_date)}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900 font-medium">{truncateText(transaction.description, 40)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      {transaction.category || 'Uncategorized'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className={`text-sm font-semibold flex items-center justify-end space-x-1 ${getTransactionTypeColor(transaction.amount)}`}>
                       <TrendingDown className="w-4 h-4" />
                      <span>{(transaction.debited_amount_inr)}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className={`text-sm font-semibold flex items-center justify-end space-x-1 ${getTransactionTypeColor(transaction.amount)}`}>
                     <TrendingUp className="w-4 h-4" /> 
                      <span>{(transaction.credited_amount_inr)}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className={`text-sm font-semibold flex items-center justify-end space-x-1 ${getTransactionTypeColor(transaction.amount)}`}>
                      <span>{formatCurrency(transaction.current_balance_inr)}</span>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {filteredTransactions.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-3">
            <Search className="w-12 h-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No transactions found</h3>
          <p className="text-gray-500">Try adjusting your search or filter criteria</p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredTransactions.length)} of {filteredTransactions.length} results
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <div className="flex items-center space-x-1">
              {[...Array(Math.min(5, totalPages))].map((_, i) => {
                const pageNum = Math.max(1, currentPage - 2) + i;
                if (pageNum > totalPages) return null;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`px-3 py-1 text-sm rounded-md ${
                      currentPage === pageNum ? 'bg-blue-600 text-white' : 'border border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TransactionList;
