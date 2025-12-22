#!/usr/bin/env python3
"""
Razorpay Integration Test Script
Tests if Razorpay credentials are configured correctly
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import razorpay

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'aspy_backend', '.env'))

def test_razorpay_connection():
    """Test Razorpay API connection"""
    
    print("=" * 50)
    print("Testing Razorpay Integration")
    print("=" * 50)
    print()
    
    # Get credentials from environment
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    
    if not key_id or not key_secret:
        print("❌ ERROR: Razorpay credentials not found in .env")
        print("\nPlease run: ./configure_razorpay.sh")
        return False
    
    print(f"✅ RAZORPAY_KEY_ID: {key_id}")
    print(f"✅ RAZORPAY_KEY_SECRET: {key_secret[:10]}...")
    print()
    
    # Initialize Razorpay client
    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        print("✅ Razorpay client initialized successfully")
        print()
        
        # Test creating a dummy order
        print("Testing order creation...")
        order_data = {
            'amount': 50000,  # Amount in paise (₹500)
            'currency': 'INR',
            'receipt': 'test_receipt_001',
            'notes': {
                'test': 'true',
                'purpose': 'integration_test'
            }
        }
        
        order = client.order.create(data=order_data)
        
        print("✅ Test order created successfully!")
        print(f"\n   Order ID: {order['id']}")
        print(f"   Amount: ₹{order['amount'] / 100:.2f}")
        print(f"   Currency: {order['currency']}")
        print(f"   Status: {order['status']}")
        print()
        
        # Test fetching the order
        print("Testing order fetch...")
        fetched_order = client.order.fetch(order['id'])
        print(f"✅ Order fetched successfully! Status: {fetched_order['status']}")
        print()
        
        print("=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("=" * 50)
        print()
        print("Your Razorpay integration is configured correctly!")
        print("You can now accept payments in your application.")
        print()
        print("Test Cards for Development:")
        print("  Card: 4111 1111 1111 1111")
        print("  CVV: Any 3 digits")
        print("  Expiry: Any future date")
        print()
        
        return True
        
    except razorpay.errors.BadRequestError as e:
        print(f"❌ Bad Request Error: {e}")
        print("\nThis usually means invalid API credentials.")
        print("Please check your Razorpay keys.")
        return False
        
    except razorpay.errors.ServerError as e:
        print(f"❌ Server Error: {e}")
        print("\nRazorpay servers might be experiencing issues.")
        print("Please try again later.")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("\nPlease check your configuration and try again.")
        return False

if __name__ == "__main__":
    success = test_razorpay_connection()
    sys.exit(0 if success else 1)
