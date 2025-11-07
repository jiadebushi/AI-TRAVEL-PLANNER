-- AI智能旅行规划后端 - 数据库表结构
-- 适用于 Supabase/PostgreSQL

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    preferences TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. 行程头表
CREATE TABLE IF NOT EXISTS trip_headers (
    trip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    trip_name VARCHAR(255) NOT NULL,
    destination VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. 行程详情表
CREATE TABLE IF NOT EXISTS trip_details (
    detail_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),    -- 主键
    trip_id UUID NOT NULL REFERENCES trip_headers(trip_id) ON DELETE CASCADE,    -- 外键 (关联到 trips 表)
    day_number INTEGER NOT NULL,
    theme TEXT,
    hotel_recommendation JSONB,  -- 存储 {"poi_id": "H001", "name": "...", "reasoning": "..."}
    activities JSONB,          -- 存储完整的 activities 列表 (包含 activity_type)
    UNIQUE(trip_id, day_number)   -- 约束：确保一个 trip 不会有两个 "Day 1"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. 预算表
CREATE TABLE IF NOT EXISTS budgets (
    budget_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trip_headers(trip_id) ON DELETE CASCADE,
    user_budget DECIMAL(10, 2) NOT NULL,  -- 用户准备的预算
    estimated_total DECIMAL(10, 2) NOT NULL,  -- LLM估算的总预算
    categories JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


-- 5. 开销表
CREATE TABLE IF NOT EXISTS expenses (
    expense_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trip_headers(trip_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CNY',
    description TEXT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. 行程地图表
CREATE TABLE IF NOT EXISTS trip_maps (
    map_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trip_headers(trip_id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    map_url TEXT NOT NULL,  -- 高德静态地图API返回的图片URL或base64编码
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(trip_id, day_number)  -- 确保每个行程的每一天只有一张地图
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_trip_headers_user_id ON trip_headers(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_details_trip_id ON trip_details(trip_id);
CREATE INDEX IF NOT EXISTS idx_budgets_trip_id ON budgets(trip_id);
CREATE INDEX IF NOT EXISTS idx_expenses_trip_id ON expenses(trip_id);
CREATE INDEX IF NOT EXISTS idx_expenses_timestamp ON expenses(timestamp);
CREATE INDEX IF NOT EXISTS idx_trip_maps_trip_id ON trip_maps(trip_id);
CREATE INDEX IF NOT EXISTS idx_trip_maps_trip_day ON trip_maps(trip_id, day_number);

-- 添加更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要更新时间的表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trip_headers_updated_at BEFORE UPDATE ON trip_headers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trip_details_updated_at BEFORE UPDATE ON trip_details
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_budgets_updated_at BEFORE UPDATE ON budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trip_maps_updated_at BEFORE UPDATE ON trip_maps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


