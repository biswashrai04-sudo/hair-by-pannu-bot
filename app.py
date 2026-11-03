"""
Hair by Pannu - WhatsApp Booking Bot
Production-grade Flask webhook server managing conversational appointment bookings,
session states, and persistence for mobile salon services in Abu Dhabi, UAE.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, request, Response
from twilio.twiml.messaging_response import MessagingResponse

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hair_by_pannu_bot")

DATABASE_PATH = os.getenv("DATABASE_PATH", "salon_bot.db")
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

SALON_SERVICES: Dict[str, Dict[str, Any]] = {
    "1": {"name": "Women's Haircut & Blowdry", "price_aed": 180, "duration": "45 mins"},
    "2": {"name": "Balayage & Full Color", "price_aed": 550, "duration": "180 mins"},
    "3": {"name": "Root Touch-Up & Gloss", "price_aed": 280, "duration": "90 mins"},
    "4": {"name": "Keratin Smoothing Treatment", "price_aed": 650, "duration": "150 mins"},
    "5": {"name": "Deep Conditioning Scalp Spa", "price_aed": 220, "duration": "60 mins"},
    "6": {"name": "Bridal & Event Hair Styling", "price_aed": 450, "duration": "90 mins"},
}

COVERAGE_AREAS: List[str] = [
    "Al Reem Island",
    "Saadiyat Island",
    "Yas Island",
    "Al Raha Beach",
    "Khalifa City",
    "Downtown Abu Dhabi",
    "Corniche",
    "Al Maryah Island",
    "Mohammed Bin Zayed City",
]

# State Machine steps
STATE_IDLE = "IDLE"
STATE_SELECT_SERVICE = "SELECT_SERVICE"
STATE_INPUT_DATE = "INPUT_DATE"
STATE_INPUT_TIME = "INPUT_TIME"
STATE_INPUT_NAME = "INPUT_NAME"
STATE_INPUT_ADDRESS = "INPUT_ADDRESS"
STATE_CONFIRM_BOOKING = "CONFIRM_BOOKING"


# ---------------------------------------------------------------------------
# Database Layer
# ---------------------------------------------------------------------------
def get_db_connection() -> sqlite3.Connection:
    """Creates a thread-safe connection to the SQLite database.

    Returns:
        sqlite3.Connection: Connection object configured with row factory.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes persistent tables for customer sessions and bookings."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                phone TEXT PRIMARY KEY,
                step TEXT NOT NULL,
                data TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_ref TEXT UNIQUE NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                service_name TEXT NOT NULL,
                price_aed REAL NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                location_address TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'CONFIRMED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    logger.info("Database schemas initialized successfully at %s", DATABASE_PATH)


def load_session(phone: str) -> Tuple[str, Dict[str, Any]]:
    """Loads current conversation step and state payload for a client.

    Args:
        phone: Sanitized phone number identifier.

    Returns:
        Tuple containing the current state step string and state payload dictionary.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT step, data FROM sessions WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        if row:
            try:
                data = json.loads(row["data"])
                return row["step"], data
            except json.JSONDecodeError:
                logger.warning("Corrupted session JSON for %s. Resetting session.", phone)
                return STATE_IDLE, {}
    return STATE_IDLE, {}


def save_session(phone: str, step: str, data: Dict[str, Any]) -> None:
    """Persists conversational state and payload for a phone number.

    Args:
        phone: Client phone number.
        step: Current state step string.
        data: Context dictionary to serialize.
    """
    data_json = json.dumps(data)
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (phone, step, data, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(phone) DO UPDATE SET
                step = excluded.step,
                data = excluded.data,
                updated_at = CURRENT_TIMESTAMP
            """,
            (phone, step, data_json),
        )
        conn.commit()


def clear_session(phone: str) -> None:
    """Resets conversational session back to the idle default state.

    Args:
        phone: Client phone number.
    """
    with get_db_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE phone = ?", (phone,))
        conn.commit()


def create_appointment(
    phone: str,
    name: str,
    service: str,
    price: float,
    date_val: str,
    time_val: str,
    address: str,
) -> str:
    """Records a confirmed appointment record into the database.

    Args:
        phone: WhatsApp mobile number.
        name: Client name.
        service: Title of selected treatment.
        price: Price in AED.
        date_val: Confirmed date string.
        time_val: Confirmed appointment time slot.
        address: Abu Dhabi home/villa address.

    Returns:
        Generated 8-character unique booking reference code.
    """
    booking_ref = f"HBP-{uuid.uuid4().hex[:6].upper()}"
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO appointments (
                booking_ref, customer_phone, customer_name, service_name,
                price_aed, appointment_date, appointment_time, location_address
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (booking_ref, phone, name, service, price, date_val, time_val, address),
        )
        conn.commit()
    logger.info("Created booking %s for %s (%s)", booking_ref, name, phone)
    return booking_ref


