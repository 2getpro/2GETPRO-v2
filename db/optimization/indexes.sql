-- ============================================
-- SQL индексы для оптимизации производительности
-- 2GETPRO_v2 Database Optimization
-- ============================================

-- ==================== Таблица users ====================

-- Основные индексы для поиска пользователей
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Индексы для фильтрации и сортировки
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at);
CREATE INDEX IF NOT EXISTS idx_users_is_banned ON users(is_banned);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Композитные индексы для частых запросов
CREATE INDEX IF NOT EXISTS idx_users_active_banned ON users(is_active, is_banned);
CREATE INDEX IF NOT EXISTS idx_users_telegram_active ON users(telegram_id, is_active);

-- ==================== Таблица subscriptions ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_plan_id ON subscriptions(plan_id);

-- Индексы для временных запросов
CREATE INDEX IF NOT EXISTS idx_subscriptions_created_at ON subscriptions(created_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_expires_at ON subscriptions(expires_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_started_at ON subscriptions(started_at);

-- Композитные индексы для частых запросов
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status ON subscriptions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_expires ON subscriptions(user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status_expires ON subscriptions(status, expires_at);

-- Индекс для поиска истекающих подписок
CREATE INDEX IF NOT EXISTS idx_subscriptions_active_expiring ON subscriptions(status, expires_at) 
    WHERE status = 'active';

-- ==================== Таблица payments ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider);
CREATE INDEX IF NOT EXISTS idx_payments_transaction_id ON payments(transaction_id);

-- Индексы для временных запросов
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);
CREATE INDEX IF NOT EXISTS idx_payments_updated_at ON payments(updated_at);
CREATE INDEX IF NOT EXISTS idx_payments_paid_at ON payments(paid_at);

-- Композитные индексы
CREATE INDEX IF NOT EXISTS idx_payments_user_status ON payments(user_id, status);
CREATE INDEX IF NOT EXISTS idx_payments_user_created ON payments(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_payments_status_created ON payments(status, created_at);
CREATE INDEX IF NOT EXISTS idx_payments_provider_status ON payments(provider, status);

-- ==================== Таблица promo_codes ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
CREATE INDEX IF NOT EXISTS idx_promo_codes_is_active ON promo_codes(is_active);
CREATE INDEX IF NOT EXISTS idx_promo_codes_created_by ON promo_codes(created_by);

-- Индексы для временных запросов
CREATE INDEX IF NOT EXISTS idx_promo_codes_valid_from ON promo_codes(valid_from);
CREATE INDEX IF NOT EXISTS idx_promo_codes_valid_until ON promo_codes(valid_until);

-- Композитные индексы
CREATE INDEX IF NOT EXISTS idx_promo_codes_active_valid ON promo_codes(is_active, valid_from, valid_until);
CREATE INDEX IF NOT EXISTS idx_promo_codes_code_active ON promo_codes(code, is_active);

-- ==================== Таблица referrals ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(status);

-- Индексы для временных запросов
CREATE INDEX IF NOT EXISTS idx_referrals_created_at ON referrals(created_at);

-- Композитные индексы
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_status ON referrals(referrer_id, status);

-- ==================== Таблица user_balance ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_user_balance_user_id ON user_balance(user_id);
CREATE INDEX IF NOT EXISTS idx_user_balance_updated_at ON user_balance(updated_at);

-- ==================== Таблица transactions ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

-- Индексы для временных запросов
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- Композитные индексы
CREATE INDEX IF NOT EXISTS idx_transactions_user_type ON transactions(user_id, type);
CREATE INDEX IF NOT EXISTS idx_transactions_user_created ON transactions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_type_status ON transactions(type, status);

-- ==================== Таблица message_logs ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_message_logs_user_id ON message_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_message_logs_message_type ON message_logs(message_type);
CREATE INDEX IF NOT EXISTS idx_message_logs_created_at ON message_logs(created_at);

-- Композитные индексы
CREATE INDEX IF NOT EXISTS idx_message_logs_user_created ON message_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_message_logs_type_created ON message_logs(message_type, created_at);

-- ==================== Таблица ads ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_ads_is_active ON ads(is_active);
CREATE INDEX IF NOT EXISTS idx_ads_created_at ON ads(created_at);
CREATE INDEX IF NOT EXISTS idx_ads_priority ON ads(priority);

-- Композитные индексы
CREATE INDEX IF NOT EXISTS idx_ads_active_priority ON ads(is_active, priority);

-- ==================== Таблица panel_sync_log ====================

-- Основные индексы
CREATE INDEX IF NOT EXISTS idx_panel_sync_log_user_id ON panel_sync_log(user_id);
CREATE INDEX IF NOT EXISTS idx_panel_sync_log_sync_type ON panel_sync_log(sync_type);
CREATE INDEX IF NOT EXISTS idx_panel_sync_log_status ON panel_sync_log(status);
CREATE INDEX IF NOT EXISTS idx_panel_sync_log_created_at ON panel_sync_log(created_at);

-- Композитные индексы
CREATE INDEX IF NOT EXISTS idx_panel_sync_log_user_status ON panel_sync_log(user_id, status);
CREATE INDEX IF NOT EXISTS idx_panel_sync_log_type_created ON panel_sync_log(sync_type, created_at);

-- ==================== Таблица sessions ====================

-- Основные индексы (если таблица существует)
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);

-- Композитные индексы
CREATE INDEX IF NOT EXISTS idx_sessions_user_expires ON sessions(user_id, expires_at);

-- ==================== Анализ и обслуживание ====================

-- Обновление статистики для оптимизатора запросов
ANALYZE users;
ANALYZE subscriptions;
ANALYZE payments;
ANALYZE promo_codes;
ANALYZE referrals;
ANALYZE user_balance;
ANALYZE transactions;
ANALYZE message_logs;
ANALYZE ads;
ANALYZE panel_sync_log;

-- ==================== Комментарии ====================

COMMENT ON INDEX idx_users_telegram_id IS 'Быстрый поиск пользователя по Telegram ID';
COMMENT ON INDEX idx_subscriptions_user_status IS 'Оптимизация запросов подписок пользователя по статусу';
COMMENT ON INDEX idx_payments_user_status IS 'Оптимизация запросов платежей пользователя по статусу';
COMMENT ON INDEX idx_subscriptions_active_expiring IS 'Частичный индекс для поиска истекающих активных подписок';