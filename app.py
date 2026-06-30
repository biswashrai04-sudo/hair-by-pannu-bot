from flask import Flask, request, jsonify
import requests
import datetime
import os

app = Flask(__name__)

ULTRAMSG_TOKEN = os.environ.get("ULTRAMSG_TOKEN", "")
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE", "")
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "")
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
        
        system_prompt = """You are Pannu's AI Assistant for "Hair by Pannu" — a premium mobile salon service in Abu Dhabi. Warm, casual, professional tone. No emojis. Short responses (1-2 sentences max).

FLOW:
1. Greeting: "Hi! Thank you for contacting Hair by Pannu. I am her digital assistant. What is your name please?"
2. After name: "Thank you for reaching out, [Name]. How can I help you today?"
   Then show options:
   A) Services & Prices
   B) Book an Appointment
3. If A: Show relevant price list briefly
   If B: Start booking flow

BLOW DRY:
- Blow Dry (Straight): 100-180 AED | 30-45 min
- Blow Dry (Wavy): 100-180 AED | 30-50 min
- Blow Dry (Curly): 120-180 AED | 45-50 min
- Blow Dry with Volume & Curls: 150-200 AED | 60-90 min

SIGNATURE HAIRCUTS:
- Desire Haircut + Bangs + Face Framing + Proper Hair Styling: 200-300 AED | 90-120 min
- Desire Haircut (No Hairwash) + Proper Blow Dry: 150-200 AED | 60-90 min
- Trim (Straight/U Shape) + Normal Blow Dry: 80-150 AED | 45-60 min
- Bangs (Any Type): 60 AED | 20 min

STYLING SERVICES:
- Blow Dry + Ironing (Sleek Straight): 120-150 AED | 50-70 min
- Blow Dry + Beach Waves Style: 130-160 AED | 50-60 min
- Blow Dry + Curling (Tight Curls): 130-160 AED | 50-60 min
- Blow Dry + Ironing (Wavy/Volume/Smooth): 150-200 AED | 60-90 min

SCALP CARE & THERAPY:
- Wellaplex Bond Treatment: 180-360 AED | 90-120 min
- Hair Spa: 150-250 AED | 90-120 min
- Oil Treatment (Head-Neck-Shoulder-Hands Massage): 150-200 AED | 90-120 min
- Head Oil Treatment + 15-min Massage: 70-150 AED | 60-90 min

SMOOTH TEXTURE & FIBRE REPAIR:
- Premium Protein Infusion: 600-1,200 AED | 60-90 min
- Advanced Keratin Smoothing: 700-1,400 AED | 60-90 min
- Premium Hair Botox: 350-600 AED | 60-90 min

HAIR COLORING ARTISTRY:
- Root Touch Up: 200-300 AED | 60-90 min
- Full Hair Coloring: 350-600 AED | 60-90 min

Note: Final pricing varies by hair length, density, and structural history. Exact quotes given upon personal consultation.

BOOKING FLOW (one question at a time):
1. "What service are we looking to book today? (You can reply with just a keyword, like Blow Dry, Haircut, or Color)."
2. "Great. What date or day works best for you?"
3. "Perfect. Do you prefer morning, afternoon, evening, or a specific time (AM/PM)?"
4. "Got it. This is a premium mobile service—what is your estimated area or location in Abu Dhabi?"

AFTER ALL DETAILS:
"Thank you! Pannu will check her schedule right now and we will get back to you quickly to confirm your slot.

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
- Keep it casual and warm
- Always mention prices are estimates and final quote depends on hair assessment"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
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
    
    payload = request.get_json(silent=True) or {}
    print(f"Full payload: {payload}")
    
    message_data = payload.get('data', {})
    print(f"Message data: {message_data}")
    
    phone = message_data.get('from', '').replace("@c.us", "")
    text = message_data.get('body', '').strip()
    pushname = message_data.get('pushname', '')
    
    print(f"Extracted - From: {phone}, Body: {text}, Name: {pushname}")
    
    if not phone or not text:
        print("Empty phone or text — skipping")
        return "OK", 200
    
    reply = ai_response(text, phone)
    print(f"AI Reply: {reply[:100]}")
    
    result = send_whatsapp(phone, reply)
    print(f"WhatsApp result: {result}")
    
    if "Here is your summary:" in reply:
        send_whatsapp(ADMIN_PHONE, f"New booking from {phone} ({pushname}):\n\n{reply}")
    
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
    customer_msg = f"Thank you! Pannu will check her schedule right now and we will get back to you quickly to confirm your slot.\n\n*Name:* {data['name']}\n*Service:* {data['service']}\n*Date:* {data['date']}\n*Time:* {data['time']}\n\nThank you for choosing Hair by Pannu. Have a nice time."
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