# ---------------------------------------------------------------------------
# Business Logic & Dialogue State Machine
# ---------------------------------------------------------------------------
def get_service_menu_text() -> str:
    """Constructs formatted menu string with service names, durations, and pricing."""
    lines = [
        "💇 *HAIR BY PANNU - MOBILE SALON (ABU DHABI)*",
        "_Luxury hair care delivered to your doorstep._\n",
        "*Select a service by replying with its number:*",
    ]
    for key, item in SALON_SERVICES.items():
        lines.append(f"*{key}*. {item['name']} - AED {item['price_aed']} ({item['duration']})")
    lines.append("\n_Reply *MENU* at any time to return here, or *CANCEL* to stop._")
    return "\n".join(lines)


def validate_date(date_text: str) -> Optional[str]:
    """Validates and normalizes date inputs (YYYY-MM-DD, DD/MM/YYYY, or 'tomorrow').

    Args:
        date_text: User input date string.

    Returns:
        Formatted 'YYYY-MM-DD' string if valid, else None.
    """
    cleaned = date_text.strip().lower()
    if cleaned in ("tomorrow", "tmrw"):
        from datetime import timedelta
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if cleaned in ("today",):
        return datetime.now().strftime("%Y-%m-%d")

    patterns = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"]
    for pattern in patterns:
        try:
            parsed = datetime.strptime(cleaned, pattern)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def handle_incoming_message(phone: str, user_input: str) -> str:
    """Core state engine processing WhatsApp client messages and routing responses.

    Args:
        phone: Sender WhatsApp identifier.
        user_input: Incoming raw message body.

    Returns:
        String text payload to send back to the user.
    """
    text = user_input.strip()
    cmd = text.lower()
    current_step, session_data = load_session(phone)

    # Global Commands
    if cmd in ("cancel", "reset", "stop"):
        clear_session(phone)
        return "❌ Your active booking session has been cancelled. Send *HI* whenever you'd like to book again!"

    if cmd in ("menu", "services", "help"):
        save_session(phone, STATE_SELECT_SERVICE, {})
        return get_service_menu_text()

    if cmd in ("coverage", "areas", "location"):
        areas_str = "\n".join([f"• {a}" for a in COVERAGE_AREAS])
        return (
            "📍 *Our Mobile Service Coverage in Abu Dhabi:*\n\n"
            f"{areas_str}\n\n"
            "We arrive fully equipped at your home or villa! Reply *BOOK* to reserve an appointment."
        )

    # State Dispatcher
    if current_step == STATE_IDLE:
        save_session(phone, STATE_SELECT_SERVICE, {})
        return (
            "✨ *Welcome to Hair by Pannu Mobile Salon Abu Dhabi!*\n\n"
            "Experience bespoke hair styling in the comfort of your private residence.\n\n"
            + get_service_menu_text()
        )

    elif current_step == STATE_SELECT_SERVICE:
        if text in SALON_SERVICES:
            selected = SALON_SERVICES[text]
            session_data["service_id"] = text
            session_data["service_name"] = selected["name"]
            session_data["price_aed"] = selected["price_aed"]
            save_session(phone, STATE_INPUT_DATE, session_data)
            return (
                f"✅ Selected: *{selected['name']}* (AED {selected['price_aed']})\n\n"
                "📅 What date would you like to schedule? "
                "(Reply with *YYYY-MM-DD*, *DD/MM/YYYY*, or *Tomorrow*)"
            )
        return (
            "⚠️ Invalid choice. Please reply with a valid service number (1-6):\n\n"
            + get_service_menu_text()
        )

    elif current_step == STATE_INPUT_DATE:
        norm_date = validate_date(text)
        if not norm_date:
            return (
                "⚠️ Date format not recognized. Please provide a valid date, e.g., "
                f"*{datetime.now().strftime('%Y-%m-%d')}*, *25/11/2026*, or *Tomorrow*."
            )
        session_data["appointment_date"] = norm_date
        save_session(phone, STATE_INPUT_TIME, session_data)
        return (
            f"📅 Date confirmed: *{norm_date}*\n\n"
            "⏰ What time works best for you? Choose from our daily slots:\n"
            "• *10:00 AM*\n"
            "• *01:00 PM*\n"
            "• *04:00 PM*\n"
            "• *07:00 PM*\n"
            "(Or type your preferred hour between 09:00 AM and 08:00 PM)"
        )

    elif current_step == STATE_INPUT_TIME:
        if len(text) < 3:
            return "⚠️ Please specify a valid time (e.g., *11:00 AM* or *04:00 PM*)."
        session_data["appointment_time"] = text
        save_session(phone, STATE_INPUT_NAME, session_data)
        return "👤 Great! What is your *full name* for the booking?"

    elif current_step == STATE_INPUT_NAME:
        if len(text) < 2:
            return "⚠️ Please enter a valid name."
        session_data["customer_name"] = text
        save_session(phone, STATE_INPUT_ADDRESS, session_data)
        return (
            f"Thank you, {text}!\n\n"
            "📍 Please share your *Abu Dhabi address or villa/apartment number* "
            "(e.g., *Villa 14, Al Reem Island, Shams Abu Dhabi*):"
        )

    elif current_step == STATE_INPUT_ADDRESS:
        if len(text) < 5:
            return "⚠️ Please provide a detailed address including your community/island."
        session_data["location_address"] = text
        save_session(phone, STATE_CONFIRM_BOOKING, session_data)
        return (
            "📋 *Please Review Your Booking Details:*\n"
            "────────────────────────────\n"
            f"• *Client Name:* {session_data.get('customer_name')}\n"
            f"• *Service:* {session_data.get('service_name')}\n"
            f"• *Price:* AED {session_data.get('price_aed')}\n"
            f"• *Date:* {session_data.get('appointment_date')}\n"
            f"• *Time:* {session_data.get('appointment_time')}\n"
            f"• *Location:* {session_data.get('location_address')}\n"
            "────────────────────────────\n"
            "Reply *YES* to confirm this booking, or *CANCEL* to discard."
        )

    elif current_step == STATE_CONFIRM_BOOKING:
        if cmd in ("yes", "y", "confirm"):
            booking_ref = create_appointment(
                phone=phone,
                name=session_data["customer_name"],
                service=session_data["service_name"],
                price=session_data["price_aed"],
                date_val=session_data["appointment_date"],
                time_val=session_data["appointment_time"],
                address=session_data["location_address"],
            )
            clear_session(phone)
            return (
                "🎉 *Booking Confirmed!*\n\n"
                f"Your booking reference is: *{booking_ref}*\n\n"
                "Our mobile stylist will arrive with all professional sanitation and styling equipment. "
                "For updates, inquiries, or reschedules, reply directly to this chat.\n\n"
                "Thank you for choosing *Hair by Pannu Abu Dhabi*! ✨"
            )
        elif cmd in ("no", "cancel"):
            clear_session(phone)
            return "❌ Booking cancelled. Type *HI* whenever you'd like to start over."
        else:
            return "⚠️ Please reply with *YES* to confirm your appointment, or *CANCEL* to abort."

    # Fallback reset
    clear_session(phone)
    return "Something went wrong. Let's start fresh!\n\n" + get_service_menu_text()


