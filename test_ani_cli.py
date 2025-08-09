import subprocess
import os

def test_ani_cli():
    """Simple test to check if ani-cli works"""
    git_bash_path = r"C:\Program Files\Git\bin\bash.exe"
    
    print("Testing ani-cli installation...")
    print(f"Git Bash path: {git_bash_path}")
    print(f"Git Bash exists: {os.path.exists(git_bash_path)}")
    
    try:
        # Test version command
        result = subprocess.run(
            [git_bash_path, "-c", "ani-cli --version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"Return code: {result.returncode}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ ani-cli is working!")
            
            # Test a simple search
            print("\nTesting a simple search...")
            result2 = subprocess.run(
                [git_bash_path, "-c", "ani-cli --help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"Help output: {result2.stdout[:500]}...")  # First 500 chars
            
        else:
            print("❌ ani-cli test failed")
            
    except Exception as e:
        print(f"❌ Error testing ani-cli: {e}")

if __name__ == "__main__":
    test_ani_cli()
