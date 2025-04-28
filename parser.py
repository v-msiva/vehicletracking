import json

def degrees_to_8_compass(degrees):
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(degrees / 45) % 8
    return directions[index]

def bcd_to_str(bcd_hex):
    return ''.join(f"{(byte >> 4) & 0xF}{byte & 0xF}" for byte in bytes.fromhex(bcd_hex))
def hex_to_ascii(hex_str):
    try:
        ascii_str = bytes.fromhex(hex_str).decode('ascii')
        return ascii_str
    except ValueError as e:
        return f"Error decoding hex: {e}"

def split_data(txt_content):
    txt_content = txt_content.replace(" ", "").upper()

    result = {}
    if len(txt_content) < 30:
        return {"error": "Insufficient data length!"}

    if not (txt_content.startswith("7E") and txt_content.endswith("7E")):
        return {"error": "Missing package header and tail!"}

    result["Flag Start"] = "7E"
    txt_content = txt_content[2:]

    msg_id = txt_content[:4]
    result["Message ID"] = msg_id
    txt_content = txt_content[4:]

    result["Message Properties"] = txt_content[:4]
    txt_content = txt_content[4:]

    result["Device Number"] = txt_content[:12]
    txt_content = txt_content[12:]

    result["Message Sequence Number"] = txt_content[:4]
    txt_content = txt_content[4:]

    check_num = txt_content[-4:-2]
    end_flag = txt_content[-2:]
    txt_content = txt_content[:-4]

    if msg_id == "0200":
        result["Location Info"] = split_location(txt_content)
    else:
        result["Response message body"] = txt_content

    result["Checksum Code"] = check_num
    result["Flag End"] = end_flag
    return result


def split_location(txt_content):
    loc = {}

    loc["Alarm Flag"] = txt_content[:8]
    txt_content = txt_content[8:]

    loc["Status Flag"] = txt_content[:8]
    txt_content = txt_content[8:]

    loc["Latitude"] = int(txt_content[:8],16)/1000000
    txt_content = txt_content[8:]

    loc["Longitude"] = int(txt_content[:8],16)/1000000
    txt_content = txt_content[8:]

    loc["Altitude"] =int(txt_content[:4],16)
    txt_content = txt_content[4:]

    loc["Speed"] = int(txt_content[:4],16)/10
    txt_content = txt_content[4:]

    loc["Direction"] = degrees_to_8_compass(int(txt_content[:4],16))
    txt_content = txt_content[4:]

    loc["Time"] = txt_content[:12]
    txt_content = txt_content[12:]

    loc["Extra Info"] = split_location_extra_info(txt_content)
    return loc


def split_location_extra_info(txt_content):
    extra_info = []

    while len(txt_content) > 3:
        extra_info_id = txt_content[:2]
        extra_info_len = txt_content[2:4]
        body_len = int(extra_info_len, 16) * 2

        if len(txt_content) < 4 + body_len:
            extra_info.append({
                "Extension ID": f"0x{extra_info_id}",
                "Length": body_len,
                "Remaining": txt_content,
                "Note": "The remaining message length is insufficient, which may be abnormal data!"
            })
            break

        extra_body = txt_content[4:4 + body_len]
        extra_info.append(get_extra_desc(extra_info_id, extra_info_len, extra_body))

        txt_content = txt_content[4 + body_len:]


    return extra_info