# ---------------------------------------------------------------------------
# Flask Application & Webhook Routing
# ---------------------------------------------------------------------------
app = Flask(__name__)
init_db()


@app.route("/health", methods=["GET"])
def health_check() -> Response:
    """Liveness probe returning application and database status."""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return jsonify({"status": "healthy", "database": "connected", "timestamp": datetime.utcnow().isoformat()}), 200
    except Exception as exc:
        logger.error("Health check failure: %s", str(exc))
        return jsonify({"status": "unhealthy", "error": str(exc)}), 500


@app.route("/webhook", methods=["POST"])
def whatsapp_webhook() -> Response:
    """WhatsApp incoming message handler.

    Accepts standard Twilio URL-encoded form submissions or raw JSON payloads,
    routes them to the conversational state machine, and replies via TwiML.
    """
    try:
        # Determine payload type
        if request.is_json:
            payload = request.get_json() or {}
            sender_raw = payload.get("From", payload.get("from", "unknown"))
            incoming_body = payload.get("Body", payload.get("text", payload.get("message", "")))
        else:
            sender_raw = request.values.get("From", "")
            incoming_body = request.values.get("Body", "")

        # Clean sender format (strip 'whatsapp:' prefix if present)
        sender_phone = sender_raw.replace("whatsapp:", "").strip()
        incoming_body = incoming_body.strip()

        if not sender_phone:
            logger.warning("Webhook received without a valid sender number.")
            return jsonify({"error": "Missing 'From' phone identifier"}), 400

        logger.info("Message received from %s: '%s'", sender_phone, incoming_body)
        bot_response_text = handle_incoming_message(sender_phone, incoming_body)

        # Build Twilio TwiML response
        twiml = MessagingResponse()
        twiml.message(bot_response_text)
        return Response(str(twiml), mimetype="application/xml")

    except Exception as exc:
        logger.exception("Unhandled error processing WhatsApp webhook: %s", str(exc))
        error_twiml = MessagingResponse()
        error_twiml.message("⚠️ An unexpected error occurred. Please try again or type *MENU*.")
        return Response(str(error_twiml), mimetype="application/xml"), 500


@app.route("/api/bookings", methods=["GET"])
def get_bookings() -> Response:
    """REST endpoint to fetch confirmed appointments for administrative views."""
    status_filter = request.args.get("status")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if status_filter:
            cursor.execute("SELECT * FROM appointments WHERE status = ? ORDER BY created_at DESC", (status_filter,))
        else:
            cursor.execute("SELECT * FROM appointments ORDER BY created_at DESC")
        rows = [dict(row) for row in cursor.fetchall()]
    return jsonify({"total": len(rows), "appointments": rows}), 200


if __name__ == "__main__":
    logger.info("Starting Hair by Pannu bot on %s:%d", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=False)