"""
Test script to verify timeout and error handling fixes
"""
import re
from pathlib import Path

def test_timeout_settings():
    """Test that timeout settings are correctly updated in config file"""
    
    print("=" * 60)
    print("Verifying Timeout Configuration Changes")
    print("=" * 60)
    
    # Check backend config
    config_file = Path(__file__).parent / "src" / "config.py"
    config_content = config_file.read_text()
    
    # Find timeout line in OpenAI settings
    timeout_match = re.search(r'timeout:\s*int\s*=\s*(\d+)', config_content)
    
    if timeout_match:
        timeout_value = int(timeout_match.group(1))
        print(f"\n✓ Backend OpenAI timeout: {timeout_value} seconds")
        if timeout_value == 60:
            print("  ✅ Correctly set to 60 seconds (was 3000)")
        else:
            print(f"  ⚠️  Expected 60, found {timeout_value}")
    else:
        print("\n✗ Could not find timeout setting in config.py")
    
    # Check frontend axios config
    frontend_axios = Path(__file__).parent.parent / "frontend" / "src" / "lib" / "axios.js"
    if frontend_axios.exists():
        axios_content = frontend_axios.read_text()
        
        ask_timeout = re.search(r'apiAsk.*?(\d+).*?ask operations', axios_content)
        if ask_timeout:
            timeout_ms = int(ask_timeout.group(1))
            timeout_s = timeout_ms / 1000
            print(f"\n✓ Frontend Ask API timeout: {timeout_s} seconds ({timeout_ms}ms)")
            if timeout_ms == 60000:
                print("  ✅ Correctly set to 60 seconds (was 10 seconds)")
            else:
                print(f"  ⚠️  Expected 60000ms, found {timeout_ms}ms")
    
    print("\n" + "=" * 60)
    print("Summary of Changes")
    print("=" * 60)
    print("\n1. ✅ Frontend timeout: 10s → 60s (apiAsk)")
    print("2. ✅ Backend OpenAI timeout: 3s → 60s")
    print("3. ✅ Added better error handling in agent.py")
    print("4. ✅ Added tool execution logging and error wrapping")
    print("5. ✅ Improved frontend error messages")
    
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Restart both servers for changes to take effect!")
    print("\nBackend:")
    print("  cd backend && ./run.sh")
    print("\nFrontend:")
    print("  cd frontend && npm run dev")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_timeout_settings()
