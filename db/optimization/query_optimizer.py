"""
Оптимизатор SQL запросов.

Предоставляет инструменты для анализа и оптимизации запросов,
добавления индексов и мониторинга медленных запросов.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    Оптимизатор SQL запросов.
    
    Предоставляет методы для:
    - Добавления индексов
    - Анализа медленных запросов
    - Оптимизации запросов
    - Предложения улучшений
    """
    
    def __init__(self, engine: AsyncEngine):
        """
        Инициализация оптимизатора.
        
        Args:
            engine: AsyncEngine для выполнения запросов
        """
        self.engine = engine
        self.slow_query_threshold = 1.0  # секунды
    
    async def add_indexes(self, session: AsyncSession) -> bool:
        """
        Добавление всех индексов из indexes.sql.
        
        Args:
            session: Сессия базы данных
            
        Returns:
            True если успешно, False иначе
        """
        try:
            # Получаем путь к файлу indexes.sql
            current_dir = Path(__file__).parent
            indexes_file = current_dir / "indexes.sql"
            
            if not indexes_file.exists():
                logger.error(f"Файл индексов не найден: {indexes_file}")
                return False
            
            # Читаем SQL файл
            with open(indexes_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Выполняем SQL
            logger.info("Применение индексов из indexes.sql")
            await session.execute(text(sql_content))
            await session.commit()
            
            logger.info("Индексы успешно применены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка применения индексов: {e}", exc_info=True)
            await session.rollback()
            return False
    
    async def analyze_query(
        self,
        session: AsyncSession,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Анализ запроса с помощью EXPLAIN ANALYZE.
        
        Args:
            session: Сессия базы данных
            query: SQL запрос для анализа
            params: Параметры запроса
            
        Returns:
            Словарь с результатами анализа
        """
        try:
            # Добавляем EXPLAIN ANALYZE
            explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
            
            # Выполняем запрос
            result = await session.execute(
                text(explain_query),
                params or {}
            )
            
            # Получаем результат
            explain_result = result.fetchone()
            if explain_result:
                analysis = explain_result[0][0]  # JSON результат
                
                # Извлекаем ключевые метрики
                plan = analysis.get('Plan', {})
                execution_time = analysis.get('Execution Time', 0)
                planning_time = analysis.get('Planning Time', 0)
                
                return {
                    'execution_time': execution_time,
                    'planning_time': planning_time,
                    'total_time': execution_time + planning_time,
                    'plan': plan,
                    'full_analysis': analysis
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка анализа запроса: {e}", exc_info=True)
            return {}
    
    async def find_slow_queries(
        self,
        session: AsyncSession,
        threshold_ms: float = 1000.0
    ) -> List[Dict[str, Any]]:
        """
        Поиск медленных запросов в pg_stat_statements.
        
        Args:
            session: Сессия базы данных
            threshold_ms: Порог времени выполнения в миллисекундах
            
        Returns:
            Список медленных запросов
        """
        try:
            query = text("""
                SELECT 
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time,
                    stddev_exec_time,
                    rows
                FROM pg_stat_statements
                WHERE mean_exec_time > :threshold
                ORDER BY mean_exec_time DESC
                LIMIT 50
            """)
            
            result = await session.execute(query, {"threshold": threshold_ms})
            rows = result.fetchall()
            
            slow_queries = []
            for row in rows:
                slow_queries.append({
                    'query': row[0],
                    'calls': row[1],
                    'total_time': row[2],
                    'mean_time': row[3],
                    'max_time': row[4],
                    'stddev_time': row[5],
                    'rows': row[6]
                })
            
            logger.info(f"Найдено {len(slow_queries)} медленных запросов")
            return slow_queries
            
        except Exception as e:
            logger.warning(f"pg_stat_statements недоступен: {e}")
            return []
    
    async def suggest_indexes(
        self,
        session: AsyncSession,
        table_name: str
    ) -> List[str]:
        """
        Предложение индексов для таблицы.
        
        Args:
            session: Сессия базы данных
            table_name: Имя таблицы
            
        Returns:
            Список предложений по индексам
        """
        suggestions = []
        
        try:
            # Получаем информацию о таблице
            query = text("""
                SELECT 
                    a.attname as column_name,
                    t.typname as data_type,
                    a.attnotnull as not_null
                FROM pg_attribute a
                JOIN pg_type t ON a.atttypid = t.oid
                WHERE a.attrelid = :table_name::regclass
                AND a.attnum > 0
                AND NOT a.attisdropped
                ORDER BY a.attnum
            """)
            
            result = await session.execute(query, {"table_name": table_name})
            columns = result.fetchall()
            
            # Проверяем существующие индексы
            index_query = text("""
                SELECT 
                    i.relname as index_name,
                    a.attname as column_name
                FROM pg_index ix
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = ix.indrelid AND a.attnum = ANY(ix.indkey)
                WHERE ix.indrelid = :table_name::regclass
            """)
            
            index_result = await session.execute(index_query, {"table_name": table_name})
            existing_indexes = {row[1] for row in index_result.fetchall()}
            
            # Предлагаем индексы для часто используемых колонок
            common_index_columns = [
                'id', 'user_id', 'created_at', 'updated_at',
                'status', 'is_active', 'telegram_id'
            ]
            
            for column in columns:
                column_name = column[0]
                
                # Пропускаем, если индекс уже существует
                if column_name in existing_indexes:
                    continue
                
                # Предлагаем индекс для часто используемых колонок
                if column_name in common_index_columns:
                    suggestions.append(
                        f"CREATE INDEX idx_{table_name}_{column_name} "
                        f"ON {table_name}({column_name});"
                    )
                
                # Предлагаем индекс для внешних ключей
                if column_name.endswith('_id'):
                    suggestions.append(
                        f"CREATE INDEX idx_{table_name}_{column_name} "
                        f"ON {table_name}({column_name});"
                    )
            
            logger.info(f"Предложено {len(suggestions)} индексов для {table_name}")
            return suggestions
            
        except Exception as e:
            logger.error(f"Ошибка предложения индексов: {e}", exc_info=True)
            return []
    
    async def optimize_table(
        self,
        session: AsyncSession,
        table_name: str
    ) -> bool:
        """
        Оптимизация таблицы (VACUUM ANALYZE).
        
        Args:
            session: Сессия базы данных
            table_name: Имя таблицы
            
        Returns:
            True если успешно, False иначе
        """
        try:
            logger.info(f"Оптимизация таблицы {table_name}")
            
            # VACUUM ANALYZE нельзя выполнить в транзакции
            await session.commit()
            
            # Выполняем VACUUM ANALYZE
            await session.execute(text(f"VACUUM ANALYZE {table_name}"))
            
            logger.info(f"Таблица {table_name} оптимизирована")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка оптимизации таблицы {table_name}: {e}", exc_info=True)
            return False
    
    async def get_table_stats(
        self,
        session: AsyncSession,
        table_name: str
    ) -> Dict[str, Any]:
        """
        Получение статистики таблицы.
        
        Args:
            session: Сессия базы данных
            table_name: Имя таблицы
            
        Returns:
            Словарь со статистикой
        """
        try:
            query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE tablename = :table_name
            """)
            
            result = await session.execute(query, {"table_name": table_name})
            row = result.fetchone()
            
            if row:
                return {
                    'schema': row[0],
                    'table': row[1],
                    'inserts': row[2],
                    'updates': row[3],
                    'deletes': row[4],
                    'live_tuples': row[5],
                    'dead_tuples': row[6],
                    'last_vacuum': row[7],
                    'last_autovacuum': row[8],
                    'last_analyze': row[9],
                    'last_autoanalyze': row[10]
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики таблицы: {e}", exc_info=True)
            return {}
    
    async def optimize_all_tables(self, session: AsyncSession) -> Dict[str, bool]:
        """
        Оптимизация всех таблиц.
        
        Args:
            session: Сессия базы данных
            
        Returns:
            Словарь {table_name: success}
        """
        tables = [
            'users', 'subscriptions', 'payments', 'promo_codes',
            'referrals', 'user_balance', 'transactions', 'message_logs',
            'ads', 'panel_sync_log'
        ]
        
        results = {}
        for table in tables:
            results[table] = await self.optimize_table(session, table)
        
        return results