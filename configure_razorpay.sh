#!/bin/bash
# Razorpay Configuration Script
# This script helps you configure Razorpay credentials

echo "=================================="
echo "DesiCodes Razorpay Configuration"
echo "=================================="
echo ""

# Define the .env file path
ENV_FILE="./aspy_backend/.env"

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env file not found at $ENV_FILE"
    echo "Creating .env file from .env.example..."
    
    if [ -f "./aspy_backend/.env.example" ]; then
        cp "./aspy_backend/.env.example" "$ENV_FILE"
        echo "✅ Created .env file"
    else
        echo "❌ .env.example not found. Please create .env manually."
        exit 1
    fi
fi

echo "📝 Adding Razorpay credentials to .env..."
echo ""

# Razorpay credentials
RAZORPAY_KEY_ID="rzp_test_RuiDxfncHIKALF"
RAZORPAY_KEY_SECRET="ntmlLyUQFK4fFxN121iEEM5r"

# Check if keys already exist
if grep -q "RAZORPAY_KEY_ID" "$ENV_FILE"; then
    echo "⚠️  RAZORPAY_KEY_ID already exists in .env"
    echo "Updating existing value..."
    
    # Update existing values (macOS compatible)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^RAZORPAY_KEY_ID=.*/RAZORPAY_KEY_ID=$RAZORPAY_KEY_ID/" "$ENV_FILE"
        sed -i '' "s/^RAZORPAY_KEY_SECRET=.*/RAZORPAY_KEY_SECRET=$RAZORPAY_KEY_SECRET/" "$ENV_FILE"
    else
        sed -i "s/^RAZORPAY_KEY_ID=.*/RAZORPAY_KEY_ID=$RAZORPAY_KEY_ID/" "$ENV_FILE"
        sed -i "s/^RAZORPAY_KEY_SECRET=.*/RAZORPAY_KEY_SECRET=$RAZORPAY_KEY_SECRET/" "$ENV_FILE"
    fi
else
    echo "Adding new Razorpay configuration..."
    echo "" >> "$ENV_FILE"
    echo "# Razorpay Payment Gateway Configuration" >> "$ENV_FILE"
    echo "RAZORPAY_KEY_ID=$RAZORPAY_KEY_ID" >> "$ENV_FILE"
    echo "RAZORPAY_KEY_SECRET=$RAZORPAY_KEY_SECRET" >> "$ENV_FILE"
fi

echo ""
echo "✅ Razorpay credentials added successfully!"
echo ""
echo "Configuration:"
echo "  RAZORPAY_KEY_ID: $RAZORPAY_KEY_ID"
echo "  RAZORPAY_KEY_SECRET: ${RAZORPAY_KEY_SECRET:0:10}..."
echo ""
echo "⚠️  IMPORTANT: These are TEST credentials"
echo "   For production, replace with LIVE keys from Razorpay Dashboard"
echo ""
echo "Next Steps:"
echo "1. Restart your backend server"
echo "2. Test payment flow with test cards"
echo "3. Check RAZORPAY_SETUP.md for testing guide"
echo ""
echo "=================================="
