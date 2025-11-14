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

# Check for .env file and offer to create
echo ""
echo "🔑 Checking environment configuration..."

if [ ! -f ".env" ]; then
    echo "❌ .env file not found"
    echo ""
    echo "The CLI requires a .env file with your Azure OpenAI credentials."
    echo ""
    read -p "Would you like to create a .env file now? (y/n) " -n 1 -r
    echo ""
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Check if .env.example exists
        if [ -f ".env.example" ]; then
            echo "Creating .env from .env.example..."
            cp .env.example .env
            echo "✓ .env file created"
        else
            # Create from template
            echo "Creating .env from template..."
            cat > .env << 'EOF'
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Optional: Database configuration for data team
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Optional: Memory settings
# MEMORY_MAX_ENTRIES=100
EOF
            echo "✓ .env file created from template"
        fi

        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your real Azure OpenAI credentials!"
        echo ""
        echo "Required values:"
        echo "  - AZURE_OPENAI_API_KEY (from Azure Portal)"
        echo "  - AZURE_OPENAI_ENDPOINT (e.g., https://your-resource.openai.azure.com/)"
        echo "  - AZURE_OPENAI_DEPLOYMENT_NAME (e.g., gpt-4, gpt-35-turbo)"
        echo ""
        echo "To edit: nano .env  (or use your preferred editor)"
        echo ""
        read -p "Press Enter after you've edited .env with your credentials..."
        echo ""
    else
        echo ""
        echo "⚠️  Skipping .env creation."
        echo "   You'll need to create it manually before running the CLI."
        echo ""
    fi
else
    echo "✓ .env file found"

    # Verify .env doesn't have placeholder values
    if grep -q "your_api_key_here\|your_key_here\|your_endpoint_here\|your_deployment_name" .env 2>/dev/null; then
        echo ""
        echo "⚠️  WARNING: .env contains placeholder values!"
        echo ""
        echo "Your .env file still has placeholder text like 'your_api_key_here'."
        echo "The CLI will not work until you add real Azure OpenAI credentials."
        echo ""
        echo "To edit: nano .env  (or use your preferred editor)"
        echo ""
        read -p "Would you like to edit .env now? (y/n) " -n 1 -r
        echo ""
        echo ""

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Try to open with available editor
            if command -v nano &> /dev/null; then
                nano .env
            elif command -v vim &> /dev/null; then
                vim .env
            elif command -v vi &> /dev/null; then
                vi .env
            else
                echo "No text editor found. Please edit .env manually."
            fi
        fi
    else
        echo "✓ .env appears to be configured"
    fi
fi

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
echo "📖 Quick Start:"
echo ""
echo "   ./cli.py                    # Simple assistant"
echo "   ./cli.py --team weather     # Weather team example"
echo "   ./cli.py --team magentic    # Web research team"
echo "   ./cli.py --team data        # Data analysis team"
echo "   ./cli.py -r                 # Resume with memory"
echo ""
echo "   Run './cli.py --help' to see all available options!"
echo ""
echo "💡 Tip: Use -r/--resume to enable persistent memory across sessions"
echo ""
