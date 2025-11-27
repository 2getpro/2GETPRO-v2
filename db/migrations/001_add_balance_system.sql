-- Миграция 001: Добавление системы баланса и транзакций
-- Дата: 2025-11-27
-- Описание: Добавляет поля баланса в таблицу users и создает таблицу transactions

-- Добавление полей balance_kopeks и max_subscriptions_limit в таблицу users
ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_kopeks INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS max_subscriptions_limit INTEGER NOT NULL DEFAULT 1;

-- Создание таблицы transactions
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    amount_kopeks INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_transaction_type CHECK (
        transaction_type IN ('balance_add', 'balance_deduct', 'subscription_purchase', 'refund', 'gift_sent', 'gift_received')
    )
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);

-- Комментарии к таблице и полям
COMMENT ON TABLE transactions IS 'История транзакций пользователей';
COMMENT ON COLUMN transactions.amount_kopeks IS 'Сумма транзакции в копейках (может быть отрицательной для списаний)';
COMMENT ON COLUMN transactions.transaction_type IS 'Тип транзакции: balance_add, balance_deduct, subscription_purchase, refund, gift_sent, gift_received';
COMMENT ON COLUMN users.balance_kopeks IS 'Баланс пользователя в копейках';
COMMENT ON COLUMN users.max_subscriptions_limit IS 'Максимальное количество одновременных подписок';