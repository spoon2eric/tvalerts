from datetime import datetime, timedelta
import sqlite3
import os
from dotenv import load_dotenv
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import emit, send
from flask_socketio import SocketIO
from pymongo import MongoClient
from pymongo.errors import PyMongoError

logging.basicConfig(level=logging.INFO)

load_dotenv()
#MongoDB connection information
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_IP = os.getenv("MONGO_IP")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_URI = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_IP}:{MONGO_PORT}/?authMechanism=DEFAULT"
MONGO_DATABASE = "market_data"
MONGO_COLLECTION_MCB = "market_cipher_b"

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DATABASE]
collection = db[MONGO_COLLECTION_MCB]


# Directory of the script or current file.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the data directory.
DATA_DIR = os.path.join(BASE_DIR, 'data')
#DATA_DIR = os.path.join(BASE_DIR, 'data')

# Ensure the data directory exists, if not, create it.
os.makedirs(DATA_DIR, exist_ok=True)

# Path to the database file.
DATABASE = os.path.join(DATA_DIR, 'database.db')

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    print("Client Connected")
    emit('response', {'data': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print("Client Disconnected")

def setup_database():
    logging.info("Setting up database...")
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        with open('schema.sql', 'r') as f:
            cursor.executescript(f.read())
        conn.commit()
        logging.info("Database setup completed successfully.")
    except Exception as e:
        logging.error(f"Error setting up database: {e}")
    finally:
        if conn:
            conn.close()

def setup_mongodb():
    logging.info("Setting up MongoDB...")
    try:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client[MONGO_DATABASE]

        # Check if collection exists; if not, create it.
        # Note: This step is optional because MongoDB automatically creates collections when inserting documents.
        if MONGO_COLLECTION_MCB not in db.list_collection_names():
            db.create_collection(MONGO_COLLECTION_MCB)
            logging.info(f"Collection {MONGO_COLLECTION_MCB} created.")
        else:
            logging.info(f"Collection {MONGO_COLLECTION_MCB} already exists.")
        
        logging.info("MongoDB setup completed successfully.")

    except Exception as e:
        logging.error(f"Error setting up MongoDB: {e}")

@socketio.on('new_alert')
def handle_new_alert(data):
    message = data.get('message')
    
    # Adjusted time
    adjusted_time = datetime.utcnow() - timedelta(hours=5)
    timestamp = adjusted_time.strftime('%Y-%m-%d %H:%M:%S')

    # Connect to the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Insert the new alert into the alerts table
        cursor.execute('INSERT INTO alerts (message, timestamp) VALUES (?, ?)', (message, timestamp))
        conn.commit()

        # Emit the alert to all connected clients
        socketio.emit('new_alert', {'timestamp': datetime.now().strftime('%m/%d %H:%M'), 
                            'message': formatted_message})


    except sqlite3.Error as e:
        print("Database error:", e)
        logging.info(f"Database error: ", e)
    finally:
        if conn:
            conn.close()

@app.route('/alerts')
def alerts():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC")
    raw_alerts = cursor.fetchall()
    conn.close()

    # Format the datetime strings for display
    formatted_alerts = []
    for alert in raw_alerts:
        adjusted_date = datetime.strptime(alert[4], '%Y-%m-%d %H:%M:%S').strftime('%m/%d %H:%M')
        formatted_alerts.append((alert[0], adjusted_date, alert[1], alert[2], alert[3]))

    return render_template('alerts.html', alerts=formatted_alerts)

@app.route("/")
def index():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''SELECT tickers.name as ticker_name, plans.name as plan_name, 
                             stages.description, ticker_stage_status.status, stages.sequence
                      FROM ticker_plan
                      JOIN tickers ON ticker_plan.ticker_id = tickers.id
                      JOIN plans ON ticker_plan.plan_id = plans.id
                      JOIN stages ON plans.id = stages.plan_id
                      JOIN ticker_stage_status ON stages.id = ticker_stage_status.stage_id AND tickers.id = ticker_stage_status.ticker_id
                      ORDER BY tickers.name, plans.name, stages.sequence''')
    
    data = {}
    for row in cursor.fetchall():
        ticker_name = row[0]
        plan_name = row[1]
        stage_description = row[2]
        status = row[3]  # unpacking status
        sequence = row[4]  # unpacking sequence

        if ticker_name not in data:
            data[ticker_name] = {}
        
        if plan_name not in data[ticker_name]:
            data[ticker_name][plan_name] = {'stages': [], 'errors': []}  # initialize 'stages' and 'errors'
        
        data[ticker_name][plan_name]['stages'].append((stage_description, status, sequence))  # using unpacked status and sequence
        
    # Fetching error messages
    cursor.execute('''SELECT tickers.name as ticker_name, plans.name as plan_name, errors.error_message
                      FROM errors
                      JOIN tickers ON errors.ticker_id = tickers.id
                      JOIN plans ON errors.plan_id = plans.id''')

    for row in cursor.fetchall():
        ticker_name = row[0]
        plan_name = row[1]
        error_message = row[2]

        if ticker_name in data and plan_name in data[ticker_name]:
            data[ticker_name][plan_name]['errors'].append(error_message)

    conn.close()
    return render_template('index.html', data=data)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Getting tickers for dropdown
    cursor.execute('SELECT * FROM tickers')
    tickers = cursor.fetchall()

    if request.method == "POST":
        if 'add_plan' in request.form:
            ticker_id = request.form.get("ticker")
            plan_name = request.form.get("plan_name")
            stages_desc = request.form.getlist("stages")

            # Check if the plan already exists
            cursor.execute("SELECT * FROM plans WHERE name=?", (plan_name,))
            existing_plan = cursor.fetchone()
            if existing_plan:
                cursor.execute('SELECT * FROM plans')
                plans = cursor.fetchall()
                conn.close()
                return render_template('settings.html', plan_exists=True, tickers=tickers, plans=plans)

            # Creating a new plan
            cursor.execute('INSERT INTO plans (name) VALUES (?)', (plan_name,))
            plan_id = cursor.lastrowid

            # Creating stages for the new plan
            for idx, stage in enumerate(stages_desc, start=1):
                cursor.execute('INSERT INTO stages (description, plan_id, sequence) VALUES (?, ?, ?)', (stage, plan_id, idx))

            # Associating ticker with the new plan
            cursor.execute('INSERT OR IGNORE INTO ticker_plan (ticker_id, plan_id) VALUES (?, ?)', (ticker_id, plan_id))

            # Initializing the status of stages for the ticker
            cursor.execute('SELECT id FROM stages WHERE plan_id = ?', (plan_id,))
            stage_ids = cursor.fetchall()
            for stage_id in stage_ids:
                cursor.execute('''INSERT OR IGNORE INTO ticker_stage_status (ticker_id, stage_id) 
                                  VALUES (?, ?)''', (ticker_id, stage_id[0]))

            conn.commit()
        
        elif 'add_ticker_to_plan' in request.form:
            ticker_id = request.form.get("ticker_to_add")
            plan_id = request.form.get("plan_to_add")

            # Associating another ticker with an existing plan
            cursor.execute('INSERT OR IGNORE INTO ticker_plan (ticker_id, plan_id) VALUES (?, ?)', (ticker_id, plan_id))

            # Initializing the status of stages for the additional ticker
            cursor.execute('SELECT id FROM stages WHERE plan_id = ?', (plan_id,))
            stage_ids = cursor.fetchall()
            for stage_id in stage_ids:
                cursor.execute('''INSERT OR IGNORE INTO ticker_stage_status (ticker_id, stage_id) 
                                  VALUES (?, ?)''', (ticker_id, stage_id[0]))

            conn.commit()

        elif 'delete_plan_submit' in request.form:
            plan_id_to_delete = request.form.get("delete_plan")

            # Deleting associated ticker_stage_status entries
            cursor.execute('DELETE FROM ticker_stage_status WHERE stage_id IN (SELECT id FROM stages WHERE plan_id = ?)', (plan_id_to_delete,))

            # Deleting associated stages
            cursor.execute('DELETE FROM stages WHERE plan_id = ?', (plan_id_to_delete,))

            # Deleting associations in ticker_plan
            cursor.execute('DELETE FROM ticker_plan WHERE plan_id = ?', (plan_id_to_delete,))

            # Deleting the plan
            cursor.execute('DELETE FROM plans WHERE id = ?', (plan_id_to_delete,))

            conn.commit()

        elif 'add_ticker' in request.form:
            new_ticker_name = request.form.get("new_ticker_name")
            if new_ticker_name:
                # Insert the new ticker
                cursor.execute('INSERT OR IGNORE INTO tickers (name) VALUES (?)', (new_ticker_name,))
                conn.commit()
                
        elif 'delete_ticker' in request.form:
            ticker_id_to_delete = request.form.get("ticker_to_delete")

            # Deleting associated ticker_stage_status entries
            cursor.execute('DELETE FROM ticker_stage_status WHERE ticker_id = ?', (ticker_id_to_delete,))

            # Deleting associations in ticker_plan
            cursor.execute('DELETE FROM ticker_plan WHERE ticker_id = ?', (ticker_id_to_delete,))

            # Deleting the ticker
            cursor.execute('DELETE FROM tickers WHERE id = ?', (ticker_id_to_delete,))
            
            conn.commit()

            # Re-fetch tickers after deletion
            cursor.execute('SELECT * FROM tickers')
            tickers = cursor.fetchall()

    # Getting plans for dropdown
    cursor.execute('SELECT * FROM plans')
    plans = cursor.fetchall()

    conn.close()

    return render_template('settings.html', tickers=tickers, plans=plans)

@app.route("/clear_alerts", methods=["POST"])
def clear_alerts():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM alerts')
    conn.commit()

    conn.close()

    return jsonify(status='success')


@app.route("/get_data", methods=["GET"])
def get_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''SELECT tickers.name as ticker_name, plans.name as plan_name, 
                                 stages.description, ticker_stage_status.status, stages.sequence
                          FROM ticker_plan
                          JOIN tickers ON ticker_plan.ticker_id = tickers.id
                          JOIN plans ON ticker_plan.plan_id = plans.id
                          JOIN stages ON plans.id = stages.plan_id
                          JOIN ticker_stage_status ON stages.id = ticker_stage_status.stage_id AND tickers.id = ticker_stage_status.ticker_id
                          ORDER BY tickers.name, plans.name, stages.sequence''')

        data = {}
        for row in cursor.fetchall():
            ticker_name = row[0]
            plan_name = row[1]
            stage_description = row[2]
            status = row[3]  # unpacking status
            sequence = row[4]  # unpacking sequence

            if ticker_name not in data:
                data[ticker_name] = {}

            if plan_name not in data[ticker_name]:
                data[ticker_name][plan_name] = {'stages': [], 'errors': []}  # initialize 'stages' and 'errors'

            data[ticker_name][plan_name]['stages'].append((stage_description, status, sequence))  # using unpacked status and sequence

        # Fetching error messages
        cursor.execute('''SELECT tickers.name as ticker_name, plans.name as plan_name, errors.error_message
                          FROM errors
                          JOIN tickers ON errors.ticker_id = tickers.id
                          JOIN plans ON errors.plan_id = plans.id''')

        for row in cursor.fetchall():
            ticker_name = row[0]
            plan_name = row[1]
            error_message = row[2]

            if ticker_name in data and plan_name in data[ticker_name]:
                data[ticker_name][plan_name]['errors'].append(error_message)

        return jsonify(data), 200

    except sqlite3.Error as e:
        print("Database error:", e)
        logging.info(f"Database error: ", e)
        return jsonify(error="Database error occurred"), 500
    finally:
        conn.close()

@app.route('/mongo-mcbdata', methods=['POST'])
def mongo_mcbdatahook():
    try:
        data = request.json
        logging.info(f"Received payload at /mongo-mcbdata: {data}")

        # Validate the received data (same as before)
        required_fields = ['TV Time', 'Time Frame', 'type', 'ticker', 'price', 'Lt Blue Wave', 'Blue Wave', 'VWAP', 'Mny Flow', 'Buy', 'Blue Wave Crossing UP', 'Blue Wave Crossing Down', 'Zero', '100%', 'OB 1 Solid', 'OS 1 Solid', 'Trigger 1', 'Trigger 2', 'RSI', 'Sto RSI']
        if not all(data.get(field) for field in required_fields):
            logging.info(f"Invalid data received for mongo-mcbdata route")
            return jsonify(error="Invalid data received for mongo-mcbdata route"), 400

        # Instead of extracting each data point, you can just insert the entire data object into MongoDB (assuming all the keys are valid fields in your MongoDB collection)
        collection.insert_one(data)
        logging.info(f"MongoDB INSERT command was successful.")
        
    except PyMongoError as e:
        logging.info(f"MongoDB Database error: {e}")
        return jsonify(error="MongoDB Database error occurred"), 500

    return jsonify(success=True), 200

@app.route('/mcbdatahook', methods=['POST'])
def mcbdatahook():
    conn = sqlite3.connect(DATABASE)

    try:
        data = request.json
        logging.info(f"Received payload at /mcbdatahook: {data}")
        #Formatting for MarketCiper B
        time_value = data.get('TV Time')
        timeframe_value = data.get('Time Frame')
        indicator_name = data.get('type') #Name of the indicator
        ticker_value = data.get('ticker')
        lt_blue_wave = data.get('Lt Blue Wave')
        blue_wave = data.get('Blue Wave')
        vwap_value = data.get('VWAP')
        mny_flow = data.get('Mny Flow')
        big_green_dot = data.get('Buy') #Value will be 1 if Green Dot appears
        bw_crossing_up = data.get('Blue Wave Crossing UP')
        bw_crossing_down = data.get('Blue Wave Crossing Down')
        zero_line = data.get('Zero')
        _100_percent = data.get('100%')
        ob_1_solid = data.get('OB 1 Solid')
        os_1_solid = data.get('OS 1 Solid')
        trigger_1 = data.get('Trigger 1')
        trigger_2 = data.get('Trigger 2')
        rsi_value = data.get('RSI')
        sto_rsi = data.get('Sto RSI')

        # Validate the received data
        if not time_value or not timeframe_value or not indicator_name or not ticker_value or not lt_blue_wave or not blue_wave or not vwap_value or not mny_flow or not big_green_dot or not bw_crossing_up or not bw_crossing_down or not zero_line or not _100_percent or not ob_1_solid or not os_1_solid or not trigger_1 or not trigger_2 or not rsi_value or not sto_rsi:
            logging.info(f"Invalid data received")
            return jsonify(error="Invalid data received"), 400
        
        cursor = conn.cursor()

        cursor.execute('INSERT INTO market_cipher_b (time_value, timeframe_value, ticker_value, lt_blue_wave, blue_wave, vwap_value, mny_flow, big_green_dot, bw_crossing_up, bw_crossing_down, zero_line, _100_percent, ob_1_solid, os_1_solid, trigger_1, trigger_2, rsi_value, sto_rsi) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                    (time_value, timeframe_value, ticker_value, lt_blue_wave, blue_wave, vwap_value, mny_flow, big_green_dot, bw_crossing_up, bw_crossing_down, zero_line, _100_percent, ob_1_solid, os_1_solid, trigger_1, trigger_2, rsi_value, sto_rsi))
        conn.commit()
        logging.info(f"INSERT command was successful.")

    except sqlite3.Error as e:
        print("Database error:", e)
        logging.info(f"Database error: {e}")
        return jsonify(error="Database error occurred"), 500
    finally:
        if conn:
            conn.close()

    return jsonify(success=True), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    conn = sqlite3.connect(DATABASE)
    
    try:
        data = request.json
        logging.info(f"Received payload at /webhook: {data}")
        ticker_name = data.get('ticker')
        plan_name = data.get('plan')
        stage_description = data.get('stage')

        # Validate the received data
        if not ticker_name or not plan_name or not stage_description:
            logging.info(f"Invalid data received")
            return jsonify(error="Invalid data received"), 400
        
        cursor = conn.cursor()

        cursor.execute('INSERT INTO alerts (ticker, plan, stage) VALUES (?, ?, ?)', 
                    (ticker_name, plan_name, stage_description))
        conn.commit()

        # Formulate a message for the clients
        formatted_message = f"Ticker: {ticker_name}, Plan: {plan_name}, Stage: {stage_description}"
        
        # Emit the alert to all connected clients
        socketio.emit('new_alert', {'timestamp': datetime.now().strftime('%m/%d %H:%M'), 
                            'message': formatted_message})

        # Validate ticker, plan, and stage
        cursor.execute("SELECT id FROM tickers WHERE name = ?", (ticker_name,))
        ticker_id = cursor.fetchone()
        if ticker_id is None:
            logging.info(f"Invalid ticker received: ", (ticker_name))
            return jsonify(error="Invalid ticker"), 400
        
        cursor.execute("SELECT id FROM plans WHERE name = ?", (plan_name,))
        plan_id = cursor.fetchone()
        if plan_id is None:
            logging.info(f"Invalid plan received: ", (plan_name))
            return jsonify(error="Invalid plan"), 400
        
        cursor.execute("SELECT id, sequence FROM stages WHERE description = ? AND plan_id = ?", (stage_description, plan_id[0]))
        stage = cursor.fetchone()
        if stage is None:
            logging.info(f"Invalid stage: ", (stage))
            return jsonify(error="Invalid stage"), 400

        # Validate the sequence
        sequence = stage[1]
        cursor.execute('''SELECT MAX(stages.sequence) 
                          FROM stages
                          JOIN ticker_stage_status ON stages.id = ticker_stage_status.stage_id
                          WHERE ticker_stage_status.status = 'completed' AND stages.plan_id = ? AND ticker_stage_status.ticker_id = ?''', 
                       (plan_id[0], ticker_id[0]))
        max_completed_sequence = cursor.fetchone()[0] or 0
        if sequence != max_completed_sequence + 1:
            error_message = "Stage completed out of order"
            cursor.execute("INSERT INTO errors (ticker_id, plan_id, error_message) VALUES (?, ?, ?)", 
                           (ticker_id[0], plan_id[0], error_message))
            conn.commit()
            return jsonify(error=error_message), 400
        
        # Update the stage status regardless of the sequence
        cursor.execute("UPDATE ticker_stage_status SET status = 'completed' WHERE stage_id = ? AND ticker_id = ?", (stage[0], ticker_id[0]))
        conn.commit()

        # Fetching error messages related to the stage being updated
        cursor.execute('''SELECT errors.error_message
                          FROM errors
                          JOIN tickers ON errors.ticker_id = tickers.id
                          JOIN plans ON errors.plan_id = plans.id
                          WHERE tickers.name = ? AND plans.name = ?''', 
                       (ticker_name, plan_name))
        
        errors_for_stage = [row[0] for row in cursor.fetchall()]

        # Emitting a WebSocket message to notify the clients about the stage completion
        data = {"ticker": ticker_name, "plan": plan_name, "stage": stage_description, "status": 'completed', "errors": errors_for_stage}
        socketio.emit('stage_updated', data, namespace='/', room=None)

    except sqlite3.Error as e:
        print("Database error:", e)
        logging.info(f"Database error: ", e)
        return jsonify(error="Database error occurred"), 500
    finally:
        if conn:
            conn.close()

    return jsonify(success=True), 200

@app.route('/reset_stages', methods=['POST'])
def reset_stages():
    ticker = request.form.get('ticker')
    plan = request.form.get('plan')

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    
    # Step 1: Delete from the errors table
    cur.execute("""
        DELETE FROM errors
        WHERE ticker_id = (SELECT id FROM tickers WHERE name = ?)
        AND plan_id = (SELECT id FROM plans WHERE name = ?)
    """, (ticker, plan))

    # Step 2: Reset the status in the ticker_stage_status table
    cur.execute("""
        UPDATE ticker_stage_status
        SET status = 'waiting'
        WHERE ticker_id = (SELECT id FROM tickers WHERE name = ?)
        AND stage_id IN (SELECT id FROM stages WHERE plan_id = (SELECT id FROM plans WHERE name = ?))
    """, (ticker, plan))
    
    conn.commit()
    conn.close()

    # Redirect back to the index after resetting
    return redirect(url_for('index'))

@app.route('/delete/<string:ticker>/<string:plan>', methods=['POST'])
def delete_plan(ticker, plan):
    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        # Find the ids of the ticker and plan from their names
        c.execute("SELECT id FROM tickers WHERE name = ?", (ticker,))
        ticker_id = c.fetchone()
        if ticker_id is None:
            return "Ticker not found", 404

        c.execute("SELECT id FROM plans WHERE name = ?", (plan,))
        plan_id = c.fetchone()
        if plan_id is None:
            return "Plan not found", 404

        # Delete associated rows in ticker_plan, ticker_stage_status, and errors table
        c.execute("DELETE FROM ticker_plan WHERE ticker_id = ? AND plan_id = ?", (ticker_id[0], plan_id[0]))
        c.execute("DELETE FROM errors WHERE ticker_id = ? AND plan_id = ?", (ticker_id[0], plan_id[0]))
        
        # Get all stages associated with the plan and delete their statuses in ticker_stage_status
        c.execute("SELECT id FROM stages WHERE plan_id = ?", (plan_id[0],))
        stage_ids = [row[0] for row in c.fetchall()]
        for stage_id in stage_ids:
            c.execute("DELETE FROM ticker_stage_status WHERE ticker_id = ? AND stage_id = ?", (ticker_id[0], stage_id))
        
        # Commit the transaction
        conn.commit()

    except sqlite3.Error as e:
        print("Database error:", e)
        logging.info(f"Database error: ", e)
    finally:
        if conn:
            conn.close()

    return redirect(url_for('index'))

def find_target_id():
    # Connect to the SQLite database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Execute the SQL query to fetch all records from the 'market_cipher_b' table
    cursor.execute('SELECT * FROM market_cipher_b')
    rows = cursor.fetchall()

    # Column names (based on the provided table structure)
    columns = ['id', 'time_value', 'timeframe_value', 'ticker', 'lt_blue_wave', 'blue_wave', 'vwap_value', 
               'mny_flow', 'big_green_dot', 'bw_crossing_up', 'bw_crossing_down', 'zero_line', 
               '_100_percent', 'ob_1_solid', 'os_1_solid', 'trigger_1', 'trigger_2', 'rsi_value', 'sto_rsi']

    # Convert rows into a list of dictionaries
    records = [dict(zip(columns, row)) for row in rows]
    for record in records:
        record['id'] = int(record['id'])
        record['bw_crossing_down'] = int(record['bw_crossing_down']) if record['bw_crossing_down'] != 'null' else 0  # or another default value
        record['zero_line'] = int(record['zero_line'])
        record['bw_crossing_up'] = int(record['bw_crossing_up']) if record['bw_crossing_up'] != 'null' else 0
        # any other fields that need to be converted...



    # Use a helper function to attempt the conversion
    def is_big_green_dot(record):
        try:
            return int(record['big_green_dot']) == 1
        except ValueError:
            return False

    # Step 1: Find the maximum id with "15MIN" timeframe and big_green_dot value of 1
    ids_with_15MIN_and_big_green_dot = [record['id'] for record in records if record['timeframe_value'] == "5MIN" and record['big_green_dot'] == 1]
    start_id = max(ids_with_15MIN_and_big_green_dot) if ids_with_15MIN_and_big_green_dot else None
    
    logging.debug("ID's with Big Green Dot: ", ids_with_15MIN_and_big_green_dot)
    print("ID's with Big Green Dot: ", ids_with_15MIN_and_big_green_dot)

    if not start_id:
        conn.close()
        return None

    # Step 2: Find the first id from start_id where bw_crossing_down is greater than zero_line and both bw_crossing_up and bw_crossing_down are non-negative
    for record in records:
        if int(record['id']) > int(start_id) and record['bw_crossing_down'] > record['zero_line'] and record['bw_crossing_up'] >= 0 and record['bw_crossing_down'] >= 0:
            start_id = record['id']
            logging.debug("First Red Dot: ", start_id)
            print("First Red Dot - ID: ", start_id)
            break

    # Step 3: Find the first id from start_id where bw_crossing_up is less than zero_line and greater than os_1_solid
    for record in records:
        if record['id'] > start_id and record['bw_crossing_up'] < record['zero_line'] and record['bw_crossing_up'] > record['os_1_solid']:
            conn.close()
            logging.debug("First Green Dot for Buy if found: ", start_id)
            print("First Green Dot for Buy if found - ID: ", start_id)
            return record['id']

    conn.close()
    return None


#setup_database()
setup_mongodb()
find_target_id()

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', debug=False, port=5000)