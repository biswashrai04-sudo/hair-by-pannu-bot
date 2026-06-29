from flask import Flask, request, jsonify
import requests
import datetime

app = Flask(__name__)

# UltraMsg API
ULTRAMSG_TOKEN = "okrceou36xa6at6d"
ULTRAMSG_INSTANCE = "instance183035"
ADMIN_PHONE = "971543393207"  # No + sign

bookings = {}

def send_whatsapp(phone, message):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
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

@app.route("/")
def home():
    return "Hair by Pannu Bot is running!"

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
    
    # Send to customer
    customer_phone = data['phone'].replace("+", "")
    customer_msg = f"✅ Booking Confirmed!\n\nID: {booking_id}\nName: {data['name']}\nService: {data['service']}\nDate: {data['date']}\nTime: {data['time']}\n\nSee you at Hair by Pannu! 💈"
    customer_result = send_whatsapp(customer_phone, customer_msg)
    
    # Send to admin
    admin_msg = f"📋 New Booking\n\nID: {booking_id}\nName: {data['name']}\nPhone: {data['phone']}\nService: {data['service']}\nDate: {data['date']}\nTime: {data['time']}"
    admin_result = send_whatsapp(ADMIN_PHONE, admin_msg)
    
    return jsonify({
        "success": True,
        "booking_id": booking_id,
        "whatsapp_customer": customer_result,
        "whatsapp_admin": admin_result
    })

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
