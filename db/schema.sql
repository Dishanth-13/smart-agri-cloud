-- Schema for smart-agri-cloud
-- Requires TimescaleDB extension

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS farms (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT
);

-- Insert sample farms if not exist
INSERT INTO farms (name, location) VALUES
    (E'Farm North', E'North Region'),
    (E'Farm South', E'South Region'),
    (E'Farm East', E'East Region'),
    (E'Farm West', E'West Region'),
    (E'Demo Farm', E'Lab')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS sensors (
    id SERIAL PRIMARY KEY,
    sensor_id TEXT UNIQUE NOT NULL,
    farm_id INTEGER REFERENCES farms(id)
);

CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS readings (
    id BIGSERIAL,
    ts TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    sensor_id TEXT,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    ph DOUBLE PRECISION,
    rainfall DOUBLE PRECISION,
    n INTEGER,
    p INTEGER,
    k INTEGER,
    farm_id INTEGER,
    PRIMARY KEY (ts, id),
    CONSTRAINT fk_farm FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL
);

SELECT create_hypertable('readings', 'ts', if_not_exists => TRUE);
