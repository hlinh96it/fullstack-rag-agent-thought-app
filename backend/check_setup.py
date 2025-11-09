#!/usr/bin/env python3
"""
Setup verification script for the Agentic RAG backend.
Checks all dependencies and configurations before running.
"""

import os
import sys
import warnings

# Suppress warnings for cleaner output
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '0'
os.environ['GRPC_POLL_STRATEGY'] = 'poll'
warnings.filterwarnings('ignore')

def check_python_version():
    """Check Python version."""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)")
        return False


def check_imports():
    """Check if all required packages are installed."""
    print("\n🔍 Checking required packages...")
    
    packages = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'pydantic': 'Pydantic',
        'pymongo': 'MongoDB Driver',
        'langchain': 'LangChain',
        'langchain_openai': 'LangChain OpenAI',
        'langchain_milvus': 'LangChain Milvus',
        'langgraph': 'LangGraph',
        'httpx': 'HTTPX',
        'boto3': 'AWS SDK (Boto3)',
    }
    
    all_ok = True
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} - not installed")
            all_ok = False
    
    return all_ok


def check_env_file():
    """Check if .env file exists."""
    print("\n🔍 Checking .env file...")
    
    env_files = ['.env', '../.env']
    found = False
    
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"   ✅ Found {env_file}")
            found = True
            break
    
    if not found:
        print(f"   ❌ .env file not found")
        print(f"   💡 Create a .env file with required credentials")
    
    return found


def check_env_variables():
    """Check if required environment variables are set."""
    print("\n🔍 Checking environment variables...")
    
    try:
        from src.config import Settings
        settings = Settings()
        
        checks = {
            'OpenAI API Key': settings.openai.openai_api_key,
            'OpenAI Model': settings.openai.model_name,
            'MongoDB URI': settings.mongo_db.mongo_uri,
            'Milvus URI': settings.milvus.uri,
            'Jina API Key': settings.jina.jina_api_key,
        }
        
        all_ok = True
        for name, value in checks.items():
            if value:
                masked = value[:8] + '...' if len(value) > 8 else '***'
                print(f"   ✅ {name}: {masked}")
            else:
                print(f"   ❌ {name}: not set")
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        print(f"   ❌ Error loading settings: {e}")
        return False


def check_connections():
    """Check connections to external services."""
    print("\n🔍 Checking service connections...")
    
    try:
        from src.config import Settings
        from src.services.database.factory import make_database_client, make_milvus_client
        from src.services.chat.factory import make_chat_client
        
        settings = Settings()
        
        # MongoDB
        try:
            mongo_client = make_database_client(settings)
            print("   ✅ MongoDB connected")
        except Exception as e:
            print(f"   ❌ MongoDB connection failed: {e}")
        
        # Milvus
        try:
            milvus_client = make_milvus_client(settings)
            print("   ✅ Milvus connected")
        except Exception as e:
            print(f"   ❌ Milvus connection failed: {e}")
        
        # OpenAI (lightweight check)
        try:
            chat_client = make_chat_client(settings)
            print("   ✅ OpenAI client initialized")
        except Exception as e:
            print(f"   ❌ OpenAI client initialization failed: {e}")
            
    except Exception as e:
        print(f"   ❌ Error importing modules: {e}")


def main():
    """Run all checks."""
    print("=" * 60)
    print("🚀 Agentic RAG Backend Setup Verification")
    print("=" * 60)
    
    results = []
    
    # Run checks
    results.append(("Python Version", check_python_version()))
    results.append(("Required Packages", check_imports()))
    results.append(("Environment File", check_env_file()))
    results.append(("Environment Variables", check_env_variables()))
    
    # Connection checks (only if previous checks pass)
    if all(r[1] for r in results):
        print("\n" + "=" * 60)
        check_connections()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All checks passed! You're ready to run the backend.")
        print("\n💡 To start the server, run:")
        print("   uvicorn src.main:app --reload")
        print("\n💡 To test the agent, run:")
        print("   python test_agent.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\n💡 Common fixes:")
        print("   - Install packages: poetry install")
        print("   - Create .env file: cp .env.example .env")
        print("   - Fill in credentials in .env file")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
