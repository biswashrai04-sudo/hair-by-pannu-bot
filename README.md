# 💇 Hair by Pannu - WhatsApp Booking Bot

> An automated, production-grade conversational booking system powering door-to-door salon appointments across Abu Dhabi, UAE.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-black.svg)](https://palletsprojects.com/p/flask/)
[![Twilio](https://img.shields.io/badge/Twilio-WhatsApp%20API-red.svg)](https://www.twilio.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 Overview

**Hair by Pannu Bot** is a complete conversational WhatsApp bot designed specifically for a premium mobile hair styling business in Abu Dhabi. It orchestrates a friction-free customer journey: presenting real-time service catalogs, booking appointments with custom scheduling, capturing location data (villas/islands), and persisting confirmed appointments to an indexed relational database.

---

## 🏛️ System Architecture

```mermaid
sequenceDiagram
    autonumber
    actor Client as Customer (WhatsApp)
    participant Twilio as Twilio WhatsApp Gateway
    participant Webhook as Flask Webhook (/webhook)
    participant State as State Machine Engine
    participant DB as SQLite (salon_bot.db)

    Client->>Twilio: Sends "Hi" or "Book"
    Twilio->>Webhook: POST application/x-www-form-urlencoded
    Webhook->>State: Evaluate input & load session
    State->>DB: Query active user state
    DB-->>State: Current step (e.g. SELECT_SERVICE)
    State->>State: Advance state machine & build reply
    State->>DB: Upsert session state / write booking
    State-->>Webhook: Return WhatsApp formatted message
    Webhook-->>Twilio: 200 OK (TwiML XML response)
    Twilio-->>Client: Delivers formatted WhatsApp message