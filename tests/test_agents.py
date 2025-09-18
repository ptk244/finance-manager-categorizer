"""
Test script for all AI agents functionality
"""
import asyncio
import sys
import os
from pathlib import Path
import tempfile
import csv
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.file_processor_agent import file_processor_agent
from agents.categorizer_agent import categorizer_agent
from agents.insights_agent import insights_agent
from services.agent_team_service import agent_team_service
from models.transaction import Transaction, ProcessedBankStatement, TransactionType, SpendingCategory
from config.settings import settings
from loguru import logger

class AgentTestSuite:
    """Comprehensive test suite for all agents"""
    
    def __init__(self):
        self.test_results = {}
        self.sample_csv_file = None
        
    def create_sample_csv(self):
        """Create a sample CSV file for testing"""
        # Create sample data
        sample_data = [
            ["Date", "Description", "Amount", "Type", "Balance"],
            ["2024-01-01", "SALARY CREDIT TCS LTD", "75000", "credit", "125000"],
            ["2024-01-02", "ATM WITHDRAWAL HDFC BANK", "-2000", "debit", "123000"],
            ["2024-01-03", "SWIGGY FOOD DELIVERY", "-450", "debit", "122550"],
            ["2024-01-04", "UPI PAYTM GROCERY STORE", "-1200", "debit", "121350"],
            ["2024-01-05", "NETFLIX SUBSCRIPTION", "-649", "debit", "120701"],
            ["2024-01-06", "UBER RIDE BANGALORE", "-320", "debit", "120381"],
            ["2024-01-07", "ELECTRICITY BILL BESCOM", "-2500", "debit", "117881"],
            ["2024-01-08", "FLIPKART SHOPPING", "-5000", "debit", "112881"],
            ["2024-01-09", "MEDICAL STORE APOLLO", "-800", "debit", "112081"],
            ["2024-01-10", "PETROL PUMP BHARAT", "-3000", "debit", "109081"]
        ]
        
        # Create temporary CSV file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        writer = csv.writer(temp_file)
        writer.writerows(sample_data)
        temp_file.close()
        
        self.sample_csv_file = temp_file.name
        return self.sample_csv_file
    
    async def test_file_processor_agent(self):
        """Test FileProcessorAgent functionality"""
        print("🗂️  Testing FileProcessorAgent...")
        
        try:
            # Create sample file
            sample_file = self.create_sample_csv()
            
            # Test file processing
            result = await file_processor_agent.process_uploaded_file(sample_file, "test_statement.csv")
            
            if result.get('success', False):
                processed_statement = result['processed_statement']
                extraction_stats = result['extraction_stats']
                
                print(f"   ✅ File processed successfully")
                print(f"   📊 Transactions extracted: {processed_statement.total_transactions}")
                print(f"   💰 Total debits: ₹{processed_statement.total_debits:,.2f}")
                print(f"   💵 Total credits: ₹{processed_statement.total_credits:,.2f}")
                print(f"   📈 Success rate: {extraction_stats['success_rate']:.1f}%")
                
                # Test validation
                transaction_dicts = [
                    {
                        'date': t.date.isoformat(),
                        'description': t.description,
                        'amount': t.amount,
                        'transaction_type': t.transaction_type.value,
                        'balance': t.balance
                    }
                    for t in processed_statement.transactions
                ]
                
                validation_result = await file_processor_agent.validate_extracted_data(transaction_dicts)
                print(f"   🔍 Data quality score: {validation_result.get('data_quality_score', 0):.1f}%")
                
                self.test_results['file_processor'] = {
                    'success': True,
                    'processed_statement': processed_statement,
                    'extraction_stats': extraction_stats
                }
                
                return True
                
            else:
                print(f"   ❌ File processing failed: {result.get('error', 'Unknown error')}")
                self.test_results['file_processor'] = {'success': False, 'error': result.get('error')}
                return False
                
        except Exception as e:
            print(f"   ❌ FileProcessorAgent test failed: {str(e)}")
            self.test_results['file_processor'] = {'success': False, 'error': str(e)}
            return False
    
    async def test_categorizer_agent(self):
        """Test CategorizerAgent functionality"""
        print("\n🏷️  Testing CategorizerAgent...")
        
        if not self.test_results.get('file_processor', {}).get('success', False):
            print("   ⏩ Skipping categorizer test - file processor failed")
            return False
        
        try:
            processed_statement = self.test_results['file_processor']['processed_statement']
            
            # Test categorization
            result = await categorizer_agent.categorize_transactions(processed_statement)
            
            if result.get('success', False):
                categorized_statement = result['categorized_statement']
                categorization_stats = result['categorization_stats']
                
                print(f"   ✅ Transactions categorized successfully")
                print(f"   📊 Categorized: {categorization_stats['categorized_transactions']}/{categorization_stats['total_transactions']}")
                print(f"   🎯 Average confidence: {categorization_stats['average_confidence']:.2f}")
                print(f"   📈 Categorization rate: {categorization_stats['categorization_rate']:.1f}%")
                
                # Test category summary
                category_summary = categorizer_agent.get_category_summary(categorized_statement.transactions)
                top_categories = list(category_summary['category_breakdown'].keys())[:3]
                print(f"   🏆 Top categories: {', '.join(top_categories)}")
                
                # Test single transaction recategorization
                first_transaction = categorized_statement.transactions[0]
                recat_result = await categorizer_agent.recategorize_transaction(first_transaction)
                
                if recat_result.get('success', False):
                    print(f"   🔄 Recategorization test passed")
                else:
                    print(f"   ⚠️  Recategorization test warning: {recat_result.get('error', 'Unknown')}")
                
                self.test_results['categorizer'] = {
                    'success': True,
                    'categorized_statement': categorized_statement,
                    'category_summary': category_summary,
                    'stats': categorization_stats
                }
                
                return True
                
            else:
                print(f"   ❌ Categorization failed: {result.get('error', 'Unknown error')}")
                self.test_results['categorizer'] = {'success': False, 'error': result.get('error')}
                return False
                
        except Exception as e:
            print(f"   ❌ CategorizerAgent test failed: {str(e)}")
            self.test_results['categorizer'] = {'success': False, 'error': str(e)}
            return False
    
    async def test_insights_agent(self):
        """Test InsightsAgent functionality"""
        print("\n💡 Testing InsightsAgent...")
        
        if not self.test_results.get('categorizer', {}).get('success', False):
            print("   ⏩ Skipping insights test - categorizer failed")
            return False
        
        try:
            categorized_statement = self.test_results['categorizer']['categorized_statement']
            
            # Test comprehensive insights generation
            result = await insights_agent.generate_comprehensive_insights(categorized_statement)
            
            if result.get('success', False):
                insights_summary = result['insights_summary']
                ai_insights = result['ai_insights']
                analysis_stats = result['analysis_stats']
                
                print(f"   ✅ Insights generated successfully")
                print(f"   💰 Net savings: ₹{insights_summary.net_savings:,.2f}")
                print(f"   📊 Categories analyzed: {analysis_stats['categories_analyzed']}")
                print(f"   💡 Insights count: {analysis_stats['insights_generated']}")
                print(f"   🎯 Recommendations: {analysis_stats['recommendations_count']}")
                
                # Show sample insights
                if ai_insights.get('key_insights'):
                    print(f"   📋 Sample insight: {ai_insights['key_insights'][0][:60]}...")
                
                if insights_summary.top_category:
                    print(f"   🏆 Top spending: {insights_summary.top_category.category} (₹{insights_summary.top_category.total_amount:,.2f})")
                
                # Test category-specific insights
                if insights_summary.top_category:
                    category_name = insights_summary.top_category.category
                    category_result = await insights_agent.generate_category_insights(
                        category_name, 
                        categorized_statement.transactions
                    )
                    
                    if category_result.get('success', False):
                        print(f"   🔍 Category insights generated for {category_name}")
                    else:
                        print(f"   ⚠️  Category insights warning: {category_result.get('error', 'Unknown')}")
                
                self.test_results['insights'] = {
                    'success': True,
                    'insights_summary': insights_summary,
                    'ai_insights': ai_insights,
                    'stats': analysis_stats
                }
                
                return True
                
            else:
                print(f"   ❌ Insights generation failed: {result.get('error', 'Unknown error')}")
                self.test_results['insights'] = {'success': False, 'error': result.get('error')}
                return False
                
        except Exception as e:
            print(f"   ❌ InsightsAgent test failed: {str(e)}")
            self.test_results['insights'] = {'success': False, 'error': str(e)}
            return False
    
    async def test_agent_team_service(self):
        """Test AgentTeamService workflow orchestration"""
        print("\n👥 Testing AgentTeamService...")
        
        try:
            # Create fresh sample file
            sample_file = self.create_sample_csv()
            
            # Test complete workflow
            result = await agent_team_service.process_complete_workflow(sample_file, "team_test.csv")
            
            if result.get('success', False):
                print(f"   ✅ Complete workflow executed successfully")
                print(f"   📊 Processing stats available: {len(result['processing_stats'])} components")
                
                if result.get('visualizations', {}).get('success', False):
                    dashboard = result['visualizations']['dashboard']
                    print(f"   📈 Visualizations created: {dashboard.get('summary', {}).get('chart_count', 0)} charts")
                else:
                    print(f"   ⚠️  Visualizations warning: {result.get('visualizations', {}).get('error', 'Unknown')}")
                
                # Test team status
                team_status = await agent_team_service.get_team_status()
                print(f"   👥 Team status: {team_status.get('status', 'Unknown')}")
                print(f"   🤖 Active agents: {team_status.get('agents_count', 0)}")
                
                self.test_results['agent_team'] = {
                    'success': True,
                    'workflow_result': result,
                    'team_status': team_status
                }
                
                return True
                
            else:
                print(f"   ❌ Team workflow failed: {result.get('error', 'Unknown error')}")
                self.test_results['agent_team'] = {'success': False, 'error': result.get('error')}
                return False
                
        except Exception as e:
            print(f"   ❌ AgentTeamService test failed: {str(e)}")
            self.test_results['agent_team'] = {'success': False, 'error': str(e)}
            return False
    
    async def test_custom_tools(self):
        """Test custom tools functionality"""
        print("\n🛠️  Testing Custom Tools...")
        
        try:
            from tools.file_extraction_tools import file_extraction_tools
            from tools.categorization_tools import categorization_tools
            from tools.visualization_tools import visualization_tools
            
            # Test file extraction tool
            sample_file = self.create_sample_csv()
            extraction_result = file_extraction_tools.extract_csv_data(sample_file)
            
            if extraction_result.get('success', False):
                print(f"   ✅ File extraction tool working")
                print(f"   📊 Extracted {len(extraction_result['transactions'])} transactions")
            else:
                print(f"   ❌ File extraction tool failed: {extraction_result.get('error')}")
                return False
            
            # Test categorization tool
            sample_transaction = extraction_result['transactions'][0]
            cat_result = await categorization_tools.categorize_single_transaction(
                sample_transaction['description'],
                sample_transaction['amount'],
                sample_transaction['transaction_type']
            )
            
            if cat_result.get('category'):
                print(f"   ✅ Categorization tool working")
                print(f"   🏷️  Sample category: {cat_result['category']} (confidence: {cat_result.get('confidence', 0):.2f})")
            else:
                print(f"   ❌ Categorization tool failed")
                return False
            
            # Test visualization tool
            category_data = {'Food & Dining': 5000, 'Transportation': 3000, 'Shopping': 4000}
            viz_result = visualization_tools.create_category_pie_chart(category_data)
            
            if not viz_result.get('error'):
                print(f"   ✅ Visualization tool working")
                print(f"   📊 Chart type: {viz_result.get('chart_type', 'Unknown')}")
            else:
                print(f"   ❌ Visualization tool failed: {viz_result.get('error')}")
                return False
            
            self.test_results['custom_tools'] = {'success': True}
            return True
            
        except Exception as e:
            print(f"   ❌ Custom tools test failed: {str(e)}")
            self.test_results['custom_tools'] = {'success': False, 'error': str(e)}
            return False
    
    async def run_comprehensive_test(self):
        """Run comprehensive test suite for all agents"""
        print("🧪 Starting Comprehensive Agent Test Suite")
        print("=" * 60)
        
        # Test order matters due to dependencies
        tests = [
            ("File Processor", self.test_file_processor_agent),
            ("Categorizer", self.test_categorizer_agent),
            ("Insights", self.test_insights_agent),
            ("Agent Team", self.test_agent_team_service),
            ("Custom Tools", self.test_custom_tools)
        ]
        
        passed_tests = 0
        
        for test_name, test_func in tests:
            try:
                success = await test_func()
                if success:
                    passed_tests += 1
            except Exception as e:
                print(f"   ❌ {test_name} test crashed: {str(e)}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 AGENT TEST SUMMARY")
        print("=" * 60)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            print(f"   {test_name.upper():<15}: {status}")
            if not result.get('success', False) and result.get('error'):
                print(f"   {'':>17} Error: {result['error'][:50]}...")
        
        print(f"\n📊 Overall Result: {passed_tests}/{len(tests)} tests passed")
        
        if passed_tests == len(tests):
            print("🎉 All agent tests passed! The system is working correctly.")
            return True
        else:
            print("⚠️  Some agent tests failed. Check the errors above.")
            self._print_troubleshooting_tips()
            return False
    
    def _print_troubleshooting_tips(self):
        """Print troubleshooting tips based on failed tests"""
        print("\n🔧 TROUBLESHOOTING TIPS:")
        
        if not self.test_results.get('file_processor', {}).get('success', False):
            print("   • Check file processing dependencies (pandas, openpyxl, PyPDF2)")
            print("   • Verify file permissions and temporary directory access")
        
        if not self.test_results.get('categorizer', {}).get('success', False):
            print("   • Verify Gemini API key and connectivity")
            print("   • Check if categorization models are accessible")
            print("   • Ensure Agno framework is properly installed")
        
        if not self.test_results.get('insights', {}).get('success', False):
            print("   • Verify Gemini Flash model availability")
            print("   • Check insights generation prompts")
        
        if not self.test_results.get('agent_team', {}).get('success', False):
            print("   • Check agent team configuration")
            print("   • Verify workflow orchestration logic")
        
        if not self.test_results.get('custom_tools', {}).get('success', False):
            print("   • Check custom tool implementations")
            print("   • Verify tool registration with agents")
    
    def cleanup(self):
        """Clean up test resources"""
        if self.sample_csv_file and os.path.exists(self.sample_csv_file):
            try:
                os.unlink(self.sample_csv_file)
            except:
                pass