def get_extra_desc(extra_info_id, extra_info_len, extra_body):
    result = {
        "extraInfoId": extra_info_id,
        "extraInfoLen": extra_info_len,
        "desc": "Unknown",
        # "raw": extra_body,
        "parsed": []
    }

    if extra_info_id == "01":
        result["desc"] = "Mileage"

    elif extra_info_id == "30":
        result["desc"] = "Mobile Network Signal Strength"

    elif extra_info_id == "31":
        result["desc"] = "GNSS Number of Positioning Satellites"

    elif extra_info_id == "F0":
        result["desc"] = "Base Station Information"
        if len(extra_body) % 24 == 0:
            while len(extra_body) >= 24:
                part = extra_body[:24]
                entry = {
                    "Mobile country code": part[0:4],
                    "Network code": part[4:6],
                    "Cell Tower id": part[6:14],
                    "Location area code": part[14:22],
                    "Signal strenght": part[22:24]
                }
                result["parsed"].append(entry)
                extra_body = extra_body[24:]
        else:
            while len(extra_body) >= 26:
                part = extra_body[:26]
                entry = {
                    "Mobile country code": int(part[0:4],16),
                    "Network code": part[4:8],
                    "Cell Tower id": part[8:16],
                    "Location": part[16:24],
                    "Signal": part[24:26]
                }
                result["parsed"].append(entry)
                extra_body = extra_body[26:]
    elif extra_info_id == "F2":
        result["desc"] = "Softwawre  Ver"
        result["parsed"].append(hex_to_ascii(extra_body))
    elif extra_info_id == "F3":
        result["desc"] = "Bluetooth List"
        mask_ble = extra_body[:2]
        result["parsed"].append({"mask": mask_ble})
        extra_body = extra_body[2:]

        while len(extra_body) >= 14:
            mask = int(mask_ble, 16)
            entry = {
                "mac": extra_body[:12],
                "rssi": extra_body[12:14]
            }
            extra_body = extra_body[14:]

            if mask & 0x01:
                entry["name"] = extra_body[:20]
                extra_body = extra_body[20:]
            if mask & 0x02:
                entry["fwVer"] = extra_body[:4]
                extra_body = extra_body[4:]
            if mask & 0x04:
                entry["voltage"] = extra_body[:4]
                extra_body = extra_body[4:]
            if mask & 0x08:
                entry["temperature"] = extra_body[:4]
                extra_body = extra_body[4:]
            if mask & 0x10:
                entry["humidity"] = extra_body[:4]
                extra_body = extra_body[4:]
            if mask & 0x20:
                entry["sensor"] = extra_body[:12]
                extra_body = extra_body[12:]
            if mask & 0x40:
                entry["res1"] = extra_body[:4]
                extra_body = extra_body[4:]
            if mask & 0x80:
                entry["res2"] = extra_body[:4]
                extra_body = extra_body[4:]

            result["parsed"].append(entry)

    elif extra_info_id == "F4":
        result["desc"] = "WIFI List"
        while len(extra_body) >= 14:
            result["parsed"].append({
                "mac": extra_body[:12],
                "rssi": extra_body[12:14]
            })
            extra_body = extra_body[14:]


    elif extra_info_id == "F6":
        result["desc"] = "Trigger Type and Sensors Information"
        sensor_info = []
        data_type = extra_body[:2]
        mask_hex = extra_body[2:4]
        sensor_info.append(f"{data_type}(Data type)")
        sensor_info.append(f"{mask_hex}(Mask)")
        extra_body = extra_body[4:]
        mask = int(mask_hex, 16)
        if mask & 0x01:
            light = int(extra_body[:4],16)
            sensor_info.append(f"{light}(Light)")
            extra_body = extra_body[4:]
        if mask & 0x02:
            temperature =  int(extra_body[:4],16)/10
            sensor_info.append(f"{temperature}(Temperature C)")
            extra_body = extra_body[4:]
        if mask & 0x04:
            humidity =  int(extra_body[:4],16)/10
            sensor_info.append(f"{humidity}(Humidity RH)")
            extra_body = extra_body[4:]
        if mask & 0x08:
            accelerometer = extra_body[:12]
            sensor_info.append(f"{accelerometer}(Accelerometer)")
            extra_body = extra_body[12:]
        if mask & 0x10:
            limit = extra_body[:20]
            sensor_info.append(f"{limit}(Limit)")
            extra_body = extra_body[20:]
        if mask & 0x20:
            res1 =  int(extra_body[:4],16)
            sensor_info.append(f"{res1}(Res1)")
            extra_body = extra_body[4:]
        if mask & 0x40:
            res2 =  int(extra_body[:4],16)
            sensor_info.append(f"{res2}(Res2)")
            extra_body = extra_body[4:]
        if mask & 0x80:
            res3 =  int(extra_body[:4],16)
            sensor_info.append(f"{res3}(Res3)")
            extra_body = extra_body[4:]

        result["parsed"].append({
            "dataType": data_type,
            "mask": mask_hex,
            "sensorInfo": sensor_info
        })

    elif extra_info_id == "F7":
        result["desc"] = "Battery info"
        charging_state_map = {
            0: "Invalid",
            1: "Uncharged",
            2: "Charging",
            3: "Full",
            4: "Exceptions"
        }
        entry = {
            "Voltage": int(extra_body[0:8],16),
            "ChargingStatus": charging_state_map.get(int(extra_body[8:10], 16), "Unknown"),
            "BatteryPercentage": int(extra_body[10:12], 16)
        }
        result["parsed"].append(entry)

    elif extra_info_id == "F8":
        result["desc"] = "Device information"
        working_mode_map = {
            0: "Periodic mode",
            1: "Trigger mode",
            2: "Tracking mode + Trigger mode",
            3: "Clock mode + Trigger mode",
            4: "Periodic mode + Trigger mode"
        }
        # Parse components
        working_mode = int(extra_body[:2], 16)
        imei_bcd = extra_body[2:18]  # 8 bytes => 16 hex chars
        iccid_bcd = extra_body[18:38]  # 10 bytes => 20 hex chars
        device_type = bytes.fromhex(extra_body[38:58]).decode('ascii').strip('\x00')

        # Final parsed result
        parsed_result = {
            "Working Mode": working_mode_map.get(working_mode, f"Unknown ({working_mode})"),
            "IMEI": bcd_to_str(imei_bcd),
            "ICCID": bcd_to_str(iccid_bcd),
            "Device Type": device_type
        }

        result["parsed"].append(parsed_result)


    elif extra_info_id == "F9":
        result["desc"] = "Auxiliary Information"

        result["parsed"].append(extra_body)
        extra_body = extra_body[4:]

    elif extra_info_id == "FA":
        result["desc"] = "Pressure"
        while len(extra_body) >= 4:
            entry = {
                "sensorId": extra_body[:2],
                "pressure": extra_body[2:4]
            }
            result["parsed"].append(entry)
            extra_body = extra_body[4:]

    else:
        result["desc"] = "Unknown"

    return result

# Example Usage
if __name__ == "__main__":
    # sample input (replace with actual hex content)
    hex_input = "7e020000d7251075180278002b000000002000001200a966e3049c2905005c02dc008b25041523160001040000000030010c310105f034019400500000cf1500000931a7019400500000cf1300000931a1019400500000cf1f0000093198019400500000d04a00000931a8f22c414f56585f474d3130302d474c5f48322e305f424739354d334c415230324130335f56322e302e383a763035f60e000f01a5016901a100200010fca0f70600000e99013cf81d02086325107518027889918080264519030599474d3130302d474c0000f912000f0000000100000000006f2504152316014f7e"
    parsed_data = split_data(hex_input)
    print(json.dumps(parsed_data, indent=4))
