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
        return {"sent": "Message queued" in r.text or r.status_code == 200}
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
    send_whatsapp(data['phone'], f"✅ *Booking Confirmed*\n\nID: {booking_id}\nName: {data['name']}\nService: {data['service']}\nDate: {data['date']}\nTime: {data['time']}\n\nSee you at Hair by Pannu! 💈")
    send_whatsapp(ADMIN_PHONE, f"📋 *New Booking*\n\nID: {booking_id}\nName: {data['name']}\nPhone: {data['phone']}\nService: {data['service']}\nDate: {data['date']}\nTime: {data['time']}")
    return jsonify({"success": True, "booking_id": booking_id})

@app.route("/cancel/<booking_id>", methods=['POST'])
def cancel(booking_id):
    if booking_id not in bookings:
        return jsonify({"success": False, "error": "Not found"})
    booking = bookings[booking_id]
    booking['status'] = "cancelled"
    send_whatsapp(booking['phone'], f"❌ Booking {booking_id} cancelled.")
    send_whatsapp(ADMIN_PHONE, f"❌ Booking {booking_id} cancelled by {booking['name']}")
    return jsonify({"success": True})

@app.route("/bookings", methods=['GET'])
def list_bookings():
    return jsonify(bookings)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
