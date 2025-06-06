#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api_server import app

if __name__ == "__main__":
    print("Starting Remote Developer API Server...")
    print("Web interface available at: http://localhost:15001")
    app.run(host="0.0.0.0", port=15001, debug=True)
