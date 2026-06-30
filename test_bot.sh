#!/bin/bash

echo "=========================================="
echo "  HAIR BY PANNU BOT - FULL TEST SUITE"
echo "=========================================="
echo ""

# Test 1: Bot is running
echo "TEST 1: Checking if bot is running..."
response=$(curl -s https://pannu-bot.onrender.com/)
if [ "$response" = "Hair by Pannu Bot is running!" ]; then
    echo "✅ PASS: Bot is running"
else
    echo "❌ FAIL: Bot not responding"
    echo "Response: $response"
fi
echo ""

# Test 2: AI Webhook - simulate customer saying "Hi"
echo "TEST 2: Testing AI webhook (customer says 'Hi')..."
webhook_response=$(curl -s -X POST https://pannu-bot.onrender.com/webhook \
  -d "from=971501234567@c.us" \
  -d "body=Hi")
if [ "$webhook_response" = "OK" ]; then
    echo "✅ PASS: Webhook accepted"
    echo "📱 Check WhatsApp for AI welcome message"
else
    echo "❌ FAIL: Webhook error"
    echo "Response: $webhook_response"
fi
echo ""

# Test 3: Structured booking
echo "TEST 3: Testing structured booking..."
booking_response=$(curl -s -X POST https://pannu-bot.onrender.com/book \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Customer","phone":"971543393207","service":"Haircut","date":"2026-07-05","time":"14:00"}')

if echo "$booking_response" | grep -q '"success":true'; then
    echo "✅ PASS: Booking created"
    echo "Response: $booking_response"
else
    echo "❌ FAIL: Booking failed"
    echo "Response: $booking_response"
fi
echo ""

# Test 4: View bookings
echo "TEST 4: Checking bookings list..."
bookings=$(curl -s https://pannu-bot.onrender.com/bookings)
if [ "$bookings" != "{}" ]; then
    echo "✅ PASS: Bookings found"
    echo "Bookings: $bookings"
else
    echo "⚠️  Bookings empty (may be normal if no bookings yet)"
fi
echo ""

# Test 5: Admin dashboard
echo "TEST 5: Checking admin dashboard..."
admin_html=$(curl -s https://pannu-bot.onrender.com/admin | head -c 100)
if echo "$admin_html" | grep -q "Hair by Pannu"; then
    echo "✅ PASS: Admin dashboard accessible"
else
    echo "❌ FAIL: Admin dashboard error"
fi
echo ""

echo "=========================================="
echo "  TEST COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check WhatsApp on +971543393207 for messages"
echo "2. Visit: https://pannu-bot.onrender.com/admin"
echo "3. If no WhatsApp messages, check Render logs:"
echo "   dashboard.render.com → pannu-bot → Logs"
