-- Kristallik Inventory System
-- Запустить в Supabase Dashboard → SQL Editor

-- Товары
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    site_id TEXT UNIQUE,                    -- ID товара на сайте mWebby
    name TEXT NOT NULL,
    sku TEXT,
    cost_price NUMERIC(10,2) DEFAULT 0,     -- себестоимость
    sell_price NUMERIC(10,2) DEFAULT 0,     -- цена продажи
    stock_qty INTEGER DEFAULT 0,            -- остаток на складе
    unit TEXT DEFAULT 'шт',
    category TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Накладные
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    supplier TEXT,
    invoice_date DATE,
    total_cost NUMERIC(10,2),
    raw_text TEXT,                          -- сырой текст от Claude
    source TEXT,                            -- 'photo' | 'excel' | 'manual'
    telegram_file_id TEXT,
    confirmed BOOLEAN DEFAULT false,        -- подтверждено пользователем
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Движения склада (приход/расход)
CREATE TABLE IF NOT EXISTS stock_movements (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    product_name TEXT,                      -- на случай если товар не найден
    type TEXT CHECK (type IN ('in','out','correction')),
    qty INTEGER NOT NULL,
    cost_price NUMERIC(10,2),
    sell_price NUMERIC(10,2),
    invoice_id INTEGER REFERENCES invoices(id),
    order_id TEXT,                          -- ID заказа с сайта
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Заказы с сайта
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    site_order_id TEXT UNIQUE,
    order_date TIMESTAMPTZ,
    total_amount NUMERIC(10,2),
    customer_name TEXT,
    status TEXT,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- Позиции заказов
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    product_name TEXT,
    qty INTEGER,
    sell_price NUMERIC(10,2),
    cost_price NUMERIC(10,2)
);

-- Расходы
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    category TEXT,                          -- 'доставка' | 'упаковка' | 'реклама' | 'другое'
    description TEXT,
    amount NUMERIC(10,2),
    expense_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Автообновление updated_at для products
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
