from flask import Flask, request, jsonify
import requests
import urllib.parse
import datetime

app = Flask(__name__)

CALLMEBOT_APIKEY = "YOUR_API_KEY"
ADMIN_PHONE = "+233543393207"

bookings = {}

def send_whatsapp(phone, message):
    encoded = urllib.parse.quote(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded}&apikey={CALLMEBOT_APIKEY}"
    try:
        r = requests.get(url, timeout=30)
        return {"sent": "Message queued" in r.text or r.status_code == 200, "response": r.text}
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
    
    customer_result = send_whatsapp(data['phone'], f"✅ Booking Confirmed! ID: {booking_id}")
    admin_result = send_whatsapp(ADMIN_PHONE, f"📋 New Booking: {booking_id} - {data['name']}")
    
    return jsonify({
        "success": True,
        "booking_id": booking_id,
        "whatsapp_customer": customer_result,
        "whatsapp_admin": admin_result
    })

@app.route("/bookings", methods=['GET'])
def list_bookings():
    return jsonify(bookings)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
