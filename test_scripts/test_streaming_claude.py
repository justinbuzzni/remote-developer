#!/usr/bin/env python3
"""Test script to verify Claude output streaming"""

import subprocess
import time
import sys
import os
import select
import fcntl

def test_streaming_with_stdbuf():
    """Test streaming with stdbuf"""
    print("Testing with stdbuf...")
    
    # Simulate a claude-like command that outputs progressively
    test_command = '''
    for i in {1..10}; do
        echo "Processing step $i..."
        sleep 1
    done
    '''
    
    # Run with stdbuf
    cmd = f'stdbuf -o0 -e0 bash -c "{test_command}"'
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0
    )
    
    # Make stdout non-blocking
    fd = process.stdout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    output_buffer = b""
    while True:
        # Check if process has ended
        poll_status = process.poll()
        
        # Use select to check if data is available
        ready, _, _ = select.select([process.stdout], [], [], 0.1)
        
        if ready:
            try:
                # Read available data
                chunk = os.read(fd, 4096)
                if chunk:
                    output_buffer += chunk
                    
                    # Process complete lines
                    while b'\n' in output_buffer:
                        line, output_buffer = output_buffer.split(b'\n', 1)
                        print(f"[STREAM] {line.decode('utf-8', errors='replace')}")
                        sys.stdout.flush()
            except OSError:
                # No data available
                pass
        
        # If process ended and no more data, break
        if poll_status is not None and not ready:
            if output_buffer:
                print(f"[STREAM] {output_buffer.decode('utf-8', errors='replace')}")
            break
    
    return_code = process.wait()
    print(f"Process finished with return code: {return_code}")

def test_streaming_with_script():
    """Test streaming with script command"""
    print("\nTesting with script command...")
    
    # Simulate a claude-like command
    test_command = '''
    for i in {1..5}; do
        echo "Script output $i"
        sleep 1
    done
    '''
    
    # Run with script
    cmd = f'script -q -c "bash -c \\"{test_command}\\"" /dev/stdout'
    
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0
    )
    
    for line in iter(process.stdout.readline, ''):
        if line:
            print(f"[SCRIPT] {line.rstrip()}")
            sys.stdout.flush()
    
    return_code = process.wait()
    print(f"Process finished with return code: {return_code}")

def test_basic_streaming():
    """Test basic streaming without special tools"""
    print("\nTesting basic streaming...")
    
    test_command = '''
    export PYTHONUNBUFFERED=1
    for i in {1..5}; do
        echo "Basic output $i"
        sleep 1
    done
    '''
    
    process = subprocess.Popen(
        ['bash', '-c', test_command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,
        env={**os.environ, 'PYTHONUNBUFFERED': '1'}
    )
    
    for line in iter(process.stdout.readline, ''):
        if line:
            print(f"[BASIC] {line.rstrip()}")
            sys.stdout.flush()
    
    return_code = process.wait()
    print(f"Process finished with return code: {return_code}")

if __name__ == "__main__":
    print("Testing different streaming methods for Claude output...")
    print("=" * 60)
    
    # Test with stdbuf
    test_streaming_with_stdbuf()
    
    # Test with script
    test_streaming_with_script()
    
    # Test basic streaming
    test_basic_streaming()
    
    print("\nAll tests completed!")