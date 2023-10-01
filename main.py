from flask import Flask, request, jsonify, render_template, redirect, url_for
import os
import sqlite3
from contextlib import closing

app = Flask(__name__)

# Directory of the script or current file.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the data directory.
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Ensure the data directory exists, if not, create it.
os.makedirs(DATA_DIR, exist_ok=True)

# Path to the database file.
DATABASE = os.path.join(DATA_DIR, 'database.db')

def connect_db():
    return sqlite3.connect(DATABASE)

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        # Initialize ticker_stages with default tickers if needed
        db.execute("INSERT INTO ticker_stages (ticker) VALUES ('LINK'), ('PEPE');")
        db.commit()


@app.route('/', methods=['GET'])
def home():
    with closing(connect_db()) as db:
        data = db.execute("SELECT * FROM alerts").fetchall()
        anomalies = db.execute("SELECT * FROM anomalies").fetchall()
        static_number = db.execute("SELECT value FROM config WHERE key='static_number'").fetchone()[0]
    return render_template('home.html', data=data, anomalies=anomalies, static_number=static_number)

@app.route('/webhook', methods=['POST'])
def webhook():
    received_data = request.json
    print(f"Received Data: {received_data}")
    ticker = received_data.get('ticker')
    action = received_data.get('action')
    signal_type = received_data.get('signal_type')
    stage = received_data.get('stage')

    with closing(connect_db()) as db:
        total_stages = db.execute("SELECT value FROM config WHERE key='static_number'").fetchone()[0]

        # Get the next_expected_stage for the specific ticker
        next_expected_stage_row = db.execute("SELECT next_expected_stage FROM ticker_stages WHERE ticker=?", (ticker,)).fetchone()

        # If ticker does not exist in ticker_stages, insert it with default next_expected_stage as 1
        if next_expected_stage_row is None:
            db.execute("INSERT INTO ticker_stages (ticker) VALUES (?)", (ticker,))
            next_expected_stage = 1
        else:
            next_expected_stage = next_expected_stage_row[0]

        if stage != next_expected_stage:
            message = f"Anomaly detected for {ticker}. Expected stage {next_expected_stage}, received {stage}."
            db.execute("INSERT INTO anomalies (message) VALUES (?)", (message,))

        db.execute("INSERT INTO alerts (ticker, action, signal_type, stage) VALUES (?, ?, ?, ?)", 
                   (ticker, action, signal_type, stage))

        # Update the next_expected_stage for the specific ticker in the ticker_stages table
        if stage == total_stages:
            db.execute("UPDATE ticker_stages SET next_expected_stage=1 WHERE ticker=?", (ticker,))
        else:
            db.execute("UPDATE ticker_stages SET next_expected_stage=next_expected_stage+1 WHERE ticker=?", (ticker,))
        
        db.commit()

    return jsonify(status="success", data=received_data)

@app.route('/get_data', methods=['GET'])
def get_data():
    with closing(connect_db()) as db:
        alerts = db.execute("SELECT * FROM alerts").fetchall()
        anomalies = db.execute("SELECT * FROM anomalies").fetchall()
        # For debugging purpose
        for row in alerts:
            print(row)
    return jsonify(alerts=alerts, anomalies=anomalies)


@app.route('/clear', methods=['POST'])
def clear():
    clear_database()
    return redirect(url_for('home'))

def clear_database():
    with closing(connect_db()) as db:
        db.execute('DELETE FROM alerts;')
        db.execute('DELETE FROM anomalies;')
        db.execute('DELETE FROM ticker_stages;')  # Reset the ticker_stages table
        # Reinsert the default tickers with next_expected_stage as 1
        db.execute("INSERT INTO ticker_stages (ticker) VALUES ('LINK'), ('PEPE');")
        db.commit()


@app.route('/set_static', methods=['POST'])
def set_static():
    static_number = request.form.get('static_number')
    with closing(connect_db()) as db:
        db.execute("UPDATE config SET value=? WHERE key='static_number'", (static_number,))
        db.commit()
    return redirect(url_for('home'))

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/add_ticker', methods=['POST'])
def add_ticker():
    ticker = request.form.get('ticker')
    static_value = request.form.get('static_value')
    
    # Insert the new ticker and static value into the database
    # Ensure to handle the case if the ticker already exists
    
    return redirect(url_for('settings'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)