#!/usr/bin/env python3
"""Simple test to verify streaming is working"""

import subprocess
import time

def test_simple_streaming():
    """Test basic line-by-line streaming"""
    print("Testing simple line streaming...")
    
    # Create a test command that outputs multiple lines with delays
    test_cmd = '''
    for i in {1..5}; do
        echo "Line $i: $(date)"
        sleep 1
    done
    echo "All done!"
    '''
    
    process = subprocess.Popen(
        ['bash', '-c', test_cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    print("Starting to read output...")
    
    # Read output line by line
    for line in iter(process.stdout.readline, ''):
        if line:
            line_text = line.rstrip()
            print(f"[RECEIVED] {line_text}")
            # Flush to ensure immediate output
            import sys
            sys.stdout.flush()
    
    return_code = process.wait()
    print(f"Process completed with return code: {return_code}")

if __name__ == "__main__":
    test_simple_streaming()