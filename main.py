
import json, os
import paho.mqtt.client as mqtt
from datetime import datetime
import requests

# MQTT Configuration
MQTT_BROKER = "iot.mongrov.net"
MQTT_PORT = 1883
MQTT_TOPIC = "mongrov/#"
ODOO_URL = "https://esg.mongrov.net/jsonrpc"
ODOO_DB = "esg"
ODOO_USERNAME = "admin@mongrov.com"
ODOO_PASSWORD = "mi123"


def send_hex_to_odoo_jsonrpc(hex_data,parsed_data):
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

        # 2. Create record in atest
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
            print(f"✔️ Data sent to Odoo via JSON-RPC - record ID: {record_id}")
        else:
            print(f"❌ Failed to send data to Odoo: {response}")
    except Exception as e:
        print(f"[❌] JSON-RPC Error: {e}")
def bcd_to_string(bcd):
    return ''.join(f"{(b >> 4) & 0xF}{b & 0xF}" for b in bcd)
def parse_hex_data(hex_data):
    try:
        # Convert to uppercase for consistency
        hex_data = hex_data.lower()
        time_bcd = bytes.fromhex(hex_data[70:82])[:6]  # Only 6 bytes (YYMMDDhhmmss)
        time_str = bcd_to_string(time_bcd)
        formatted_time = datetime.strptime(time_str, "%y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "flag": hex_data[0:2],
            "message_id": hex_data[2:6],                # WORD = 2 bytes = 4 hex
            "body_parameters_property": hex_data[6:10],          # WORD = 4 hex
            "device_id": hex_data[10:22],               # BCD[6] = 6 bytes = 12 hex
            "message_sequence": hex_data[22:26],        # WORD = 4 hex
            "alarm": hex_data[26:34],                   # DWORD = 8 hex
            "status": hex_data[34:42],                  # DWORD = 8 hex
            "latitude": int(hex_data[42:50], 16) / 1000000,   # DWORD = 8 hex
            "longitude": int(hex_data[50:58], 16) / 1000000,  # DWORD = 8 hex
            "altitude": int(hex_data[58:62], 16),       # WORD = 4 hex
            "speed": int(hex_data[62:66], 16),          # WORD = 4 hex
            "direction": int(hex_data[66:70], 16),      # WORD = 4 hex
            "time": hex_data[70:82],                    # BCD[6] = 6 bytes = 12 hex
            "formated_time": formatted_time,
            "mileage": int(hex_data[82:94], 16)         # BCD[6] = 12 hex
        }
        return data
    except Exception as e:
        print(f"Error parsing hex data: {e}")
        return None

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to topic: {MQTT_TOPIC}")

def safe_append_to_file(path, content, is_json=False):
    try:
        with open(path, "a") as f:
            if is_json:
                json.dump(content, f)
                f.write("\n")
            else:
                f.write(content + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[ERROR] Failed to write to {path}: {e}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload
        hex_data = payload.hex()
        json_data = {
            "topic": msg.topic,
            "raw_data": hex_data,
            "length": len(payload),
        }

        parsed_data = parse_hex_data(hex_data)

        # Save both raw and parsed data
        safe_append_to_file("raw_data.log", hex_data)

        if parsed_data:
            safe_append_to_file("parsed_data.json", parsed_data, is_json=True)
        send_hex_to_odoo_jsonrpc(hex_data,parsed_data)
        # Print file paths
        parsed_path = os.path.abspath("parsed_data.json")
        raw_path = os.path.abspath("raw_data.log")
        print(f"Parsed JSON will be saved to: {parsed_path}")
        print(f"Raw hex logs will be saved to: {raw_path}")

        # Display parsed output
        if parsed_data:
            print("Parsed JSON Data at:", datetime.now())
            print(json.dumps(parsed_data, indent=4))

        print("Received Metadata:\n", json.dumps(json_data, indent=4))

    except Exception as e:
        print(f"Error processing message: {e}")

# MQTT Setup
# on_connect('client','userdate','flags')
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
