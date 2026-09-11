#!/bin/sh
set -eu

psql --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=reader_password="$READONLY_PASSWORD" <<'SQL'
CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL
);

CREATE TABLE sales_orders (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    status TEXT NOT NULL,
    total_amount NUMERIC(12, 2) NOT NULL,
    ordered_at DATE NOT NULL
);

INSERT INTO customers (name, region) VALUES
    ('北辰科技', '华东'),
    ('远帆制造', '华南'),
    ('澄海零售', '华北');

INSERT INTO sales_orders (customer_id, status, total_amount, ordered_at) VALUES
    (1, 'paid', 12800.00, '2026-08-01'),
    (1, 'paid', 7600.00, '2026-08-16'),
    (2, 'pending', 3500.00, '2026-09-02'),
    (2, 'paid', 9200.00, '2026-09-05'),
    (3, 'cancelled', 1800.00, '2026-09-08');

CREATE ROLE trustquery_reader LOGIN PASSWORD :'reader_password';
GRANT CONNECT ON DATABASE analytics TO trustquery_reader;
GRANT USAGE ON SCHEMA public TO trustquery_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO trustquery_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO trustquery_reader;
SQL
