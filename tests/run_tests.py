"""
Run all tests for the Nexus Agents system.
"""
import asyncio
import os
import sys
import importlib
from dotenv import load_dotenv

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


async def run_tests():
    """Run all tests."""
    # Get all test files
    test_files = [f for f in os.listdir(os.path.dirname(__file__)) if f.startswith("test_") and f.endswith(".py") and f != "run_tests.py"]
    
    # Run each test
    for test_file in test_files:
        test_name = test_file[:-3]  # Remove .py extension
        print(f"\n=== Running {test_name} ===\n")
        
        try:
            # Import the test module
            module = importlib.import_module(f"tests.{test_name}")
            
            # Run the main function if it exists
            if hasattr(module, "main") and callable(module.main):
                await module.main()
            # Otherwise, run the test function if it exists
            elif hasattr(module, f"test_{test_name[5:]}") and callable(getattr(module, f"test_{test_name[5:]}")):
                test_func = getattr(module, f"test_{test_name[5:]}")
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
            else:
                print(f"No test function found in {test_name}")
        except Exception as e:
            print(f"Error running {test_name}: {e}")
    
    print("\n=== All tests completed ===")


if __name__ == "__main__":
    asyncio.run(run_tests())