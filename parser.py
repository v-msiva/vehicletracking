import json

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

    loc["Latitude"] = txt_content[:8]
    txt_content = txt_content[8:]

    loc["Longitude"] = txt_content[:8]
    txt_content = txt_content[8:]

    loc["Altitude"] = txt_content[:4]
    txt_content = txt_content[4:]

    loc["Speed"] = txt_content[:4]
    txt_content = txt_content[4:]

    loc["Direction"] = txt_content[:4]
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
        "raw": extra_body,
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
                    "mcc": part[0:4],
                    "mnc": part[4:6],
                    "ci": part[6:14],
                    "lac": part[14:22],
                    "rssi": part[22:24]
                }
                result["parsed"].append(entry)
                extra_body = extra_body[24:]
        else:
            while len(extra_body) >= 26:
                part = extra_body[:26]
                entry = {
                    "mcc": part[0:4],
                    "mnc": part[4:8],
                    "ci": part[8:16],
                    "lac": part[16:24],
                    "rssi": part[24:26]
                }
                result["parsed"].append(entry)
                extra_body = extra_body[26:]

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
        while len(extra_body) >= 4:
            mask = extra_body[:4]
            entry = {"mask": mask}
            extra_body = extra_body[4:]

            if int(mask, 16) & 0x01:
                entry["triggerType"] = "Emergency"
            if int(mask, 16) & 0x02:
                entry["triggerType"] = "Scheduled"
            if int(mask, 16) & 0x04:
                entry["triggerType"] = "Manual"
            if int(mask, 16) & 0x08:
                entry["sensorStatus"] = "Active"
            if int(mask, 16) & 0x10:
                entry["sensorStatus"] = "Inactive"
            if int(mask, 16) & 0x20:
                entry["sensorStatus"] = "Faulty"
            if int(mask, 16) & 0x40:
                entry["sensorStatus"] = "Unknown"

            result["parsed"].append(entry)

    elif extra_info_id == "F7":
        result["desc"] = "GPS Coordinates"
        while len(extra_body) >= 20:
            entry = {
                "latitude": extra_body[:10],
                "longitude": extra_body[10:20]
            }
            result["parsed"].append(entry)
            extra_body = extra_body[20:]

    elif extra_info_id == "F8":
        result["desc"] = "Temperature"
        while len(extra_body) >= 4:
            entry = {
                "sensorId": extra_body[:2],
                "temperature": extra_body[2:4]
            }
            result["parsed"].append(entry)
            extra_body = extra_body[4:]

    elif extra_info_id == "F9":
        result["desc"] = "Humidity"
        while len(extra_body) >= 4:
            entry = {
                "sensorId": extra_body[:2],
                "humidity": extra_body[2:4]
            }
            result["parsed"].append(entry)
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
