#!/usr/bin/env python3
"""
Test script to verify the pagination fix for ResponseValidationError.
"""

import sys
import os

# Add the backend/app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app'))

from fastapi_pagination import Page
from app.schemas.response_schema import create_response, IGetResponsePaginated, PageBase
from pydantic import ValidationError


def test_page_conversion():
    """Test that Page objects are properly converted by create_response"""
    
    print("🧪 Testing Page Object Conversion")
    print("=" * 40)
    
    # Create a mock Page object (similar to what fastapi-pagination returns)
    mock_items = [
        {"id": "1", "name": "Item 1"},
        {"id": "2", "name": "Item 2"},
        {"id": "3", "name": "Item 3"},
    ]
    
    mock_page = Page[dict](
        items=mock_items,
        total=10,
        page=1,
        size=3,
        pages=4
    )
    
    print(f"📊 Mock Page Object:")
    print(f"   - Items: {len(mock_page.items)}")
    print(f"   - Total: {mock_page.total}")
    print(f"   - Page: {mock_page.page}")
    print(f"   - Size: {mock_page.size}")
    print(f"   - Pages: {mock_page.pages}")
    print()
    
    try:
        print("🔄 Converting Page to Response...")
        response = create_response(data=mock_page)
        
        print("✅ Conversion successful!")
        print(f"   - Type: {type(response)}")
        
        # Check if it's the expected type
        if isinstance(response, IGetResponsePaginated):
            print("✅ Response is IGetResponsePaginated")
            print(f"   - Message: {response.message}")
            print(f"   - Data type: {type(response.data)}")
            
            if isinstance(response.data, PageBase):
                print("✅ Data is PageBase")
                print(f"   - Items count: {len(response.data.items)}")
                print(f"   - Total: {response.data.total}")
                print(f"   - Page: {response.data.page}")
                print(f"   - Size: {response.data.size}")
                print(f"   - Pages: {response.data.pages}")
                print(f"   - Previous page: {response.data.previous_page}")
                print(f"   - Next page: {response.data.next_page}")
            else:
                print(f"❌ Data is not PageBase, it's {type(response.data)}")
                return False
        else:
            print(f"❌ Response is not IGetResponsePaginated, it's {type(response)}")
            return False
        
        # Try to serialize to JSON (this is what FastAPI does)
        print("\n🔄 Testing JSON serialization...")
        try:
            if hasattr(response, 'model_dump'):
                json_data = response.model_dump()
                print("✅ JSON serialization successful!")
                print(f"   - Keys: {list(json_data.keys())}")
            else:
                print("⚠️  Response doesn't have model_dump method")
        except Exception as e:
            print(f"❌ JSON serialization failed: {e}")
            return False
        
        return True
        
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_cases():
    """Test edge cases for pagination"""
    
    print("\n🧪 Testing Edge Cases")
    print("=" * 40)
    
    test_cases = [
        {
            "name": "Empty page",
            "page": Page[dict](items=[], total=0, page=1, size=10, pages=0)
        },
        {
            "name": "Single page",
            "page": Page[dict](items=[{"id": "1"}], total=1, page=1, size=10, pages=1)
        },
        {
            "name": "Last page",
            "page": Page[dict](items=[{"id": "1"}], total=25, page=3, size=10, pages=3)
        },
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        try:
            response = create_response(data=test_case['page'])
            
            if isinstance(response, IGetResponsePaginated) and isinstance(response.data, PageBase):
                print(f"   ✅ {test_case['name']} - OK")
                
                # Check previous/next page logic
                page_data = response.data
                expected_prev = test_case['page'].page - 1 if test_case['page'].page > 1 else None
                expected_next = test_case['page'].page + 1 if test_case['page'].page < test_case['page'].pages else None
                
                if page_data.previous_page == expected_prev and page_data.next_page == expected_next:
                    print(f"   ✅ Previous/Next page logic correct")
                else:
                    print(f"   ❌ Previous/Next page logic incorrect")
                    print(f"      Expected prev: {expected_prev}, got: {page_data.previous_page}")
                    print(f"      Expected next: {expected_next}, got: {page_data.next_page}")
                    all_passed = False
            else:
                print(f"   ❌ {test_case['name']} - Failed")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ {test_case['name']} - Error: {e}")
            all_passed = False
    
    return all_passed


def main():
    """Main test function"""
    print("🧪 Pagination Fix Verification Test")
    print("=" * 50)
    
    try:
        # Test basic conversion
        basic_test = test_page_conversion()
        
        # Test edge cases
        edge_test = test_edge_cases()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        if basic_test and edge_test:
            print("✅ All tests passed!")
            print("🎉 The pagination fix should resolve the ResponseValidationError")
            print("\n🔍 What was fixed:")
            print("   ✅ Page objects are now properly converted to IGetResponsePaginated")
            print("   ✅ PageBase structure is correctly populated")
            print("   ✅ Previous/Next page logic works correctly")
            print("   ✅ JSON serialization works properly")
            print("\n🚀 Try the questions endpoint now:")
            print("   GET /questions")
            return 0
        else:
            print("❌ Some tests failed!")
            print("⚠️  The ResponseValidationError may still occur")
            return 1
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
