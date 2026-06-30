from flask import Flask, request, jsonify
import requests
import datetime
import os

app = Flask(__name__)

ULTRAMSG_TOKEN = "okrceou36xa6at6d"
ULTRAMSG_INSTANCE = "instance183035"
ADMIN_PHONE = "971543393207"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

bookings = {}
sessions = {}

def send_whatsapp(phone, message):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    data = {
        "token": ULTRAMSG_TOKEN,
        "to": phone,
        "body": message,
        "priority": "1"
    }
    try:
        r = requests.post(url, data=data, timeout=30)
        return {"sent": r.status_code == 200, "response": r.text[:100]}
    except Exception as e:
        return {"sent": False, "error": str(e)}

def ai_response(customer_message, phone):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pannu-bot.onrender.com",
            "X-Title": "Hair by Pannu Bot"
        }
        
        history = sessions.get(phone, [])
        
        messages = [
            {
                "role": "system",
                "content": """You are Pannu's AI Assistant for "Hair by Pannu". Warm, casual, professional tone. No emojis. Short responses (1-2 sentences max).

FLOW:
1. Greeting: "Hi! Thank you for contacting Hair by Pannu. I am her digital assistant. What is your name please?"
2. After name: "Thank you for reaching out, [Name]. How can I help you today?"
   Then show options:
   A) Services & Prices
   B) Book an Appointment
3. If A: Show price list briefly
   If B: Start booking flow

PRICE LIST:
- Haircut: 50 AED
- Blow Dry: 80 AED  
- Color: 150 AED
- Treatment: 100 AED
- Styling: 80 AED
*Note: Final pricing varies by hair length and density.*

BOOKING FLOW (one question at a time):
1. "What service are we looking to book today? (You can reply with just a keyword, like Blow Dry, Haircut, or Color)."
2. "Great. What date or day works best for you?"
3. "Perfect. Do you prefer morning, afternoon, evening, or a specific time (AM/PM)?"
4. "Got it. This is a premium mobile service—what is your estimated area or location in Abu Dhabi?"

AFTER ALL DETAILS:
"Thank you! Silent will check Pannu's schedule right now and we will get back to you quickly to confirm your slot.

Here is your summary:
*Name:* [Client Name]
*Service:* [Full Service Name]
*Date:* [Date]
*Time:* [Time/Window]
*Location:* [Location]

Thank you for choosing Hair by Pannu. Have a nice time."

CONSTRAINTS:
- No emojis
- Never ask two questions at once
- Use asterisks (*) for bold text
- Keep it casual and warm"""
            }
        ]
        
        for msg in history:
            messages.append(msg)
        
        messages.append({"role": "user", "content": customer_message})
        
        data = {
            "model": "openai/gpt-4o-mini",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 300
        }
        
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        result = r.json()
        reply = result['choices'][0]['message']['content']
        
        if phone not in sessions:
            sessions[phone] = []
        sessions[phone].append({"role": "user", "content": customer_message})
        sessions[phone].append({"role": "assistant", "content": reply})
        sessions[phone] = sessions[phone][-12:]
        
        return reply
        
    except Exception as e:
        print(f"AI Error: {e}")
        return "Hi! Thank you for contacting Hair by Pannu. I am her digital assistant. What is your name please?"

@app.route("/webhook", methods=['POST'])
def webhook():
    print("=== WEBHOOK HIT ===")
    print(f"Headers: {dict(request.headers)}")
    print(f"Form: {dict(request.form)}")
    print(f"JSON: {request.get_json(silent=True)}")
    print(f"Data: {request.get_data(as_text=True)}")
    
    # Try to get data from multiple sources
    data = request.form
    if not data:
        json_data = request.get_json(silent=True)
        if json_data:
            data = json_data
    
    phone = data.get('from', '').replace("@c.us", "") if hasattr(data, 'get') else ''
    text = data.get('body', '').strip() if hasattr(data, 'get') else ''
    
    print(f"From: {phone}, Body: {text}")
    
    if not phone or not text:
        print("Empty phone or text")
        return "OK", 200
    
    reply = ai_response(text, phone)
    print(f"AI Reply: {reply[:100]}")
    
    result = send_whatsapp(phone, reply)
    print(f"WhatsApp result: {result}")
    
    if "Here is your summary:" in reply:
        send_whatsapp(ADMIN_PHONE, f"New booking from {phone}:\n\n{reply}")
    
    return "OK", 200

@app.route("/")
def home():
    return "Hair by Pannu AI Bot is running!"

@app.route("/book", methods=['POST'])
def book():
    data = request.json
    booking_id = f"BP{datetime.datetime.now().strftime('%H%M%S')}"
    
    bookings[booking_id] = {
        "name": data['name'],
        "phone": data['phone'],
        "service": data['service'],
        "date": data['date'],
        "time": data['time'],
        "status": "confirmed"
    }
    
    customer_phone = data['phone'].replace("+", "")
    customer_msg = f"Thank you! Silent will check Pannu's schedule right now and we will get back to you quickly to confirm your slot.\n\n*Name:* {data['name']}\n*Service:* {data['service']}\n*Date:* {data['date']}\n*Time:* {data['time']}\n\nThank you for choosing Hair by Pannu. Have a nice time."
    send_whatsapp(customer_phone, customer_msg)
    
    admin_msg = f"New Booking: {booking_id}\nName: {data['name']}\nPhone: {data['phone']}\nService: {data['service']}\nDate: {data['date']}\nTime: {data['time']}"
    send_whatsapp(ADMIN_PHONE, admin_msg)
    
    return jsonify({"success": True, "booking_id": booking_id})

@app.route("/bookings", methods=['GET'])
def list_bookings():
    return jsonify(bookings)

@app.route("/admin")
def admin():
    html = "<h1>Hair by Pannu - Bookings</h1>"
    for id, b in bookings.items():
        html += f"<p><b>{id}</b>: {b['name']} | {b['service']} | {b['date']} {b['time']} | {b['phone']}</p>"
    return html

@app.route("/debug")
def debug():
    key_set = "YES" if OPENROUTER_API_KEY else "NO"
    key_preview = OPENROUTER_API_KEY[:10] + "..." if OPENROUTER_API_KEY else "EMPTY"
    return jsonify({
        "openrouter_key_set": key_set,
        "key_preview": key_preview,
        "admin_phone": ADMIN_PHONE,
        "ultramsg_instance": ULTRAMSG_INSTANCE
    })

@app.route("/test-ai")
def test_ai():
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pannu-bot.onrender.com",
            "X-Title": "Hair by Pannu Bot"
        }
        
        data = {
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hi"}],
            "temperature": 0.7,
            "max_tokens": 50
        }
        
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        return jsonify({
            "status": r.status_code,
            "response": r.json()['choices'][0]['message']['content'] if r.status_code == 200 else r.text
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/test-webhook")
def test_webhook():
    phone = "971501234567"
    text = "Hi"
    
    reply = ai_response(text, phone)
    result = send_whatsapp(phone, reply)
    
    return jsonify({
        "ai_reply": reply,
        "whatsapp_result": result
    })

@app.route("/ping")
def ping():
    return jsonify({
        "status": "alive",
        "time": str(datetime.datetime.now()),
        "webhook_url": "https://pannu-bot.onrender.com/webhook"
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
