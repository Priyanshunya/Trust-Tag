🛡️ Trust-Tag: Hardware-Secured Logistics Integrity System

Theme: Sustainable Development / Smart Logistics

Team: Vision Synapse

⚡ The Concept

Trust-Tag is a universal security system that transforms standard packaging into an active sensor. Unlike passive "VOID" tapes, we use Analog Signature Fingerprinting to detect tampering in real-time.


System Logic: Cut/Tamper $\rightarrow$ Analog Variation $\rightarrow$ ESP32 Trigger $\rightarrow$ Cloud Alert.

🏗️ System Architecture

The system operates on a "Zero-Trust" architecture:

Edge Layer: ESP32 captures the chaotic resistance signature of the seal (PUF).

Ingestion: Data streams via Secure Serial/MQTT to the Cloud.

Validation: Cloud Logic compares the live signature against the "Origin Signature" stored in Firestore.

Intelligence: Vertex AI filters out noise (temperature drift) from active tampering.


🛠️ Tech Stack

Firmware: C++ (Arduino Framework)

Backend: Python (Flask / Google Cloud Functions)

Database: Firebase Firestore (NoSQL)


🚀 How to Run (Local Demo Mode)

Hardware: Connect the Voltage Divider circuit as per the Pinout table.

Flash: Upload firmware/scanner.ino to ESP32.

Run Server
