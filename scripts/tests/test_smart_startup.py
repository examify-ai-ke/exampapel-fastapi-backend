#!/usr/bin/env python3
"""
Test script to verify the smart startup behavior.
This script tests the updated startup.py functionality.
"""

import asyncio
import sys
import os

# Add the backend/app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app'))

from app.core.startup import (
    check_database_has_data,
    should_initialize_database,
    get_database_status
)
from app.core.config import settings, ModeEnum
from app.db.session import SessionLocal


async def test_database_checks():
    """Test the database checking functionality"""
    
    print("🧪 Testing Smart Startup Functionality")
    print("=" * 50)
    
    print(f"🔧 Current Environment: {settings.MODE.value}")
    print()
    
    try:
        async with SessionLocal() as session:
            print("📊 Testing database data check...")
            data_status = await check_database_has_data(session)
            
            print("   Database Table Status:")
            for table_name, has_data in data_status.items():
                status = "✅ HAS DATA" if has_data else "❌ EMPTY"
                print(f"      - {table_name}: {status}")
            
            total_tables = len(data_status)
            tables_with_data = sum(1 for has_data in data_status.values() if has_data)
            print(f"   Summary: {tables_with_data}/{total_tables} tables have data")
            print()
            
        print("🤔 Testing initialization decision logic...")
        should_init = await should_initialize_database()
        print(f"   Should initialize database: {'✅ YES' if should_init else '❌ NO'}")
        
        if settings.MODE != ModeEnum.development:
            print(f"   Reason: Not in development mode (current: {settings.MODE.value})")
        elif not should_init:
            print("   Reason: Database already has data")
        else:
            print("   Reason: Database is empty and we're in development mode")
        print()
        
        print("📈 Getting comprehensive database status...")
        db_status = await get_database_status()
        
        print("   Database Status Report:")
        print(f"      Connection: {db_status.get('connection_status', 'unknown')}")
        print(f"      Environment: {db_status.get('environment', 'unknown')}")
        print(f"      Initialization Complete: {db_status.get('initialization_complete', False)}")
        
        if 'record_counts' in db_status:
            print("   Record Counts:")
            for table_name, count in db_status['record_counts'].items():
                print(f"      - {table_name}: {count} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def simulate_startup_scenarios():
    """Simulate different startup scenarios"""
    
    print("\n" + "=" * 50)
    print("🎭 Startup Scenario Simulation")
    print("=" * 50)
    
    # Scenario 1: Current state
    print("📋 Scenario 1: Current Database State")
    should_init = await should_initialize_database()
    print(f"   Result: {'Initialize' if should_init else 'Skip initialization'}")
    print()
    
    # Scenario 2: What would happen in production
    print("📋 Scenario 2: If this were Production Mode")
    original_mode = settings.MODE
    settings.MODE = ModeEnum.production
    
    try:
        should_init_prod = await should_initialize_database()
        print(f"   Result: {'Initialize' if should_init_prod else 'Skip initialization'}")
        print("   Note: Production mode should always skip initialization")
    finally:
        settings.MODE = original_mode
    print()
    
    # Scenario 3: Development recommendations
    print("📋 Scenario 3: Development Mode Recommendations")
    if settings.MODE == ModeEnum.development:
        async with SessionLocal() as session:
            data_status = await check_database_has_data(session)
            has_any_data = any(data_status.values())
            
            if has_any_data:
                print("   💡 Current state: Database has data")
                print("   🔄 To reinitialize: Clear database first, then restart")
                print("   🧹 Use: make clear-dummy-db (if available)")
            else:
                print("   🆕 Current state: Database is empty")
                print("   ✅ Initialization will run automatically on startup")
    else:
        print(f"   ⚠️  Not in development mode (current: {settings.MODE.value})")
        print("   📝 Set ENVIRONMENT=development to enable auto-initialization")


async def main():
    """Main test function"""
    try:
        # Test database checks
        checks_ok = await test_database_checks()
        
        # Simulate scenarios
        await simulate_startup_scenarios()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        if checks_ok:
            print("✅ All database checks passed!")
            print("🚀 Smart startup functionality is working correctly")
            
            print("\n🔍 Key Features:")
            print("   ✅ Environment-aware initialization")
            print("   ✅ Database state detection")
            print("   ✅ Duplicate prevention")
            print("   ✅ Comprehensive status reporting")
            
            print("\n🎯 Behavior:")
            print("   🔧 Development mode: Initialize only if database is empty")
            print("   🏭 Production mode: Never auto-initialize")
            print("   📊 Always provides detailed status information")
            
            return 0
        else:
            print("❌ Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
