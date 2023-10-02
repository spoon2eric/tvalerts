-- Create Tables
CREATE TABLE IF NOT EXISTS tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ticker_plan (
    ticker_id INTEGER,
    plan_id INTEGER,
    PRIMARY KEY (ticker_id, plan_id),
    FOREIGN KEY (ticker_id) REFERENCES tickers (id),
    FOREIGN KEY (plan_id) REFERENCES plans (id)
);

CREATE TABLE IF NOT EXISTS stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    plan_id INTEGER,
    sequence INTEGER NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES plans (id)
);

CREATE TABLE IF NOT EXISTS ticker_stage_status (
    ticker_id INTEGER,
    stage_id INTEGER,
    status TEXT DEFAULT 'waiting',
    PRIMARY KEY (ticker_id, stage_id),
    FOREIGN KEY (ticker_id) REFERENCES tickers (id),
    FOREIGN KEY (stage_id) REFERENCES stages (id)
);

CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker_id INTEGER,
    plan_id INTEGER,
    error_message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker_id) REFERENCES tickers (id),
    FOREIGN KEY (plan_id) REFERENCES plans (id)
);

-- Insert initial data
INSERT OR IGNORE INTO tickers (name) VALUES ('ETHUSD'), ('BTCUSD'), ('LINKUSD'), ('MASKUSD'), ('PEPEUSD'), ('AVAXUSD'), ('FTMUSD'), ('AGIXUSD');