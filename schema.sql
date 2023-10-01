DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS anomalies;
DROP TABLE IF EXISTS config;
DROP TABLE IF EXISTS ticker_stages;
DROP TABLE IF EXISTS ticker_static_values;

CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    action TEXT,
    signal_type TEXT,
    stage INTEGER
);

CREATE TABLE ticker_stages (
    ticker TEXT PRIMARY KEY,
    next_expected_stage INTEGER DEFAULT 1
);

CREATE TABLE anomalies (
    id INTEGER PRIMARY KEY,
    message TEXT
);

CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value INTEGER
);

CREATE TABLE ticker_static_values (
    ticker TEXT PRIMARY KEY,
    static_value INTEGER NOT NULL
);


INSERT INTO config (key, value) VALUES ('static_number', 3);
INSERT INTO config (key, value) VALUES ('next_expected_stage', 1);
