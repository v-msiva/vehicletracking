
import json, os
import paho.mqtt.client as mqtt
from datetime import datetime
import requests
import signal, sys
import pytz
def get_indian_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def signal_handler(sig, frame):
    print("\n🛑 Ctrl+C detected. Disconnecting MQTT client...")
    client.disconnect()
    client.loop_stop()
    print("✅ MQTT client disconnected. Exiting program.")
    sys.exit(0)
# Importing parser methods
from parser import split_data
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"⚠️ Unexpected disconnection (rc={rc}). Trying to reconnect...")
        try:
            client.reconnect()
        except Exception as e:
            print(f"❌ Reconnection failed: {e}")
# MQTT Configuration
MQTT_BROKER = "iot.mongrov.net"
MQTT_PORT = 1883
MQTT_TOPIC = "mongrov/#"
ODOO_URL = "https://esg.mongrov.net/jsonrpc"
ODOO_DB = "esg"
ODOO_USERNAME = "admin@mongrov.com"
ODOO_PASSWORD = "mi123"


def send_hex_to_odoo_jsonrpc(hex_data, parsed_data):
    try:
        # 1. Authenticate
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]
            },
            "id": 1,
        }

        response = requests.post(ODOO_URL, json=payload).json()
        uid = response.get("result")
        if not uid:
            print("❌ Login failed.")
            return

        # 2. Create record in Odoo
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "x_gps",
                    "create",
                    [{
                        "x_name": hex_data,
                        "x_json": parsed_data
                    }]
                ]
            },
        }

        response = requests.post(ODOO_URL, json=payload).json()
        record_id = response.get("result")
        if record_id:
            print(f"✔️ Data sent to Odoo - ID: {record_id}")
        else:
            print(f"❌ Failed to send data to Odoo: {response}")
    except Exception as e:
        print(f"[❌] JSON-RPC Error: {e}")


def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to topic: {MQTT_TOPIC}")


def safe_append_to_file(path, content, is_json=False):
    path=path+"\log"
    print(path)
    try:
        with open(path, "a") as f:
            if is_json:
                json.dump(content, f)
                f.write(f"{datetime.now().isoformat()} - {content}\n")
            else:
                f.write(f"{datetime.now().isoformat()} - {content}+\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[ERROR] Failed to write to {path}: {e}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload
        hex_data = payload.hex().upper()
        json_data = {
            "topic": msg.topic,
            "raw_data": hex_data,
            "length": len(payload),
        }

        # Parse using parser.py
        parsed_data = split_data(hex_data)

        # Save both raw and parsed data

        safe_append_to_file("raw_data.log", hex_data)
        if parsed_data:
            safe_append_to_file("parsed_data.json", parsed_data, is_json=True)

        send_hex_to_odoo_jsonrpc(hex_data, parsed_data)

        # Print paths
        print(f"Parsed JSON saved to: {os.path.abspath('parsed_data.json')}")
        print(f"Raw hex logs saved to: {os.path.abspath('raw_data.log')}")

        # Display parsed output
        if parsed_data:
            print("Parsed JSON Data at:", get_indian_time())
            print(json.dumps(parsed_data, indent=4))

        print("Received Metadata:\n", json.dumps(json_data, indent=4))

    except Exception as e:
        print(f"Error processing message: {e}")


# MQTT Client Setup
print("🚀 Transporter app started...")
signal.signal(signal.SIGINT, signal_handler)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
