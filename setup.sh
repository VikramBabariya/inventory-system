#!/bin/bash
echo "🚀 Starting Project Setup..."

# Check for Node
if ! command -v node &> /dev/null
then
    echo "❌ Node not found. Please install NVM first."
    exit
else
    echo "✅ Node version $(node -v) detected."
fi

# Check for Docker
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit
else
    echo "✅ Docker is running."
fi

echo "📦 Installing Project Dependencies..."
npm install

echo "🎉 Setup Complete! Run 'npm start' to begin."