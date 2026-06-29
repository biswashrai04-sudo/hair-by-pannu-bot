from flask import Flask, request, jsonify
import datetime

app = Flask(__name__)
bookings = {}

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
