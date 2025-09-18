"""
Test script to verify Gemini API connectivity and functionality
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.gemini_service import gemini_service
from config.settings import settings
from loguru import logger
import json

async def test_gemini_connection():
    """Test basic Gemini API connection"""
    print("🔍 Testing Gemini API Connection...")
    
    try:
        result = await gemini_service.test_connection()
        
        if result.get('status') == 'connected':
            print("✅ Gemini API connection successful!")
            print(f"   📋 Categorization Model: {result.get('model_categorization')}")
            print(f"   💡 Insights Model: {result.get('model_insights')}")
            print(f"   📝 Response Preview: {result.get('response', 'N/A')}")
            return True
        else:
            print("❌ Gemini API connection failed!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False

async def test_transaction_categorization():
    """Test transaction categorization functionality"""
    print("\n🏷️  Testing Transaction Categorization...")
    
    # Test transactions
    test_transactions = [
        {
            "description": "SWIGGY BANGALORE",
            "amount": 450.0,
            "type": "debit"
        },
        {
            "description": "ATM WITHDRAWAL HDFC BANK",
            "amount": 2000.0,
            "type": "debit"
        },
        {
            "description": "UPI PAYTM GROCERY STORE",
            "amount": 1200.0,
            "type": "debit"
        },
        {
            "description": "SALARY CREDIT TCS LTD",
            "amount": 75000.0,
            "type": "credit"
        },
        {
            "description": "NETFLIX SUBSCRIPTION",
            "amount": 649.0,
            "type": "debit"
        }
    ]
    
    success_count = 0
    
    for i, transaction in enumerate(test_transactions, 1):
        try:
            print(f"\n   Transaction {i}: {transaction['description']}")
            
            result = await gemini_service.categorize_transaction(
                transaction['description'],
                transaction['amount'],
                transaction['type']
            )
            
            print(f"   ✅ Category: {result.get('category', 'Unknown')}")
            print(f"   🎯 Confidence: {result.get('confidence', 0):.2f}")
            print(f"   💭 Reasoning: {result.get('reasoning', 'N/A')[:50]}...")
            
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Categorization failed: {str(e)}")
    
    print(f"\n📊 Categorization Results: {success_count}/{len(test_transactions)} successful")
    return success_count == len(test_transactions)

async def test_insights_generation():
    """Test insights generation functionality"""
    print("\n💡 Testing Insights Generation...")
    
    # Sample transaction data
    sample_data = {
        'total_transactions': 25,
        'total_debits': 45000.0,
        'total_credits': 75000.0,
        'category_breakdown': {
            'Food & Dining': 8000.0,
            'Transportation': 5000.0,
            'Utilities': 3500.0,
            'Entertainment': 4000.0,
            'Groceries': 6000.0,
            'Shopping': 8500.0,
            'Others': 10000.0
        },
        'top_transactions': [
            {'description': 'Large Shopping Mall Purchase', 'amount': 5000.0, 'date': '2024-01-15'},
            {'description': 'Restaurant Dinner', 'amount': 2500.0, 'date': '2024-01-20'},
            {'description': 'Uber Rides', 'amount': 1800.0, 'date': '2024-01-25'}
        ]
    }
    
    try:
        result = await gemini_service.generate_insights(sample_data)
        
        print("   ✅ Insights generated successfully!")
        print(f"   📄 Summary: {result.get('summary', 'N/A')[:100]}...")
        
        if result.get('key_insights'):
            print(f"   🔍 Key Insights Count: {len(result['key_insights'])}")
            for insight in result['key_insights'][:2]:  # Show first 2
                print(f"      • {insight}")
        
        if result.get('recommendations'):
            print(f"   💡 Recommendations Count: {len(result['recommendations'])}")
            for rec in result['recommendations'][:2]:  # Show first 2
                print(f"      • {rec}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Insights generation failed: {str(e)}")
        return False

async def test_api_key_validity():
    """Test if API key is properly configured"""
    print("\n🔑 Testing API Key Configuration...")
    
    if not settings.gemini_api_key:
        print("   ❌ No Gemini API key found in environment variables")
        print("   💡 Please set GEMINI_API_KEY in your .env file")
        return False
    
    if settings.gemini_api_key == "your_gemini_api_key_here":
        print("   ❌ Gemini API key is still the default placeholder")
        print("   💡 Please update GEMINI_API_KEY with your actual API key")
        return False
    
    # Check key format (basic validation)
    if len(settings.gemini_api_key) < 20:
        print("   ⚠️  API key seems unusually short")
        return False
    
    print(f"   ✅ API key configured (length: {len(settings.gemini_api_key)} characters)")
    print(f"   📋 Categorization Model: {settings.gemini_model_categorization}")
    print(f"   💡 Insights Model: {settings.gemini_model_insights}")
    
    return True

async def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("🧪 Starting Gemini API Comprehensive Test Suite")
    print("=" * 60)
    
    # Test results
    test_results = {}
    
    # 1. Test API key configuration
    test_results['api_key'] = await test_api_key_validity()
    
    # 2. Test connection
    test_results['connection'] = await test_gemini_connection()
    
    # 3. Test categorization (only if connection works)
    if test_results['connection']:
        test_results['categorization'] = await test_transaction_categorization()
    else:
        test_results['categorization'] = False
        print("\n🏷️  Skipping categorization test due to connection failure")
    
    # 4. Test insights generation (only if connection works)
    if test_results['connection']:
        test_results['insights'] = await test_insights_generation()
    else:
        test_results['insights'] = False
        print("\n💡 Skipping insights test due to connection failure")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.upper():<15}: {status}")
    
    print(f"\n📊 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Gemini API is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the configuration.")
        
        # Provide troubleshooting tips
        print("\n🔧 TROUBLESHOOTING TIPS:")
        
        if not test_results['api_key']:
            print("   • Check your GEMINI_API_KEY in .env file")
            print("   • Ensure you have a valid Google AI Studio API key")
            print("   • Visit: https://makersuite.google.com/app/apikey")
        
        if not test_results['connection']:
            print("   • Verify your internet connection")
            print("   • Check if the API key has proper permissions")
            print("   • Ensure Gemini API is not blocked by firewall")
        
        if test_results['connection'] and not test_results['categorization']:
            print("   • Categorization model might be overloaded, try again")
            print("   • Check model availability in your region")
        
        if test_results['connection'] and not test_results['insights']:
            print("   • Insights model might be overloaded, try again")
            print("   • Verify prompt formatting is correct")
        
        return False

def print_environment_info():
    """Print environment information"""
    print("\n🌍 ENVIRONMENT INFORMATION")
    print("-" * 40)
    print(f"   Python Version: {sys.version.split()[0]}")
    print(f"   Project Root: {project_root}")
    print(f"   Settings Debug: {settings.debug}")
    print(f"   Upload Directory: {settings.upload_dir}")
    print(f"   Max File Size: {settings.max_file_size}")
    print(f"   Allowed Extensions: {', '.join(settings.allowed_extensions)}")

async def test_individual_component(component: str):
    """Test individual component"""
    print(f"🧪 Testing {component.upper()} component...")
    
    if component == "connection":
        return await test_gemini_connection()
    elif component == "categorization":
        return await test_transaction_categorization()
    elif component == "insights":
        return await test_insights_generation()
    elif component == "api_key":
        return await test_api_key_validity()
    else:
        print(f"❌ Unknown component: {component}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Gemini API functionality")
    parser.add_argument(
        "--component", 
        choices=["connection", "categorization", "insights", "api_key", "all"],
        default="all",
        help="Specific component to test"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--env-info", 
        action="store_true",
        help="Show environment information"
    )
    
    args = parser.parse_args()
    
    if args.env_info:
        print_environment_info()
    
    if args.verbose:
        # Configure more detailed logging
        logger.add(
            sys.stdout,
            level="DEBUG",
            format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}"
        )
    
    try:
        if args.component == "all":
            success = asyncio.run(run_comprehensive_test())
        else:
            success = asyncio.run(test_individual_component(args.component))
        
        if success:
            print(f"\n✅ {args.component.upper()} test completed successfully!")
            sys.exit(0)
        else:
            print(f"\n❌ {args.component.upper()} test failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        sys.exit(1)