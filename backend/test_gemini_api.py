"""
Test script to verify Gemini API connection and model functionality
"""
import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def test_gemini_api_connection():
    """Test basic Gemini API connection"""
    print("🤖 Testing Gemini API Connection...")
    print("=" * 50)
    
    # Get API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in environment variables")
        print("Please set GEMINI_API_KEY in your .env file")
        return False
    
    print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Configure the API
    genai.configure(api_key=api_key)
    
    try:
        # List available models
        print("\n📋 Available Models:")
        models = []
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                models.append(model.name)
                print(f"  - {model.name}")
        
        if not models:
            print("❌ No models available for content generation")
            return False
        
        print(f"\n✓ Found {len(models)} available models")
        return True
        
    except Exception as e:
        print(f"❌ Error connecting to Gemini API: {str(e)}")
        return False

def test_categorization_model():
    """Test the categorization model (Gemini Pro)"""
    print("\n🎯 Testing Categorization Model...")
    print("=" * 50)
    
    try:
        # Initialize the model
        model = genai.GenerativeModel(os.getenv('CATEGORIZATION_MODEL'))
        
        # Test prompt for transaction categorization
        test_prompt = """
        You are an expert financial transaction categorization specialist.
        
        Please categorize the following transaction:
        Date: 2024-01-15
        Description: STARBUCKS COFFEE #12345
        Amount: 456.50
        Type: debit
        
        Respond with JSON:
        {
            "category": "Primary Category",
            "subcategory": "Specific Subcategory", 
            "confidence": 0.95,
            "reasoning": "Clear explanation"
        }
        """
        
        print("📤 Sending test categorization request...")
        response = model.generate_content(test_prompt)
        
        print("📥 Response received:")
        print(response.text)
        
        # Try to parse as JSON
        try:
            json_response = json.loads(response.text.strip())
            print("✓ Response is valid JSON")
            
            required_fields = ['category', 'confidence', 'reasoning']
            for field in required_fields:
                if field in json_response:
                    print(f"✓ Has required field: {field}")
                else:
                    print(f"⚠️  Missing field: {field}")
            
        except json.JSONDecodeError:
            print("⚠️  Response is not valid JSON, but model is working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing categorization model: {str(e)}")
        return False

def test_insights_model():
    """Test the insights model (Gemini Flash)"""
    print("\n📊 Testing Insights Model...")
    print("=" * 50)
    
    try:
        # Initialize the model
        model = genai.GenerativeModel(os.getenv('INSIGHTS_MODEL'))
        
        # Test prompt for insights generation
        test_prompt = """
        You are an expert financial analyst. Generate insights for this financial data:
        
        Total Income: ₹50,000
        Total Spending: ₹30,000  
        Savings Rate: 40%
        Top Categories: Food (₹8,000), Rent (₹15,000), Transport (₹4,000)
        
        Provide 3 key insights and 2 recommendations in JSON format:
        {
            "key_insights": ["insight 1", "insight 2", "insight 3"],
            "recommendations": ["recommendation 1", "recommendation 2"]
        }
        """
        
        print("📤 Sending test insights request...")
        response = model.generate_content(test_prompt)
        
        print("📥 Response received:")
        print(response.text)
        
        # Try to parse as JSON
        try:
            json_response = json.loads(response.text.strip())
            print("✓ Response is valid JSON")
            
            if 'key_insights' in json_response and 'recommendations' in json_response:
                print("✓ Has required insights structure")
            else:
                print("⚠️  Missing insights structure")
                
        except json.JSONDecodeError:
            print("⚠️  Response is not valid JSON, but model is working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing insights model: {str(e)}")
        return False

def test_model_parameters():
    """Test different model parameters"""
    print("\n⚙️  Testing Model Parameters...")
    print("=" * 50)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-002')
        
        # Test with generation config
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=1000,
        )
        
        test_prompt = "Explain what a bank transaction is in exactly 50 words."
        
        print("📤 Testing with custom parameters...")
        response = model.generate_content(
            test_prompt,
            generation_config=generation_config
        )
        
        print("📥 Response:")
        print(response.text)
        print(f"✓ Response length: {len(response.text)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing model parameters: {str(e)}")
        return False

def test_error_handling():
    """Test error handling and edge cases"""
    print("\n🛡️  Testing Error Handling...")
    print("=" * 50)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-002')
        
        # Test with empty prompt
        print("Testing empty prompt...")
        try:
            response = model.generate_content("")
            print("⚠️  Empty prompt accepted")
        except Exception as e:
            print(f"✓ Empty prompt correctly rejected: {str(e)}")
        
        # Test with very long prompt
        print("\nTesting very long prompt...")
        long_prompt = "Categorize this transaction: " + "A" * 10000
        try:
            response = model.generate_content(long_prompt)
            print("✓ Long prompt handled successfully")
        except Exception as e:
            print(f"⚠️  Long prompt failed: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in error handling test: {str(e)}")
        return False

async def test_async_functionality():
    """Test async functionality"""
    print("\n⚡ Testing Async Functionality...")
    print("=" * 50)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-002')
        
        print("📤 Testing async content generation...")
        
        # Simple async test
        test_prompt = "What is 2+2? Give a brief answer."
        response = await model.generate_content_async(test_prompt)
        
        print("📥 Async response received:")
        print(response.text)
        print("✓ Async functionality working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing async functionality: {str(e)}")
        return False

def run_all_tests():
    """Run all Gemini API tests"""
    print("🚀 Finance Manager - Gemini API Test Suite")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Basic API Connection
    results['connection'] = test_gemini_api_connection()
    
    if not results['connection']:
        print("\n❌ API connection failed. Cannot proceed with other tests.")
        return False
    
    # Test 2: Categorization Model
    results['categorization'] = test_categorization_model()
    
    # Test 3: Insights Model  
    results['insights'] = test_insights_model()
    
    # Test 4: Model Parameters
    results['parameters'] = test_model_parameters()
    
    # Test 5: Error Handling
    results['error_handling'] = test_error_handling()
    
    # Test 6: Async Functionality
    print("\nRunning async test...")
    try:
        results['async'] = asyncio.run(test_async_functionality())
    except Exception as e:
        print(f"❌ Async test failed: {str(e)}")
        results['async'] = False
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title():<20} {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Gemini API is ready for Finance Manager.")
        return True
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return False

def check_environment():
    """Check environment setup"""
    print("\n🔍 Environment Check")
    print("=" * 30)
    
    # Check .env file
    if os.path.exists('.env'):
        print("✓ .env file found")
    else:
        print("⚠️  .env file not found")
        print("Create .env file with: GEMINI_API_KEY=your_key_here")
    
    # Check required packages
    required_packages = [
        'google-generativeai',
        'python-dotenv'
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            print(f"Install with: pip install {package}")

if __name__ == "__main__":
    try:
        check_environment()
        success = run_all_tests()
        
        if success:
            print("\n✅ Gemini API is configured correctly!")
            print("You can now run the Finance Manager application.")
        else:
            print("\n❌ Some issues found. Please resolve them before running the app.")
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        print("Please check your setup and try again.")