import logging

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    filename='app.log',  # 相对路径，日志文件名为 app.log
    format='%(asctime)s - %(levelname)s - %(message)s'
)

headers = {
    "User-Agent": "",
    "Cookie": ""
}


def connect_sql():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="88888888",
        database="mysql"
    )


init_connection = None
init_cursor = None
try:
    init_connection = connect_sql()
    init_cursor = init_connection.cursor()
    create_table_query = """
                CREATE TABLE IF NOT EXISTS users (
                name VARCHAR(255) NOT NULL PRIMARY KEY,
                password VARCHAR(255) NOT NULL
            )
            """
    init_cursor.execute(create_table_query)
    init_insert_query = "INSERT INTO users (name, password) VALUES (admin, admin)"
    init_cursor.execute(init_insert_query)
    init_connection.commit()
except mysql.connector.Error:
    if init_connection:
        init_connection.rollback()
finally:
    if init_cursor:
        init_cursor.close()
    if init_connection and init_connection.is_connected():
        init_connection.close()


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


@app.route("/api/login")
def login():
    name = request.args.get('name')
    password = request.args.get('password')

    connection = None
    cursor = None
    try:
        connection = connect_sql()
        cursor = connection.cursor()

        select_rename_query = "SELECT * FROM users WHERE name = %s"
        cursor.execute(select_rename_query, (name,))
        result = cursor.fetchall()
        if len(result) == 0:
            return jsonify({"success": False, "error": "用户不存在"})

        select_password_query = "SELECT * FROM users WHERE name = %s AND password = %s"
        cursor.execute(select_password_query, (name, password))
        result = cursor.fetchall()
        if len(result) == 0:
            return jsonify({"success": False, "error": "密码错误"})

        return jsonify({"success": True, "data": name})

    except mysql.connector.Error as e:
        logging.error(e)
        if connection:
            connection.rollback()
        return jsonify({"success": False, "error": "内部错误"})
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route("/api/register")
def register():
    name = request.args.get("name")
    password = request.args.get("password")

    connection = None
    cursor = None
    try:
        connection = connect_sql()
        cursor = connection.cursor()

        select_rename_query = "SELECT * FROM users WHERE name = %s"
        cursor.execute(select_rename_query, (name,))
        result = cursor.fetchall()
        if len(result) == 1:
            return jsonify({"success": False, "error": "用户已存在"})

        insert_query = "INSERT INTO users (name, password) VALUES (%s, %s)"
        cursor.execute(insert_query, (name, password))
        connection.commit()

        return jsonify({"success": True, "data": name})

    except mysql.connector.Error as e:
        logging.error(e)
        if connection:
            connection.rollback()
        return jsonify({"success": False, "error": "内部错误"})
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


if __name__ == '__main__':
    app.run(port=5000, debug=True)
