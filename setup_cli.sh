#!/bin/bash
# Setup script for AutoGen CLI Agent

echo "🤖 Setting up AutoGen CLI Agent..."
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi

echo "✓ pip3 found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✓ Dependencies installed"

# Make CLI executable
echo ""
echo "🔧 Making CLI executable..."
chmod +x cli.py

echo "✓ CLI is now executable"

# Create symlink or alias suggestion
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To use the CLI, you can:"
echo ""
echo "1. Run directly:"
echo "   ./cli.py"
echo ""
echo "2. Run with python:"
echo "   python3 cli.py"
echo ""
echo "3. Create an alias (add to ~/.bashrc or ~/.zshrc):"
echo "   alias autogen-cli='python3 $(pwd)/cli.py'"
echo ""
echo "4. Create a symlink (requires sudo):"
echo "   sudo ln -s $(pwd)/cli.py /usr/local/bin/autogen-cli"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  Don't forget to set up your .env file with:"
echo "   AZURE_OPENAI_API_KEY=your_key_here"
echo "   AZURE_OPENAI_ENDPOINT=your_endpoint_here"
echo "   AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name"
echo ""
echo "Run './cli.py --help' to see all available options!"
echo ""
