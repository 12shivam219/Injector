#!/usr/bin/env python3
"""
Test script to verify the reorganized project structure works correctly.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all main imports work with the new structure."""
    print("🧪 TESTING REORGANIZED PROJECT STRUCTURE")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test resume customizer imports
    print("\n📦 Testing resume_customizer module:")
    try:
        from resume_customizer.parsers.text_parser import parse_input_text_restricted, RestrictedFormatError
        print("  ✅ parse_input_text_restricted imported successfully")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ Failed to import parse_input_text_restricted: {e}")
        tests_failed += 1
    
    try:
        from resume_customizer.parsers.text_parser import get_parser
        print("  ✅ get_parser imported successfully")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ Failed to import get_parser: {e}")
        tests_failed += 1
    
    # Test infrastructure imports
    print("\n🏗️ Testing infrastructure module:")
    try:
        from infrastructure.utilities.logger import get_logger
        print("  ✅ get_logger imported successfully")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ Failed to import get_logger: {e}")
        tests_failed += 1
    
    try:
        from infrastructure.security.security_enhancements import InputSanitizer
        print("  ✅ InputSanitizer imported successfully")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ Failed to import InputSanitizer: {e}")
        tests_failed += 1
    
    # Test restricted parser functionality
    print("\n🔍 Testing restricted parser functionality:")
    try:
        test_input = """Java
•	Test point 1
•	Test point 2"""
        
        points, stacks = parse_input_text_restricted(test_input)
        print(f"  ✅ Restricted parser works: {len(points)} points, {len(stacks)} stacks")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ Restricted parser failed: {e}")
        tests_failed += 1
    
    # Test invalid format rejection
    print("\n❌ Testing invalid format rejection:")
    try:
        invalid_input = "Java: • Point 1 • Point 2"
        points, stacks = parse_input_text_restricted(invalid_input)
        print(f"  ❌ Should have failed but got {len(points)} points")
        tests_failed += 1
    except RestrictedFormatError:
        print("  ✅ Invalid format correctly rejected")
        tests_passed += 1
    except Exception as e:
        print(f"  ⚠️ Unexpected error: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"  ✅ Passed: {tests_passed}")
    print(f"  ❌ Failed: {tests_failed}")
    
    if tests_failed == 0:
        print("\n🎉 ALL TESTS PASSED! The reorganized structure is working correctly.")
        return True
    else:
        print(f"\n⚠️ {tests_failed} tests failed. Some imports or functionality may need fixing.")
        return False


def test_directory_structure():
    """Test that the new directory structure exists."""
    print("\n📂 Testing directory structure:")
    
    expected_dirs = [
        "resume_customizer",
        "resume_customizer/parsers",
        "resume_customizer/processors", 
        "resume_customizer/detectors",
        "resume_customizer/formatters",
        "resume_customizer/email",
        "infrastructure",
        "infrastructure/config",
        "infrastructure/monitoring",
        "infrastructure/security",
        "infrastructure/async_processing",
        "infrastructure/utilities",
        "tests_new",
        "ui"
    ]
    
    all_exist = True
    for dir_path in expected_dirs:
        if os.path.exists(dir_path):
            print(f"  ✅ {dir_path}")
        else:
            print(f"  ❌ {dir_path} - MISSING")
            all_exist = False
    
    return all_exist


if __name__ == "__main__":
    print("🚀 Starting reorganized structure test...")
    
    structure_ok = test_directory_structure()
    imports_ok = test_imports()
    
    if structure_ok and imports_ok:
        print("\n🎯 SUCCESS: Reorganized project structure is working correctly!")
        print("\n📋 Next steps:")
        print("  1. Test the full Streamlit application")
        print("  2. Verify all UI components work")
        print("  3. Test resume processing functionality")
    else:
        print("\n⚠️ Some issues were found that need to be addressed.")