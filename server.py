import logging

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

headers = {
    "User-Agent": "",
    "Cookie": ""
}


def get_station_code():
    url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
    response = requests.get(url, headers=headers)
    stations = response.text.split("'")[1].split("@")
    station_dict = {}
    for station in stations[1:]:
        parts = station.split("|")
        if len(parts) >= 3:
            name = parts[1]
            code = parts[2]
            station_dict[name] = code
    return station_dict


@app.route('/api/stations')
def get_all_stations():
    try:
        station_dict = get_station_code()
        # 返回车站名称列表（中文）
        return jsonify({"success": True, "data": list(station_dict.keys())})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/tickets')
def get_tickets():
    from_station_name = request.args.get('from', '北京南')
    to_station_name = request.args.get('to', '上海虹桥')
    date = request.args.get('date', '2025-01-01')

    station_dict = get_station_code()
    from_station = station_dict.get(from_station_name)
    to_station = station_dict.get(to_station_name)

    if not from_station or not to_station:
        return jsonify({"success": False, "error": "车站名称无效"})

    url = f"https://kyfw.12306.cn/otn/leftTicket/queryR?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_station}&leftTicketDTO.to_station={to_station}&purpose_codes=ADULT"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        tickets = []
        if data.get("data"):
            for train in data["data"]["result"]:
                train_info = train.split("|")
                tickets.append({
                    "train_no": train_info[3],
                    "departure_time": train_info[8],
                    "arrival_time": train_info[9],
                    "duration": train_info[10],
                    "tickets": train_info[26]
                })
        return jsonify({"success": True, "data": tickets})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
     app.run(port=5000, debug=True)
    # get_tickets()
    # get_all_stations()
