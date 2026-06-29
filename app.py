from flask import Flask, request, jsonify
import requests
import datetime
import threading
import time

app = Flask(__name__)

ULTRAMSG_TOKEN = "okrceou36xa6at6d"
ULTRAMSG_INSTANCE = "instance183035"
ADMIN_PHONE = "971543393207"

bookings = {}
sessions = {}  # Track user sessions

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

def welcome_message(phone):
    """Send welcome message"""
    msg = (
        "👋 *Hello! Welcome to Hair by Pannu!*\n\n"
        "How are you today? 😊\n\n"
        "How can I help you?\n\n"
        "💈 *Our Services:*\n"
        "• Haircut\n"
        "• Hair Coloring\n"
        "• Hair Treatment\n"
        "• Styling\n\n"
        "📅 *To book, just tell me:*\n"
        "• Your name\n"
        "• Service you want\n"
        "• Preferred date & time\n\n"
        "Example: _Hi, I'm John. I want a haircut on July 5th at 2pm_"
    )
    send_whatsapp(phone, msg)

@app.route("/webhook", methods=['POST'])
def webhook():
    """Receive incoming WhatsApp messages"""
    data = request.form
    
    # UltraMsg sends these fields
    phone = data.get('from', '').replace("@c.us", "")
    text = data.get('body', '').strip()
    
    if not phone or not text:
        return "OK", 200
    
    # New user or any message → send welcome
    if phone not in sessions:
        sessions[phone] = {'step': 'welcome'}
        welcome_message(phone)
        return "OK", 200
    
    # Existing user sent another message
    if sessions[phone]['step'] == 'welcome':
        # Try to parse as booking
        # For now, just welcome again
        welcome_message(phone)
    
    return "OK", 200

@app.route("/")
def home():
    return "Hair by Pannu Bot is running!"

@app.route("/welcome", methods=['POST'])
def manual_welcome():
    """Manually send welcome"""
    data = request.json
    phone = data['phone'].replace("+", "")
    welcome_message(phone)
    return jsonify({"success": True})

@app.route("/book", methods=['POST'])
def book():
    """Structured booking from Flutter"""
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
    customer_msg = f"✅ *Booking Confirmed!*\n\nID: {booking_id}\nName: {data['name']}\nService: {data['service']}\nDate: {data['date']}\nTime: {data['time']}\n\nSee you at Hair by Pannu! 💈"
    send_whatsapp(customer_phone, customer_msg)
    
    admin_msg = f"📋 *New Booking*\n\nID: {booking_id}\nName: {data['name']}\nPhone: {data['phone']}\nService: {data['service']}\nDate: {data['date']}\nTime: {data['time']}"
    send_whatsapp(ADMIN_PHONE, admin_msg)
    
    return jsonify({"success": True, "booking_id": booking_id})

@app.route("/bookings", methods=['GET'])
def list_bookings():
    return jsonify(bookings)

@app.route("/admin")
def admin():
    html = "<h1>📋 Hair by Pannu - Bookings</h1>"
    for id, b in bookings.items():
        html += f"<p><b>{id}</b>: {b['name']} | {b['service']} | {b['date']} {b['time']} | {b['phone']}</p>"
    return html

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
