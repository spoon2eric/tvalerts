from socket import SocketIO
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import emit, send
from flask_socketio import SocketIO

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
    conn = sqlite3.connect('tradingview.db')
    cursor = conn.cursor()
    with open('schema.sql', 'r') as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()

@app.route("/")
def index():
    conn = sqlite3.connect('tradingview.db')
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
    conn = sqlite3.connect('tradingview.db')
    cursor = conn.cursor()

    # Getting tickers for dropdown
    cursor.execute('SELECT * FROM tickers')
    tickers = cursor.fetchall()

    if request.method == "POST":
        if 'add_plan' in request.form:
            ticker_id = request.form.get("ticker")
            plan_name = request.form.get("plan_name")
            stages_desc = request.form.getlist("stages")

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

    # Getting plans for dropdown
    cursor.execute('SELECT * FROM plans')
    plans = cursor.fetchall()

    conn.close()

    return render_template('settings.html', tickers=tickers, plans=plans)

@app.route("/get_data", methods=["GET"])
def get_data():
    conn = sqlite3.connect('tradingview.db')
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
        return jsonify(error="Database error occurred"), 500
    finally:
        conn.close()

@app.route('/webhook', methods=['POST'])
def webhook():
    conn = sqlite3.connect('tradingview.db')
    
    try:
        data = request.json
        ticker_name = data.get('ticker')
        plan_name = data.get('plan')
        stage_description = data.get('stage')

        # Validate the received data
        if not ticker_name or not plan_name or not stage_description:
            return jsonify(error="Invalid data received"), 400
        
        cursor = conn.cursor()

        # Validate ticker, plan, and stage
        cursor.execute("SELECT id FROM tickers WHERE name = ?", (ticker_name,))
        ticker_id = cursor.fetchone()
        if ticker_id is None:
            return jsonify(error="Invalid ticker"), 400
        
        cursor.execute("SELECT id FROM plans WHERE name = ?", (plan_name,))
        plan_id = cursor.fetchone()
        if plan_id is None:
            return jsonify(error="Invalid plan"), 400
        
        cursor.execute("SELECT id, sequence FROM stages WHERE description = ? AND plan_id = ?", (stage_description, plan_id[0]))
        stage = cursor.fetchone()
        if stage is None:
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
        return jsonify(error="Database error occurred"), 500
    finally:
        if conn:
            conn.close()

    return jsonify(success=True), 200

@app.route('/delete/<string:ticker>/<string:plan>', methods=['POST'])
def delete_plan(ticker, plan):
    try:
        # Connect to the database
        conn = sqlite3.connect('tradingview.db')
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
    finally:
        if conn:
            conn.close()

    return redirect(url_for('index'))

if __name__ == "__main__":
    setup_database()
    socketio.run(app, host='0.0.0.0', debug=True, port=5000)