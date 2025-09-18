from agno import Tool
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any
import json
from datetime import datetime
from loguru import logger

class VisualizationTools:
    """Custom tools for creating financial data visualizations"""
    
    @Tool
    def create_category_pie_chart(self, category_data: Dict[str, float]) -> Dict[str, Any]:
        """Create pie chart for category-wise spending distribution"""
        try:
            # Prepare data
            categories = list(category_data.keys())
            amounts = list(category_data.values())
            
            # Calculate percentages
            total = sum(amounts)
            percentages = [round((amount/total)*100, 1) for amount in amounts]
            
            # Create pie chart
            fig = px.pie(
                values=amounts,
                names=categories,
                title="Spending Distribution by Category",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            # Customize layout
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Amount: ₹%{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
            )
            
            fig.update_layout(
                font=dict(size=14),
                showlegend=True,
                height=500
            )
            
            return {
                'chart_type': 'pie',
                'chart_data': fig.to_json(),
                'summary': {
                    'total_categories': len(categories),
                    'total_amount': total,
                    'top_category': categories[amounts.index(max(amounts))],
                    'top_amount': max(amounts)
                }
            }
            
        except Exception as e:
            logger.error(f"Pie chart creation failed: {str(e)}")
            return {'error': str(e)}
    
    @Tool
    def create_spending_timeline(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create timeline visualization of spending patterns"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame(transactions)
            df['date'] = pd.to_datetime(df['date'])
            df['amount_signed'] = df.apply(
                lambda x: -x['amount'] if x['transaction_type'] == 'debit' else x['amount'], 
                axis=1
            )
            
            # Group by date
            daily_summary = df.groupby(df['date'].dt.date).agg({
                'amount_signed': 'sum',
                'amount': lambda x: sum(x[df.loc[x.index, 'transaction_type'] == 'debit']),  # expenses
            }).reset_index()
            daily_summary.columns = ['date', 'net_flow', 'expenses']
            
            # Create timeline chart
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Daily Cash Flow', 'Daily Expenses'),
                vertical_spacing=0.1
            )
            
            # Add net flow
            fig.add_trace(
                go.Scatter(
                    x=daily_summary['date'],
                    y=daily_summary['net_flow'],
                    mode='lines+markers',
                    name='Net Cash Flow',
                    line=dict(color='blue'),
                    fill='tozeroy'
                ),
                row=1, col=1
            )
            
            # Add expenses
            fig.add_trace(
                go.Bar(
                    x=daily_summary['date'],
                    y=daily_summary['expenses'],
                    name='Daily Expenses',
                    marker_color='red',
                    opacity=0.7
                ),
                row=2, col=1
            )
            
            fig.update_layout(
                title="Spending Timeline Analysis",
                height=600,
                showlegend=True
            )
            
            return {
                'chart_type': 'timeline',
                'chart_data': fig.to_json(),
                'summary': {
                    'total_days': len(daily_summary),
                    'avg_daily_expense': round(daily_summary['expenses'].mean(), 2),
                    'max_daily_expense': round(daily_summary['expenses'].max(), 2),
                    'min_daily_expense': round(daily_summary['expenses'].min(), 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Timeline chart creation failed: {str(e)}")
            return {'error': str(e)}
    
    @Tool
    def create_top_transactions_chart(self, transactions: List[Dict[str, Any]], top_n: int = 10) -> Dict[str, Any]:
        """Create bar chart for top transactions"""
        try:
            # Filter debit transactions and sort by amount
            debit_transactions = [t for t in transactions if t['transaction_type'] == 'debit']
            top_transactions = sorted(debit_transactions, key=lambda x: x['amount'], reverse=True)[:top_n]
            
            if not top_transactions:
                return {'error': 'No debit transactions found'}
            
            # Prepare data
            descriptions = [t['description'][:30] + '...' if len(t['description']) > 30 else t['description'] 
                          for t in top_transactions]
            amounts = [t['amount'] for t in top_transactions]
            categories = [t.get('category', 'Other') for t in top_transactions]
            
            # Create bar chart
            fig = px.bar(
                x=amounts,
                y=descriptions,
                orientation='h',
                title=f"Top {len(top_transactions)} Expenses",
                labels={'x': 'Amount (₹)', 'y': 'Transaction'},
                color=categories,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            
            fig.update_layout(
                height=max(400, len(top_transactions) * 40),
                yaxis={'categoryorder': 'total ascending'},
                xaxis_title="Amount (₹)",
                yaxis_title="Transactions"
            )
            
            return {
                'chart_type': 'bar_horizontal',
                'chart_data': fig.to_json(),
                'summary': {
                    'total_transactions': len(top_transactions),
                    'top_transaction_amount': max(amounts),
                    'total_top_expenses': sum(amounts),
                    'avg_top_expense': round(sum(amounts)/len(amounts), 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Top transactions chart creation failed: {str(e)}")
            return {'error': str(e)}
    
    @Tool
    def create_category_comparison_chart(self, category_data: Dict[str, float]) -> Dict[str, Any]:
        """Create horizontal bar chart for category comparison"""
        try:
            # Sort categories by amount
            sorted_categories = sorted(category_data.items(), key=lambda x: x[1], reverse=True)
            categories = [item[0] for item in sorted_categories]
            amounts = [item[1] for item in sorted_categories]
            
            # Create horizontal bar chart
            fig = px.bar(
                x=amounts,
                y=categories,
                orientation='h',
                title="Category-wise Spending Comparison",
                labels={'x': 'Amount (₹)', 'y': 'Categories'},
                color=amounts,
                color_continuous_scale='Viridis'
            )
            
            fig.update_layout(
                height=max(400, len(categories) * 30),
                yaxis={'categoryorder': 'total ascending'},
                xaxis_title="Amount (₹)",
                yaxis_title="Categories",
                coloraxis_showscale=False
            )
            
            # Add value labels on bars
            fig.update_traces(
                texttemplate='₹%{x:,.0f}',
                textposition='inside'
            )
            
            return {
                'chart_type': 'bar_comparison',
                'chart_data': fig.to_json(),
                'summary': {
                    'total_categories': len(categories),
                    'highest_spending_category': categories[0],
                    'lowest_spending_category': categories[-1],
                    'spending_range': amounts[0] - amounts[-1]
                }
            }
            
        except Exception as e:
            logger.error(f"Category comparison chart creation failed: {str(e)}")
            return {'error': str(e)}
    
    @Tool
    def create_income_vs_expense_chart(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create income vs expense comparison chart"""
        try:
            df = pd.DataFrame(transactions)
            df['date'] = pd.to_datetime(df['date'])
            
            # Calculate monthly income and expenses
            df['month'] = df['date'].dt.to_period('M')
            monthly_data = df.groupby(['month', 'transaction_type'])['amount'].sum().unstack(fill_value=0)
            
            if 'credit' not in monthly_data.columns:
                monthly_data['credit'] = 0
            if 'debit' not in monthly_data.columns:
                monthly_data['debit'] = 0
            
            # Create grouped bar chart
            fig = go.Figure(data=[
                go.Bar(name='Income', x=monthly_data.index.astype(str), y=monthly_data['credit'], 
                       marker_color='green', opacity=0.7),
                go.Bar(name='Expenses', x=monthly_data.index.astype(str), y=monthly_data['debit'], 
                       marker_color='red', opacity=0.7)
            ])
            
            fig.update_layout(
                title='Monthly Income vs Expenses',
                xaxis_title='Month',
                yaxis_title='Amount (₹)',
                barmode='group',
                height=400
            )
            
            # Calculate savings
            monthly_data['savings'] = monthly_data['credit'] - monthly_data['debit']
            
            return {
                'chart_type': 'income_expense',
                'chart_data': fig.to_json(),
                'summary': {
                    'months_covered': len(monthly_data),
                    'total_income': monthly_data['credit'].sum(),
                    'total_expenses': monthly_data['debit'].sum(),
                    'net_savings': monthly_data['savings'].sum(),
                    'avg_monthly_savings': round(monthly_data['savings'].mean(), 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Income vs expense chart creation failed: {str(e)}")
            return {'error': str(e)}
    
    @Tool
    def create_comprehensive_dashboard(self, transactions: List[Dict[str, Any]], category_data: Dict[str, float]) -> Dict[str, Any]:
        """Create a comprehensive financial dashboard"""
        try:
            charts = {}
            
            # Create all charts
            charts['pie_chart'] = self.create_category_pie_chart(category_data)
            charts['timeline'] = self.create_spending_timeline(transactions)
            charts['top_transactions'] = self.create_top_transactions_chart(transactions)
            charts['category_comparison'] = self.create_category_comparison_chart(category_data)
            charts['income_expense'] = self.create_income_vs_expense_chart(transactions)
            
            # Compile summary statistics
            total_transactions = len(transactions)
            total_expenses = sum([t['amount'] for t in transactions if t['transaction_type'] == 'debit'])
            total_income = sum([t['amount'] for t in transactions if t['transaction_type'] == 'credit'])
            
            dashboard_summary = {
                'total_transactions': total_transactions,
                'total_expenses': total_expenses,
                'total_income': total_income,
                'net_savings': total_income - total_expenses,
                'categories_count': len(category_data),
                'chart_count': len([c for c in charts.values() if 'error' not in c])
            }
            
            return {
                'dashboard_type': 'comprehensive',
                'charts': charts,
                'summary': dashboard_summary
            }
            
        except Exception as e:
            logger.error(f"Dashboard creation failed: {str(e)}")
            return {'error': str(e)}

# Create tool instance
visualization_tools = VisualizationTools()