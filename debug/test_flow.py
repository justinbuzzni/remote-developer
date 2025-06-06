#!/usr/bin/env python3
"""Test the execution flow"""

import subprocess
import time

def test_subprocess_flow():
    """Test if subprocess properly returns"""
    print("Starting test...")
    
    # Test command that outputs multiple things
    test_cmd = '''
    echo "Step 1"
    sleep 1
    echo "Step 2"
    sleep 1
    echo "Step 3"
    '''
    
    print("Running subprocess...")
    process = subprocess.Popen(
        ['bash', '-c', test_cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    print("Reading output...")
    for line in iter(process.stdout.readline, ''):
        if line:
            print(f"Got: {line.rstrip()}")
    
    return_code = process.wait()
    print(f"Process completed with return code: {return_code}")
    
    print("Continuing after subprocess...")
    print("Next step would execute here")
    print("Final step")

if __name__ == "__main__":
    test_subprocess_flow()
    print("Script completed!")