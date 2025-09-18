# backend/services/agent_team_service.py

from agno.team import Team
from agno.agent import Agent
from agents.file_processor_agent import file_processor_agent
from agents.categorizer_agent import categorizer_agent
from agents.insights_agent import insights_agent
from tools.visualization_tools import visualization_tools
from typing import Dict, Any
from loguru import logger
import asyncio

class AgentTeamService:
    """Service to orchestrate the multi-agent system for finance management"""
    members = [
            file_processor_agent.agent,
            categorizer_agent.agent,
            insights_agent.agent
        ]
    def __init__(self):
        # Create agent team
        self.team = Team(
            name="FinanceManagerTeam",
            description="Multi-agent system for processing bank statements and generating financial insights",
            members=[
                file_processor_agent.agent,
                categorizer_agent.agent,
                insights_agent.agent
            ],
            instructions=[
            "Work together to provide comprehensive financial analysis.",
            "FileProcessorAgent handles file extraction and data validation.",
            "CategorizerAgent categorizes transactions using AI and rules.",
            "InsightsAgent generates actionable financial insights.",
            "Coordinate to ensure data flows smoothly between agents.",
            "Handle errors gracefully and provide meaningful feedback.",
            "Maintain data accuracy and consistency throughout the pipeline."
           ],
           debug_mode=True
        )
        

        
    async def process_complete_workflow(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """Execute the complete workflow from file upload to insights generation"""
        try:
            logger.info(f"Starting complete workflow for file: {file_name}")
            workflow_results = {}

            # Step 1: File Processing
            logger.info("Step 1: Processing uploaded file")
            processing_result = await file_processor_agent.process_uploaded_file(file_path, file_name)

            if not processing_result.get('success', False):
                raise Exception(f"File processing failed: {processing_result.get('error', 'Unknown error')}")

            workflow_results['file_processing'] = {
                'success': True,
                'stats': processing_result.get('extraction_stats', {}),
                'processed_statement': processing_result['processed_statement']
            }

            # Step 2: Transaction Categorization
            logger.info("Step 2: Categorizing transactions")
            categorization_result = await categorizer_agent.categorize_transactions(
                processing_result['processed_statement']
            )

            if not categorization_result.get('success', False):
                raise Exception(f"Categorization failed: {categorization_result.get('error', 'Unknown error')}")

            workflow_results['categorization'] = {
                'success': True,
                'stats': categorization_result.get('categorization_stats', {}),
                'categorized_statement': categorization_result['categorized_statement']
            }

            # Step 3: Category Summary
            logger.info("Step 3: Generating category summary")
            category_summary = categorizer_agent.get_category_summary(
                categorization_result['categorized_statement'].transactions
            )

            workflow_results['category_summary'] = category_summary

            # Step 4: Insights Generation
            logger.info("Step 4: Generating financial insights")
            insights_result = await insights_agent.generate_comprehensive_insights(
                categorization_result['categorized_statement']
            )

            if not insights_result.get('success', False):
                raise Exception(f"Insights generation failed: {insights_result.get('error', 'Unknown error')}")

            workflow_results['insights'] = {
                'success': True,
                'insights_summary': insights_result['insights_summary'],
                'ai_insights': insights_result.get('ai_insights', {}),
                'analysis_stats': insights_result.get('analysis_stats', {})
            }

            # Step 5: Visualization Generation
            logger.info("Step 5: Creating visualizations")
            try:
                category_distribution = category_summary.get('category_distribution', {})
                transactions_list = [
                    {
                        'date': t.date.isoformat(),
                        'description': t.description,
                        'amount': t.amount,
                        'transaction_type': t.transaction_type.value,
                        'category': t.category.value if t.category else 'Other',
                        'balance': t.balance
                    }
                    for t in categorization_result['categorized_statement'].transactions
                ]

                dashboard_result = visualization_tools.create_comprehensive_dashboard(
                    transactions_list, category_distribution
                )

                workflow_results['visualizations'] = {
                    'success': True,
                    'dashboard': dashboard_result
                }

            except Exception as viz_error:
                logger.warning(f"Visualization generation failed: {str(viz_error)}")
                workflow_results['visualizations'] = {
                    'success': False,
                    'error': str(viz_error)
                }

            final_result = {
                'success': True,
                'workflow_completed': True,
                'processed_statement': workflow_results['categorization']['categorized_statement'],
                'insights_summary': workflow_results['insights']['insights_summary'],
                'category_summary': workflow_results['category_summary'],
                'visualizations': workflow_results['visualizations'],
                'processing_stats': {
                    'file_processing': workflow_results['file_processing']['stats'],
                    'categorization': workflow_results['categorization']['stats'],
                    'insights': workflow_results['insights']['analysis_stats']
                }
            }

            logger.info("Complete workflow executed successfully")
            return final_result

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'workflow_completed': False,
                'partial_results': workflow_results if 'workflow_results' in locals() else {}
            }

    # --- Additional helper methods for separate tasks ---
    async def process_file_only(self, file_path: str, file_name: str) -> Dict[str, Any]:
        try:
            logger.info("Processing file extraction only")
            return await file_processor_agent.process_uploaded_file(file_path, file_name)
        except Exception as e:
            logger.error(f"File processing failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def categorize_only(self, processed_statement) -> Dict[str, Any]:
        try:
            logger.info("Processing categorization only")
            return await categorizer_agent.categorize_transactions(processed_statement)
        except Exception as e:
            logger.error(f"Categorization failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def generate_insights_only(self, categorized_statement) -> Dict[str, Any]:
        try:
            logger.info("Processing insights generation only")
            return await insights_agent.generate_comprehensive_insights(categorized_statement)
        except Exception as e:
            logger.error(f"Insights generation failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def create_visualizations_only(self, transactions_list, category_data) -> Dict[str, Any]:
        try:
            logger.info("Creating visualizations only")
            dashboard_result = visualization_tools.create_comprehensive_dashboard(
                transactions_list, category_data
            )
            return {'success': True, 'dashboard': dashboard_result}
        except Exception as e:
            logger.error(f"Visualization creation failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_team_status(self) -> Dict[str, Any]:
        try:
            return {
                'team_name': self.team.name,
                'agents_count': len(self.team.agents),
                'agents': [agent.name for agent in self.team.agents],
                'status': 'active',
                'capabilities': [
                    'File Processing (CSV, Excel, PDF)',
                    'AI-Powered Transaction Categorization',
                    'Financial Insights Generation',
                    'Interactive Visualizations',
                    'Multi-format Support'
                ]
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

# Create service instance
agent_team_service = AgentTeamService()
