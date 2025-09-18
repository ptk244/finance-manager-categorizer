from agno.agent import Agent
from models.transaction import ProcessedBankStatement, CategorySummary, InsightsSummary, Transaction
from services.gemini_service import gemini_service
from typing import List, Dict, Any
from loguru import logger
import statistics

class InsightsAgent:
    """Agent responsible for generating financial insights using Gemini Flash model"""
    
    def __init__(self):
        self.agent = Agent(
            name="InsightsAgent",
            description="Specialized in analyzing financial data and generating actionable insights",
            instructions=[
                "You are a personal finance advisor and data analyst.",
                "Generate meaningful, actionable insights from transaction data.",
                "Focus on spending patterns, savings opportunities, and financial health.",
                "Provide specific, quantified insights with Indian currency context.",
                "Identify unusual spending patterns and trends.",
                "Suggest practical recommendations for better financial management.",
                "Make insights relatable and easy to understand for average users.",
                "Highlight both positive and negative financial behaviors.",
                "Consider seasonal patterns and lifestyle factors."
            ],
            model=f"gemini/{gemini_service.insights_model.model_name}",
            # show_tool_calls=True,
            debug_mode=True
        )
    
    async def generate_comprehensive_insights(self, categorized_statement: ProcessedBankStatement) -> Dict[str, Any]:
        """Generate comprehensive financial insights from categorized transactions"""
        try:
            logger.info("Generating comprehensive financial insights")
            
            # Extract basic statistics
            basic_stats = self._calculate_basic_statistics(categorized_statement)
            
            # Generate category breakdown
            category_breakdown = self._generate_category_breakdown(categorized_statement.transactions)
            
            # Find top transactions and patterns
            transaction_analysis = self._analyze_transaction_patterns(categorized_statement.transactions)
            
            # Prepare data for AI insights
            insights_data = {
                'total_transactions': categorized_statement.total_transactions,
                'total_debits': categorized_statement.total_debits,
                'total_credits': categorized_statement.total_credits,
                'net_savings': categorized_statement.total_credits - categorized_statement.total_debits,
                'date_range': {
                    'start': categorized_statement.date_range['start'].strftime('%Y-%m-%d'),
                    'end': categorized_statement.date_range['end'].strftime('%Y-%m-%d')
                },
                'category_breakdown': {k: v['total_amount'] for k, v in category_breakdown.items()},
                'top_transactions': transaction_analysis['top_expenses'][:5],
                'spending_patterns': transaction_analysis['patterns'],
                'basic_stats': basic_stats
            }
            
            # Generate AI-powered insights
            ai_insights = await gemini_service.generate_insights(insights_data)
            
            # Create category summaries
            category_summaries = []
            for category, data in category_breakdown.items():
                if data['total_amount'] > 0:  # Only include categories with spending
                    category_summaries.append(CategorySummary(
                        category=category,
                        total_amount=data['total_amount'],
                        transaction_count=data['transaction_count'],
                        percentage=data['percentage'],
                        avg_transaction=data['avg_transaction']
                    ))
            
            # Sort by amount
            category_summaries.sort(key=lambda x: x.total_amount, reverse=True)
            
            # Find largest expense
            largest_expense = max(
                [t for t in categorized_statement.transactions if t.transaction_type.value == 'debit'],
                key=lambda x: x.amount
            ) if any(t.transaction_type.value == 'debit' for t in categorized_statement.transactions) else None
            
            # Create comprehensive insights summary
            insights_summary = InsightsSummary(
                total_expenses=categorized_statement.total_debits,
                total_income=categorized_statement.total_credits,
                net_savings=categorized_statement.total_credits - categorized_statement.total_debits,
                top_category=category_summaries[0] if category_summaries else None,
                largest_expense=largest_expense,
                category_breakdown=category_summaries,
                insights_text=self._format_insights_text(ai_insights, basic_stats),
                recommendations=ai_insights.get('recommendations', [])
            )
            
            logger.info("Successfully generated comprehensive insights")
            
            return {
                'success': True,
                'insights_summary': insights_summary,
                'ai_insights': ai_insights,
                'analysis_stats': {
                    'categories_analyzed': len(category_summaries),
                    'patterns_identified': len(transaction_analysis['patterns']),
                    'insights_generated': len(ai_insights.get('key_insights', [])),
                    'recommendations_count': len(ai_insights.get('recommendations', []))
                }
            }
            
        except Exception as e:
            logger.error(f"Insights generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'insights_summary': None
            }
    
    async def generate_category_insights(self, category: str, transactions: List[Transaction]) -> Dict[str, Any]:
        """Generate specific insights for a particular spending category"""
        try:
            category_transactions = [t for t in transactions if t.category and t.category.value == category]
            
            if not category_transactions:
                return {'error': f'No transactions found for category: {category}'}
            
            total_amount = sum(t.amount for t in category_transactions)
            avg_amount = total_amount / len(category_transactions)
            
            # Analyze spending patterns within category
            monthly_spending = {}
            for transaction in category_transactions:
                month_key = transaction.date.strftime('%Y-%m')
                monthly_spending[month_key] = monthly_spending.get(month_key, 0) + transaction.amount
            
            category_insights = {
                'category': category,
                'total_spent': total_amount,
                'transaction_count': len(category_transactions),
                'average_transaction': avg_amount,
                'highest_transaction': max(category_transactions, key=lambda x: x.amount),
                'monthly_breakdown': monthly_spending,
                'frequency_analysis': self._analyze_spending_frequency(category_transactions)
            }
            
            return {
                'success': True,
                'category_insights': category_insights
            }
            
        except Exception as e:
            logger.error(f"Category insights generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_basic_statistics(self, statement: ProcessedBankStatement) -> Dict[str, Any]:
        """Calculate basic financial statistics"""
        try:
            transactions = statement.transactions
            debit_amounts = [t.amount for t in transactions if t.transaction_type.value == 'debit']
            credit_amounts = [t.amount for t in transactions if t.transaction_type.value == 'credit']
            
            stats = {
                'total_transactions': len(transactions),
                'total_expenses': sum(debit_amounts),
                'total_income': sum(credit_amounts),
                'net_savings': sum(credit_amounts) - sum(debit_amounts),
                'avg_expense': statistics.mean(debit_amounts) if debit_amounts else 0,
                'median_expense': statistics.median(debit_amounts) if debit_amounts else 0,
                'max_expense': max(debit_amounts) if debit_amounts else 0,
                'min_expense': min(debit_amounts) if debit_amounts else 0,
                'expense_std_dev': statistics.stdev(debit_amounts) if len(debit_amounts) > 1 else 0,
                'days_covered': (statement.date_range['end'] - statement.date_range['start']).days + 1,
                'avg_daily_expense': sum(debit_amounts) / max(1, (statement.date_range['end'] - statement.date_range['start']).days + 1),
                'current_balance': statement.current_balance
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Statistics calculation failed: {str(e)}")
            return {}
    
    def _generate_category_breakdown(self, transactions: List[Transaction]) -> Dict[str, Dict[str, Any]]:
        """Generate detailed breakdown by spending categories"""
        category_data = {}
        total_expenses = sum(t.amount for t in transactions if t.transaction_type.value == 'debit')
        
        for transaction in transactions:
            if transaction.transaction_type.value == 'debit' and transaction.category:
                category = transaction.category.value
                
                if category not in category_data:
                    category_data[category] = {
                        'total_amount': 0,
                        'transaction_count': 0,
                        'transactions': []
                    }
                
                category_data[category]['total_amount'] += transaction.amount
                category_data[category]['transaction_count'] += 1
                category_data[category]['transactions'].append({
                    'date': transaction.date.strftime('%Y-%m-%d'),
                    'description': transaction.description,
                    'amount': transaction.amount
                })
        
        # Calculate percentages and averages
        for category, data in category_data.items():
            data['percentage'] = (data['total_amount'] / total_expenses) * 100 if total_expenses > 0 else 0
            data['avg_transaction'] = data['total_amount'] / data['transaction_count']
        
        return category_data
    
    def _analyze_transaction_patterns(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Analyze transaction patterns and identify trends"""
        try:
            debit_transactions = [t for t in transactions if t.transaction_type.value == 'debit']
            
            # Sort by amount to find top expenses
            top_expenses = sorted(debit_transactions, key=lambda x: x.amount, reverse=True)[:10]
            
            # Identify patterns
            patterns = []
            
            # Frequent merchants
            merchant_frequency = {}
            for transaction in debit_transactions:
                # Simple merchant extraction (first few words)
                merchant = ' '.join(transaction.description.split()[:3]).upper()
                merchant_frequency[merchant] = merchant_frequency.get(merchant, 0) + 1
            
            frequent_merchants = sorted(merchant_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
            if frequent_merchants and frequent_merchants[0][1] > 2:
                patterns.append(f"Frequent spending at {frequent_merchants[0][0]} ({frequent_merchants[0][1]} transactions)")
            
            # Weekend vs weekday spending
            weekend_spending = sum(t.amount for t in debit_transactions if t.date.weekday() >= 5)
            weekday_spending = sum(t.amount for t in debit_transactions if t.date.weekday() < 5)
            
            if weekend_spending > 0 and weekday_spending > 0:
                weekend_ratio = weekend_spending / (weekend_spending + weekday_spending) * 100
                if weekend_ratio > 40:
                    patterns.append(f"High weekend spending: {weekend_ratio:.1f}% of total expenses")
                elif weekend_ratio < 15:
                    patterns.append(f"Low weekend spending: {weekend_ratio:.1f}% of total expenses")
            
            # Large transaction analysis
            large_transactions = [t for t in debit_transactions if t.amount > statistics.mean([t.amount for t in debit_transactions]) * 2]
            if large_transactions:
                patterns.append(f"{len(large_transactions)} unusually large transactions detected")
            
            return {
                'top_expenses': [
                    {
                        'description': t.description,
                        'amount': t.amount,
                        'date': t.date.strftime('%Y-%m-%d'),
                        'category': t.category.value if t.category else 'Other'
                    }
                    for t in top_expenses
                ],
                'patterns': patterns,
                'frequent_merchants': frequent_merchants
            }
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {str(e)}")
            return {
                'top_expenses': [],
                'patterns': [],
                'frequent_merchants': []
            }
    
    def _analyze_spending_frequency(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Analyze frequency patterns in spending"""
        try:
            # Daily frequency
            daily_spending = {}
            for transaction in transactions:
                day = transaction.date.strftime('%Y-%m-%d')
                daily_spending[day] = daily_spending.get(day, 0) + transaction.amount
            
            # Calculate frequency metrics
            spending_days = len([day for day, amount in daily_spending.items() if amount > 0])
            total_days = (max(transactions, key=lambda x: x.date).date - 
                         min(transactions, key=lambda x: x.date).date).days + 1
            
            return {
                'spending_days': spending_days,
                'total_days': total_days,
                'spending_frequency': (spending_days / total_days) * 100,
                'avg_spending_per_active_day': sum(daily_spending.values()) / max(1, spending_days)
            }
            
        except Exception as e:
            logger.error(f"Frequency analysis failed: {str(e)}")
            return {}
    
    def _format_insights_text(self, ai_insights: Dict[str, Any], basic_stats: Dict[str, Any]) -> str:
        """Format AI insights into readable text"""
        try:
            insights_parts = []
            
            # Add summary
            if ai_insights.get('summary'):
                insights_parts.append(ai_insights['summary'])
            
            # Add key insights
            if ai_insights.get('key_insights'):
                insights_parts.append("\nKey Insights:")
                for insight in ai_insights['key_insights']:
                    insights_parts.append(f"• {insight}")
            
            # Add spending patterns
            if ai_insights.get('spending_patterns'):
                insights_parts.append(f"\nSpending Patterns: {ai_insights['spending_patterns']}")
            
            # Add savings potential
            if ai_insights.get('savings_potential'):
                insights_parts.append(f"\nSavings Opportunities: {ai_insights['savings_potential']}")
            
            return '\n'.join(insights_parts)
            
        except Exception as e:
            logger.error(f"Insights formatting failed: {str(e)}")
            return "Insights analysis completed successfully."

# Create agent instance
insights_agent = InsightsAgent()