async def test_individual_agent(agent_name: str):
    """Test individual agent"""
    suite = AgentTestSuite()
    
    try:
        if agent_name == "file_processor":
            success = await suite.test_file_processor_agent()
        elif agent_name == "categorizer":
            # Need file processor first
            await suite.test_file_processor_agent()
            success = await suite.test_categorizer_agent()
        elif agent_name == "insights":
            # Need both previous agents
            await suite.test_file_processor_agent()
            await suite.test_categorizer_agent()
            success = await suite.test_insights_agent()
        elif agent_name == "team":
            success = await suite.test_agent_team_service()
        elif agent_name == "tools":
            success = await suite.test_custom_tools()
        else:
            print(f"❌ Unknown agent: {agent_name}")
            return False
        
        return success
        
    finally:
        suite.cleanup()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AI Agents functionality")
    parser.add_argument(
        "--agent",
        choices=["file_processor", "categorizer", "insights", "team", "tools", "all"],
        default="all",
        help="Specific agent to test"
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.add(sys.stdout, level="DEBUG")
    
    try:
        if args.agent == "all":
            suite = AgentTestSuite()
            try:
                success = asyncio.run(suite.run_comprehensive_test())
            finally:
                suite.cleanup()
        else:
            success = asyncio.run(test_individual_agent(args.agent))
        
        if success:
            print(f"\n✅ {args.agent.upper()} test completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ {args.agent.upper()} test failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        sys.exit(1)