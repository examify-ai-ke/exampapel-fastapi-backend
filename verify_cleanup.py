#!/usr/bin/env python3
"""
Verification script to ensure all legacy endpoints and references have been properly removed.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def check_removed_files():
    """Check that the old endpoint files have been removed"""
    print("🗑️  Checking removed files...")
    
    removed_files = [
        "backend/app/app/api/v1/endpoints/main_question.py",
        "backend/app/app/api/v1/endpoints/sub_question.py",
        "backend/app/app/crud/main_question_crud.py",
        "backend/app/app/crud/sub_question_crud.py"
    ]
    
    all_removed = True
    for file_path in removed_files:
        if os.path.exists(file_path):
            print(f"   ❌ File still exists: {file_path}")
            all_removed = False
        else:
            print(f"   ✅ File removed: {file_path}")
    
    return all_removed

def check_legacy_references():
    """Check for any remaining legacy references"""
    print("\n🔍 Checking for legacy references...")
    
    # Check for MainQuestion/SubQuestion imports or aliases
    code, stdout, stderr = run_command(
        'grep -r "MainQuestion\|SubQuestion" backend/app/app/ --include="*.py" | grep -v "class MainQuestion\|class SubQuestion"'
    )
    
    if code == 0 and stdout.strip():
        print("   ❌ Found legacy references:")
        for line in stdout.strip().split('\n'):
            print(f"      {line}")
        return False
    else:
        print("   ✅ No legacy references found")
        return True

def check_api_routes():
    """Check that legacy routes are not registered"""
    print("\n🛣️  Checking API routes...")
    
    api_file = "backend/app/app/api/v1/api.py"
    if os.path.exists(api_file):
        with open(api_file, 'r') as f:
            content = f.read()
            
        if "main_question" in content or "sub_question" in content:
            print("   ❌ Legacy routes still registered in api.py")
            return False
        else:
            print("   ✅ Legacy routes removed from api.py")
            return True
    else:
        print("   ❌ API file not found")
        return False

def check_unified_endpoint():
    """Check that the unified questions endpoint exists"""
    print("\n🔗 Checking unified endpoint...")
    
    questions_file = "backend/app/app/api/v1/endpoints/questions.py"
    if os.path.exists(questions_file):
        print("   ✅ Unified questions endpoint exists")
        return True
    else:
        print("   ❌ Unified questions endpoint not found")
        return False

def check_schema_cleanup():
    """Check that schemas have been cleaned up"""
    print("\n📋 Checking schema cleanup...")
    
    schema_file = "backend/app/app/schemas/question_schema.py"
    if os.path.exists(schema_file):
        with open(schema_file, 'r') as f:
            content = f.read()
        
        # Check for proper schema structure
        has_main_create = "class MainQuestionCreate" in content
        has_sub_create = "class SubQuestionCreate" in content
        has_main_read = "class MainQuestionRead" in content
        has_sub_read = "class SubQuestionRead" in content
        has_question_read = "class QuestionRead" in content
        
        if all([has_main_create, has_sub_create, has_main_read, has_sub_read, has_question_read]):
            print("   ✅ Schema structure is correct")
            return True
        else:
            print("   ❌ Schema structure issues found")
            return False
    else:
        print("   ❌ Question schema file not found")
        return False

def check_model_cleanup():
    """Check that model aliases have been removed"""
    print("\n🏗️  Checking model cleanup...")
    
    # Check question model
    question_model = "backend/app/app/models/question_model.py"
    if os.path.exists(question_model):
        with open(question_model, 'r') as f:
            content = f.read()
        
        if "MainQuestion = Question" in content or "SubQuestion = Question" in content:
            print("   ❌ Model aliases still present in question_model.py")
            return False
        else:
            print("   ✅ Model aliases removed from question_model.py")
    
    # Check models __init__.py
    models_init = "backend/app/app/models/__init__.py"
    if os.path.exists(models_init):
        with open(models_init, 'r') as f:
            content = f.read()
        
        if "MainQuestion" in content or "SubQuestion" in content:
            print("   ❌ Model aliases still present in models/__init__.py")
            return False
        else:
            print("   ✅ Model aliases removed from models/__init__.py")
            return True
    
    return False

def main():
    """Main verification function"""
    print("🧹 FastAPI Question Model Cleanup Verification")
    print("=" * 50)
    
    checks = [
        ("Removed Files", check_removed_files),
        ("Legacy References", check_legacy_references),
        ("API Routes", check_api_routes),
        ("Unified Endpoint", check_unified_endpoint),
        ("Schema Cleanup", check_schema_cleanup),
        ("Model Cleanup", check_model_cleanup),
    ]
    
    all_passed = True
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
            if not result:
                all_passed = False
        except Exception as e:
            print(f"   ❌ Error during {check_name}: {e}")
            results.append((check_name, False))
            all_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 CLEANUP VERIFICATION SUMMARY")
    print("=" * 50)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    if all_passed:
        print("\n🎉 All cleanup checks passed! The legacy endpoints have been successfully removed.")
        print("   The unified Question model and endpoints are ready to use.")
        return 0
    else:
        print("\n⚠️  Some cleanup checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
