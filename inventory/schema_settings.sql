-- Настройки системы
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Курс доллара по умолчанию
INSERT INTO settings (key, value) VALUES ('exchange_rate', '41.5')
ON CONFLICT (key) DO NOTHING;
