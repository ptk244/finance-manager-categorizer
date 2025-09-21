// components/InsightsPanel.jsx
import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  AlertCircle,
  Target,
  Lightbulb,
  PieChart,
  BarChart3,
  HeartPulse,
  CreditCard,
  Wallet,
  Info,
  FileText,
} from "lucide-react";
import { formatCurrency, calculatePercentage } from "../utils/helpers";

const InsightsPanel = ({ insights, transactions, categorySummary }) => {
  const [activeTab, setActiveTab] = useState("overview");

  // Calculate summary statistics
  const totalIncome = transactions
    .filter((t) => t.type === "credit")
    .reduce((sum, t) => sum + t.amount, 0);

  const totalExpenses = transactions
    .filter((t) => t.type === "debit")
    .reduce((sum, t) => sum + t.amount, 0);

  const netAmount = totalIncome - totalExpenses;

  const topCategories = Object.entries(categorySummary || {})
    // Sort by total_amount (descending)
    .sort(([, a], [, b]) => Math.abs(b.total_amount) - Math.abs(a.total_amount))
    .slice(0, 5);

  const topExpenses = (transactions || [])
    .filter((t) => t.type === "debit")
    .sort((a, b) => b.amount - a.amount) // largest first
    .slice(0, 5);

  const tabs = [
    { id: "overview", label: "Overview", icon: PieChart },
    { id: "insights", label: "AI Insights", icon: Lightbulb },
    { id: "recommendations", label: "Tips", icon: Target },
    { id: "statistical_insights", label: "Statistics", icon: BarChart3 },
    { id: "financial_health", label: "Health Check", icon: HeartPulse },
    { id: "metadata", label: "Report Details", icon: FileText },
  ];

  // Insight Card Component
  const InsightCard = ({
    icon: Icon,
    title,
    value,
    description,
    trend,
    color = "blue",
  }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-xl border-l-4 bg-gradient-to-r ${
        color === "green"
          ? "from-green-50 to-emerald-50 border-green-400"
          : color === "red"
          ? "from-red-50 to-rose-50 border-red-400"
          : color === "yellow"
          ? "from-yellow-50 to-amber-50 border-yellow-400"
          : "from-blue-50 to-indigo-50 border-blue-400"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <div
            className={`p-2 rounded-lg ${
              color === "green"
                ? "bg-green-100 text-green-600"
                : color === "red"
                ? "bg-red-100 text-red-600"
                : color === "yellow"
                ? "bg-yellow-100 text-yellow-600"
                : "bg-blue-100 text-blue-600"
            }`}
          >
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-medium text-gray-900">{title}</h4>
            {value && (
              <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
            )}
          </div>
        </div>

        {trend && (
          <div
            className={`flex items-center space-x-1 text-sm ${
              trend > 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {trend > 0 ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span>{Math.abs(trend)}%</span>
          </div>
        )}
      </div>

      {description && (
        <p className="text-sm text-gray-600 mt-2">{description}</p>
      )}
    </motion.div>
  );

  return (
    <div className="bg-white rounded-xl card-shadow overflow-hidden">
      {/* Header with Tabs */}
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Financial Insights
        </h2>
        <div className="overflow-x-auto">
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
        </div>
      </div>

      <div className="p-6">
        <AnimatePresence mode="wait">
          {/* Overview Tab */}
          {activeTab === "overview" && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
              {/* Financial Summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <InsightCard
                  icon={Wallet}
                  title="Total Income"
                  value={formatCurrency(totalIncome)}
                  description={`From ${
                    transactions.filter((t) => t.type === "credit").length
                  } income transactions`}
                  color="green"
                />

                <InsightCard
                  icon={CreditCard}
                  title="Total Expenses"
                  value={formatCurrency(totalExpenses)}
                  description={`From ${
                    transactions.filter((t) => t.type === "debit").length
                  } expense transactions`}
                  color="red"
                />

                <InsightCard
                  icon={BarChart3}
                  title="Net Amount"
                  value={formatCurrency(netAmount)}
                  description={
                    netAmount >= 0
                      ? "You saved money this month!"
                      : "You overspent this month"
                  }
                  color={netAmount >= 0 ? "green" : "red"}
                />
              </div>

              {/* Top Categories */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Top Spending Categories
                </h3>
                <div className="space-y-3">
                  {topCategories.map(([category, data], index) => (
                    <motion.div
                      key={category}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                          <span className="text-sm font-medium text-blue-600">
                            {index + 1}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">
                            {category}
                          </p>
                          <p className="text-sm text-gray-500">
                            {calculatePercentage(
                              data.total_amount,
                              totalExpenses
                            )}
                            % of total expenses
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-gray-900">
                          {formatCurrency(Math.abs(data.total_amount))}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Largest Transactions */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Largest Expenses
                </h3>
                <div className="space-y-2">
                  {topExpenses.map((transaction, index) => (
                    <motion.div
                      key={`${transaction.transaction_date}-${transaction.description}-${index}`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-gray-900 truncate">
                          {transaction.description}
                        </p>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className="text-xs px-2 py-1 bg-blue-100 text-blue-600 rounded-full">
                            {transaction.category || "Uncategorized"}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(transaction.transaction_date).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <div className="text-right ml-4">
                        <p className="font-semibold text-red-600">
                          {formatCurrency(transaction.amount)}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* AI Insights Tab */}
          {activeTab === "insights" && (
            <motion.div
              key="insights"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              {insights?.key_insights ? (
                insights.key_insights.map((insight, index) => {
                  // Try to extract a number from the string
                  const match = insight.match(/([\d,.]+)/);
                  let formattedInsight = insight;

                  if (match) {
                    const number = parseFloat(match[1].replace(/,/g, ""));
                    if (!isNaN(number) && insight.includes("$")) {
                      // Replace $amount with INR formatted string
                      formattedInsight = insight.replace(
                        `$${match[1]}`,
                        formatCurrency(number, "INR")
                      );
                    }
                  }

                  return (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="p-4 border border-blue-200 rounded-xl bg-blue-50/50"
                    >
                      <div className="flex items-start space-x-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <Lightbulb className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-gray-800 font-medium">
                            {formattedInsight}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  );
                })
              ) : (
                <div className="text-center py-8">
                  <Info className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    AI Insights Coming Soon
                  </h3>
                  <p className="text-gray-500">
                    Upload your bank statement and process it to see
                    personalized insights
                  </p>
                </div>
              )}

              {insights?.spending_behavior && (
                <div className="mt-6">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Spending Behavior Analysis
                  </h3>
                  <div className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl border border-purple-200 space-y-2">
                    <p className="text-sm text-gray-800">
                      <strong>Total Spending:</strong>{" "}
                      {formatCurrency(
                        insights.spending_behavior.total_spending
                      )}
                    </p>
                    <p className="text-sm text-gray-800">
                      <strong>Total Income:</strong>{" "}
                      {formatCurrency(insights.spending_behavior.total_income)}
                    </p>
                    <p className="text-sm text-gray-800">
                      <strong>Net Savings:</strong>{" "}
                      {formatCurrency(insights.spending_behavior.net_savings)}
                    </p>
                    <p className="text-sm text-gray-800">
                      <strong>Transactions:</strong>{" "}
                      {insights.spending_behavior.transaction_count}
                    </p>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Recommendations Tab */}
          {activeTab === "recommendations" && (
            <motion.div
              key="recommendations"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              {insights?.recommendations ? (
                insights.recommendations.map((recommendation, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="p-4 border border-green-200 rounded-xl bg-green-50/50"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-green-100 rounded-lg">
                        <Target className="w-5 h-5 text-green-600" />
                      </div>
                      <div>
                        <p className="text-gray-800">{recommendation}</p>
                      </div>
                    </div>
                  </motion.div>
                ))
              ) : (
                <div className="space-y-4">
                  {/* Default recommendations based on spending patterns */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 border border-green-200 rounded-xl bg-green-50/50"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-green-100 rounded-lg">
                        <Target className="w-5 h-5 text-green-600" />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 mb-1">
                          Track Your Spending
                        </h4>
                        <p className="text-gray-700 text-sm">
                          Review your transactions regularly to identify
                          spending patterns and areas for improvement.
                        </p>
                      </div>
                    </div>
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="p-4 border border-yellow-200 rounded-xl bg-yellow-50/50"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-yellow-100 rounded-lg">
                        <AlertCircle className="w-5 h-5 text-yellow-600" />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 mb-1">
                          Set Budget Limits
                        </h4>
                        <p className="text-gray-700 text-sm">
                          Consider setting monthly budget limits for your top
                          spending categories to better control expenses.
                        </p>
                      </div>
                    </div>
                  </motion.div>

                  {netAmount < 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className="p-4 border border-red-200 rounded-xl bg-red-50/50"
                    >
                      <div className="flex items-start space-x-3">
                        <div className="p-2 bg-red-100 rounded-lg">
                          <TrendingDown className="w-5 h-5 text-red-600" />
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900 mb-1">
                            Reduce Overspending
                          </h4>
                          <p className="text-gray-700 text-sm">
                            You spent {formatCurrency(Math.abs(netAmount))} more
                            than you earned this month. Consider reviewing your
                            largest expense categories.
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              )}
            </motion.div>
          )}

          {/* Statistical Insights Tab */}
          {activeTab === "statistical_insights" && (
            <motion.div
              key="statistical_insights"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              {insights?.statistical_insights ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="p-4 border border-green-200 rounded-xl bg-green-50/50"
                >
                  <div className="p-4 bg-gradient-to-r from-yellow-50 to-amber-50 rounded-xl border border-yellow-200 space-y-2">
                    <p className="text-sm text-gray-800">
                      <strong>Income-Spending Ratio:</strong>{" "}
                      {insights.statistical_insights.income_spending_ratio.toFixed(
                        2
                      )}{" "}
                      ({insights.statistical_insights.ratio_comment})
                    </p>
                    <p className="text-sm text-gray-800">
                      <strong>Top Category Concentration:</strong>{" "}
                      {insights.statistical_insights.top_category_concentration.toFixed(
                        2
                      )}
                      % ({insights.statistical_insights.concentration_comment})
                    </p>
                    <p className="text-sm text-gray-800">
                      <strong>Transaction Pattern:</strong>{" "}
                      {insights.statistical_insights.transaction_pattern}
                    </p>
                    <p className="text-sm text-gray-800">
                      <strong>Savings Assessment:</strong>{" "}
                      {insights.statistical_insights.savings_assessment}
                    </p>
                  </div>
                </motion.div>
              ) : (
                <div className="space-y-4">
                  {/* Default recommendations if no statistical insights */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 border border-green-200 rounded-xl bg-green-50/50"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-green-100 rounded-lg">
                        <Target className="w-5 h-5 text-green-600" />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 mb-1">
                          Track Your Spending
                        </h4>
                        <p className="text-gray-700 text-sm">
                          Review your transactions regularly to identify
                          spending patterns and areas for improvement.
                        </p>
                      </div>
                    </div>
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="p-4 border border-yellow-200 rounded-xl bg-yellow-50/50"
                  >
                    <div className="flex items-start space-x-3">
                      <div className="p-2 bg-yellow-100 rounded-lg">
                        <AlertCircle className="w-5 h-5 text-yellow-600" />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 mb-1">
                          Set Budget Limits
                        </h4>
                        <p className="text-gray-700 text-sm">
                          Consider setting monthly budget limits for your top
                          spending categories to better control expenses.
                        </p>
                      </div>
                    </div>
                  </motion.div>

                  {netAmount < 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className="p-4 border border-red-200 rounded-xl bg-red-50/50"
                    >
                      <div className="flex items-start space-x-3">
                        <div className="p-2 bg-red-100 rounded-lg">
                          <TrendingDown className="w-5 h-5 text-red-600" />
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900 mb-1">
                            Reduce Overspending
                          </h4>
                          <p className="text-gray-700 text-sm">
                            You spent {formatCurrency(Math.abs(netAmount))} more
                            than you earned this month. Consider reviewing your
                            largest expense categories.
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              )}
            </motion.div>
          )}
          {/* Financial Health Tab */}
          {activeTab === "financial_health" && (
            <motion.div
              key="financial_health"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              {insights?.financial_health ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="p-4 border border-blue-200 rounded-xl bg-blue-50/50"
                >
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">
                    Financial Health Overview
                  </h4>
                  <p className="text-sm text-gray-800">
                    <strong>Status:</strong> {insights.financial_health.status}
                  </p>
                  <p className="text-sm text-gray-800">
                    <strong>Savings Rate:</strong>{" "}
                    {insights.financial_health.savings_rate}
                  </p>
                  <p className="text-sm text-gray-800">
                    <strong>Note:</strong> {insights.financial_health.note}
                  </p>
                </motion.div>
              ) : (
                <p className="text-gray-600">
                  No financial health data available.
                </p>
              )}
            </motion.div>
          )}
          {/* Metadata Tab */}
          {activeTab === "metadata" && (
            <motion.div
              key="metadata"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              {insights?.metadata ? (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="p-4 border border-purple-200 rounded-xl bg-purple-50/50"
                >
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">
                    Report Details
                  </h4>
                  <p className="text-sm text-gray-800">
                    <strong>Total Transactions:</strong>{" "}
                    {insights.metadata.total_transactions}
                  </p>
                  <p className="text-sm text-gray-800">
                    <strong>Analysis Period:</strong>{" "}
                    {insights.metadata.analysis_period}
                  </p>
                  <p className="text-sm text-gray-800">
                    <strong>Generated At:</strong>{" "}
                    {new Date(insights.metadata.generated_at).toLocaleString(
                      "en-IN",
                      {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }
                    )}
                  </p>
                </motion.div>
              ) : (
                <p className="text-gray-600">No metadata available.</p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default InsightsPanel;
