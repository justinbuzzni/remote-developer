# Claude Output Streaming Guide

## Overview

This document explains how the Remote Developer application streams output from `claude code --print` command in real-time.

## Problem

When running `claude code --print` through subprocess, the output is often buffered, meaning it doesn't appear in real-time but only after the command completes or the buffer fills up. This creates a poor user experience as users can't see the progress of their tasks.

## Solutions Implemented

### 1. Unbuffered Subprocess Execution

The `exec_in_devpod_stream_realtime` function uses several techniques to achieve real-time output:

- **Unbuffered I/O**: Sets `bufsize=0` in subprocess.Popen
- **Non-blocking I/O**: Uses `fcntl` to make the stdout pipe non-blocking
- **Select polling**: Uses `select.select()` to check for available data without blocking
- **Character-based reading**: Reads data in chunks and processes complete lines

### 2. Environment Variables

- **PYTHONUNBUFFERED=1**: Disables Python's output buffering
- This is set both in the subprocess environment and in the bash script

### 3. stdbuf Utility

The Claude execution script checks for and uses `stdbuf` when available:

```bash
stdbuf -o0 -e0 claude --print "task" 2>&1 | stdbuf -o0 tee output.txt
```

- `-o0`: Sets stdout to unbuffered
- `-e0`: Sets stderr to unbuffered

### 4. Fallback Methods

If `stdbuf` is not available, the script falls back to:

1. **script command**: Uses `script -q -c` to capture output with pseudo-terminal
2. **Basic execution**: Standard execution with tee

## Implementation Details

### Real-time Streaming Function

```python
def exec_in_devpod_stream_realtime(devpod_name: str, command: str, task_id: str, pod_name: str = None):
    # Sets up unbuffered subprocess
    # Uses non-blocking I/O with fcntl
    # Polls for data with select()
    # Processes output line by line
```

### Claude Script Modifications

The bash script that executes Claude includes:

1. Environment variable setting: `export PYTHONUNBUFFERED=1`
2. stdbuf wrapper when available
3. Multiple fallback methods for different environments

## Testing

Use the provided test script to verify streaming functionality:

```bash
python test_scripts/test_streaming_claude.py
```

This tests:
- Streaming with stdbuf
- Streaming with script command
- Basic streaming with environment variables

## Troubleshooting

If streaming is still not working in real-time:

1. **Check stdbuf availability**: Run `which stdbuf` in the devpod
2. **Verify environment**: Ensure PYTHONUNBUFFERED is set
3. **Container limitations**: Some container environments may have additional buffering
4. **Network latency**: kubectl exec may introduce delays in streaming

## Future Improvements

1. **WebSocket streaming**: Direct WebSocket connection to devpod for lower latency
2. **PTY allocation**: Use pseudo-terminal for better interactive output
3. **Custom output parser**: Parse Claude's specific output format for better progress tracking