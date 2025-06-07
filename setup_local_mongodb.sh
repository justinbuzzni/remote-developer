#!/bin/bash
# Setup script for local MongoDB

echo "Setting up local MongoDB for Remote Developer..."

# Check if MongoDB is running
if ! nc -z localhost 27018 2>/dev/null; then
    echo "MongoDB is not running on port 27018"
    echo "Please start MongoDB first"
    exit 1
fi

echo "MongoDB is running on port 27018"

# Create database and user
cat << 'EOF' | mongosh --port 27018
use remote_developer

// Create user with proper permissions
db.createUser({
  user: "hsmoa-mongodb",
  pwd: "buzzni2012!",
  roles: [
    { role: "readWrite", db: "remote_developer" },
    { role: "dbAdmin", db: "remote_developer" }
  ]
})

// Create collections
db.createCollection("tasks")
db.createCollection("task_logs")

print("Database and user created successfully!")
EOF

echo "Setup complete!"
echo ""
echo "To test the connection, run:"
echo "python test_mongodb_connection.py"