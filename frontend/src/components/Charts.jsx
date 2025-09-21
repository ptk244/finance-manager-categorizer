// components/Charts.jsx
import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Area,
  AreaChart,
} from 'recharts';
import { motion } from 'framer-motion';
import { getCategoryColor, formatCurrency } from '../utils/helpers';

// Custom tooltip for charts
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
        {label && <p className="font-medium text-gray-900 mb-1">{label}</p>}
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {`${entry.dataKey}: ${entry.dataKey.includes('amount') || entry.dataKey.includes('value')
              ? formatCurrency(entry.value)
              : entry.value
            }`}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// Pie Chart Component
export const CategoryPieChart = ({ data, title = "Spending by Category" }) => {
  const chartData = Object.entries(data).map(([category, info], index) => ({
    name: category,
    value: Math.abs(info.total_amount || 0),
    color: getCategoryColor(category, index),
  }));

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white p-6 rounded-xl card-shadow"
    >
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={350}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            outerRadius={120}
            innerRadius={60}
            dataKey="value"
            animationDuration={1000}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      
      {/* Legend */}
      <div className="mt-4 grid grid-cols-2 gap-2">
        {chartData.slice(0, 8).map((entry, index) => (
          <div key={index} className="flex items-center space-x-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-sm text-gray-600 truncate">{entry.name}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
};

// Bar Chart Component
export const CategoryBarChart = ({ data, title = "Category Spending" }) => {
  const chartData = Object.entries(data)
    .map(([category, info], index) => ({
      category: category.length > 12 ? category.substring(0, 12) + '...' : category,
      amount: Math.abs(info.total_amount),
      fill: getCategoryColor(category, index),
    }))
    .sort((a, b) => b.amount - a.amount)
    .slice(0, 8);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white p-6 rounded-xl card-shadow"
    >
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="category" 
            tick={{ fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis 
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => `$${value}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar 
            dataKey="amount" 
            radius={[4, 4, 0, 0]}
            animationDuration={1000}
          />
        </BarChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

// Monthly Spending Trend
export const MonthlyTrendChart = ({ transactions, title = "Spending Trend" }) => {
  // Group transactions by month
  const monthlyData = transactions.reduce((acc, transaction) => {
    const transaction_date = new Date(transaction.transaction_date);
    const monthKey = `${transaction_date.getFullYear()}-${String(transaction_date.getMonth() + 1).padStart(2, '0')}`;
    
    if (!acc[monthKey]) {
      acc[monthKey] = { month: monthKey, income: 0, expenses: 0 };
    }

    // ✅ Use transaction.type instead of amount sign
    if (transaction.type === "credit") {
      acc[monthKey].income += transaction.amount;
    } else if (transaction.type === "debit") {
      acc[monthKey].expenses += transaction.amount;
    }
    
    return acc;
  }, {});

  // Format chart data with readable month names
  const chartData = Object.values(monthlyData).map(item => ({
    ...item,
    month: new Date(item.month + '-01').toLocaleDateString('en-US', { 
      month: 'short', 
      year: 'numeric' 
    })
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white p-6 rounded-xl card-shadow"
    >
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="month" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => `₹${value}`} />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="expenses"
            stackId="1"
            stroke="#EF4444"
            fill="#FEE2E2"
            name="Expenses"
          />
          <Area
            type="monotone"
            dataKey="income"
            stackId="2"
            stroke="#10B981"
            fill="#D1FAE5"
            name="Income"
          />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  );
};


// Daily Spending Chart
export const DailySpendingChart = ({ transactions, title = "Daily Spending" }) => {
  // Group by day and calculate daily totals
  const dailyData = transactions
    .filter(t => t.type === "debit") // ✅ Only expenses (not amount < 0)
    .reduce((acc, transaction) => {
      const transaction_date = new Date(transaction.transaction_date).toISOString().split('T')[0];
      if (!acc[transaction_date]) {
        acc[transaction_date] = { transaction_date, amount: 0 };
      }
      acc[transaction_date].amount += transaction.amount; // ✅ already positive
      return acc;
    }, {});

  const chartData = Object.values(dailyData)
    .sort((a, b) => new Date(a.transaction_date) - new Date(b.transaction_date))
    .map(item => ({
      ...item,
      transaction_date: new Date(item.transaction_date).toLocaleDateString('en-US', { 
        month: 'short', 
        day: '2-digit' 
      })
    }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white p-6 rounded-xl card-shadow"
    >
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="transaction_date" 
            tick={{ fontSize: 11 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => `₹${value}`} />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="amount"
            stroke="#8B5CF6"
            strokeWidth={2}
            dot={{ fill: '#8B5CF6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, fill: '#8B5CF6' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
};
