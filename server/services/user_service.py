"""
用户服务
处理用户相关的业务逻辑
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from ..core.database import db_manager
from ..core.exceptions import ValidationError, BusinessRuleError, PermissionDeniedError
from ..models.user import User, UserUpdate

class UserService:
    """用户服务"""
    
    def __init__(self):
        self.db = db_manager
    
    def get_user_profile(self, user_id: int) -> Optional[User]:
        """获取用户资料"""
        with self.db.connection as conn:
            query = "SELECT * FROM users WHERE id = ?"
            result = conn.execute(query, [user_id]).fetchone()
            
            if result:
                user_data = dict(result)
                return User(
                    id=user_data["id"],
                    open_id=user_data["open_id"],
                    nickname=user_data.get("nickname"),
                    avatar=user_data.get("avatar"),
                    is_admin=user_data.get("is_admin", False),
                    balance_cents=user_data.get("balance_cents", 0),
                    created_at=user_data.get("created_at"),
                    updated_at=user_data.get("updated_at")
                )
            return None
    
    def update_user_profile(self, user_id: int, user_data: UserUpdate) -> User:
        """更新用户资料"""
        with self.db.transaction() as conn:
            # 构建更新查询
            update_fields = []
            params = []
            
            if user_data.nickname is not None:
                update_fields.append("nickname = ?")
                params.append(user_data.nickname)
            
            if user_data.avatar is not None:
                update_fields.append("avatar = ?")
                params.append(user_data.avatar)
            
            if update_fields:
                update_fields.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(user_id)
                
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
                conn.execute(query, params)
            
            return self.get_user_profile(user_id)
    
    def get_user_balance(self, user_id: int) -> int:
        """获取用户余额"""
        with self.db.connection as conn:
            query = "SELECT balance_cents FROM users WHERE id = ?"
            result = conn.execute(query, [user_id]).fetchone()
            return result["balance_cents"] if result else 0
    
    def get_user_order_history(
        self, 
        user_id: int, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取用户订单历史
        
        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期  
            status: 订单状态过滤
            limit: 每页数量
            offset: 偏移量
            
        Returns:
            包含订单列表和统计信息的字典
        """
        with self.db.connection as conn:
            # 构建查询条件
            where_conditions = ["o.user_id = ?"]
            params = [user_id]
            
            if start_date:
                where_conditions.append("m.date >= ?")
                params.append(start_date.isoformat())
                
            if end_date:
                where_conditions.append("m.date <= ?")
                params.append(end_date.isoformat())
                
            if status:
                where_conditions.append("o.status = ?")
                params.append(status)
            
            where_clause = " AND ".join(where_conditions)
            
            # 查询订单列表
            orders_query = f"""
            SELECT 
                o.order_id,
                o.meal_id,
                o.qty as quantity,
                o.options_json as selected_options,
                o.amount_cents as total_price_cents,
                o.status as order_status,
                o.created_at as order_time,
                o.updated_at as last_modified,
                m.date as meal_date,
                m.slot as meal_slot,
                m.title,
                m.description as meal_description,
                m.status as meal_status
            FROM orders o
            JOIN meals m ON o.meal_id = m.meal_id
            WHERE {where_clause}
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
            """
            
            orders = conn.execute(
                orders_query, 
                params + [limit, offset]
            ).fetchall()
            
            # 查询总数
            count_query = f"""
            SELECT COUNT(*) as total
            FROM orders o
            JOIN meals m ON o.meal_id = m.meal_id
            WHERE {where_clause}
            """
            
            total_count = conn.execute(count_query, params).fetchone()["total"]
            
            # 查询统计信息（不包含平均单次消费）
            stats = self._get_user_order_statistics(conn, user_id, start_date, end_date)
            
            return {
                "orders": [dict(order) for order in orders],
                "total_count": total_count,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(orders) < total_count
                },
                "statistics": stats
            }
    
    def _get_user_order_statistics(
        self, 
        conn, 
        user_id: int, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """获取用户订单统计信息"""
        
        # 基础查询条件
        where_conditions = ["o.user_id = ?"]
        params = [user_id]
        
        if start_date:
            where_conditions.append("m.date >= ?")
            params.append(start_date.isoformat())
            
        if end_date:
            where_conditions.append("m.date <= ?")
            params.append(end_date.isoformat())
        
        where_clause = " AND ".join(where_conditions)
        
        # 总体统计
        stats_query = f"""
        SELECT 
            COUNT(*) as total_orders,
            COALESCE(SUM(o.amount_cents), 0) as total_spent_cents,
            COALESCE(SUM(o.qty), 0) as total_meals,
            COUNT(DISTINCT m.date) as total_days
        FROM orders o
        JOIN meals m ON o.meal_id = m.meal_id
        WHERE {where_clause} AND o.status = 'active'
        """
        
        general_stats = dict(conn.execute(stats_query, params).fetchone())
        
        # 按状态统计
        status_query = f"""
        SELECT 
            o.status,
            COUNT(*) as count,
            COALESCE(SUM(o.amount_cents), 0) as total_cents
        FROM orders o
        JOIN meals m ON o.meal_id = m.meal_id
        WHERE {where_clause}
        GROUP BY o.status
        """
        
        status_stats = conn.execute(status_query, params).fetchall()
        
        # 按时段统计
        slot_query = f"""
        SELECT 
            m.slot,
            COUNT(*) as count,
            COALESCE(SUM(o.amount_cents), 0) as total_cents
        FROM orders o
        JOIN meals m ON o.meal_id = m.meal_id
        WHERE {where_clause} AND o.status = 'active'
        GROUP BY m.slot
        """
        
        slot_stats = conn.execute(slot_query, params).fetchall()
        
        # 最近30天趋势
        trend_query = f"""
        SELECT 
            m.date,
            COUNT(*) as orders_count,
            COALESCE(SUM(o.amount_cents), 0) as daily_spent_cents
        FROM orders o
        JOIN meals m ON o.meal_id = m.meal_id
        WHERE {where_clause} 
            AND o.status = 'active'
            AND m.date >= ?
        GROUP BY m.date
        ORDER BY m.date DESC
        LIMIT 30
        """
        
        trend_start = (datetime.now().date() - timedelta(days=30)).isoformat()
        trend_stats = conn.execute(
            trend_query, 
            params + [trend_start]
        ).fetchall()
        
        return {
            "general": general_stats,
            "by_status": [dict(row) for row in status_stats],
            "by_slot": [dict(row) for row in slot_stats], 
            "recent_trend": [dict(row) for row in trend_stats]
        }
    
    def get_user_balance_history(
        self, 
        user_id: int, 
        limit: int = 50, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """获取用户余额变动历史"""
        with self.db.connection as conn:
            # 查询余额变动记录
            history_query = """
            SELECT 
                ledger_id,
                user_id,
                amount_cents,
                remark as description,
                ref_id as related_order_id,
                type,
                created_at,
                (SELECT balance_cents FROM users WHERE id = l.user_id) as balance_after_cents
            FROM ledger l
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """
            
            history = conn.execute(history_query, [user_id, limit, offset]).fetchall()
            
            # 查询总数
            count_query = "SELECT COUNT(*) as total FROM ledger WHERE user_id = ?"
            total_count = conn.execute(count_query, [user_id]).fetchone()["total"]
            
            return {
                "history": [dict(record) for record in history],
                "total_count": total_count,
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(history) < total_count
                }
            }
    
    def get_user_profile_summary(self, user_id: int) -> Dict[str, Any]:
        """获取用户资料摘要"""
        with self.db.connection as conn:
            # 基本信息
            user_query = """
            SELECT id, open_id, nickname, avatar, 
                   balance_cents, is_admin, created_at
            FROM users WHERE id = ?
            """
            user_info = dict(conn.execute(user_query, [user_id]).fetchone())
            
            # 订单统计（最近30天）
            thirty_days_ago = (datetime.now().date() - timedelta(days=30)).isoformat()
            stats_query = """
            SELECT 
                COUNT(*) as recent_orders,
                COALESCE(SUM(o.amount_cents), 0) as recent_spent_cents,
                COUNT(DISTINCT m.date) as recent_meal_days
            FROM orders o
            JOIN meals m ON o.meal_id = m.meal_id
            WHERE o.user_id = ? 
                AND o.status = 'active'
                AND m.date >= ?
            """
            
            recent_stats = dict(conn.execute(
                stats_query, 
                [user_id, thirty_days_ago]
            ).fetchone())
            
            # 总计统计
            total_stats_query = """
            SELECT 
                COUNT(*) as total_orders,
                COALESCE(SUM(o.amount_cents), 0) as total_spent_cents
            FROM orders o
            WHERE o.user_id = ? AND o.status = 'active'
            """
            
            total_stats = dict(conn.execute(total_stats_query, [user_id]).fetchone())
            
            return {
                "user_info": user_info,
                "recent_activity": recent_stats,
                "lifetime_stats": total_stats
            }
    
    def recharge_balance(self, user_id: int, amount_cents: int, operator_id: int) -> Dict[str, Any]:
        """充值用户余额（管理员操作）"""
        with self.db.transaction() as conn:
            # 验证操作者权限
            if not self._is_admin(operator_id):
                raise PermissionDeniedError("需要管理员权限")
            
            # 验证充值金额
            if amount_cents <= 0:
                raise ValidationError("充值金额必须大于0")
            
            # 获取当前余额
            old_balance = self.get_user_balance(user_id)
            
            # 更新余额
            update_query = """
            UPDATE users 
            SET balance_cents = balance_cents + ?, updated_at = ?
            WHERE id = ?
            """
            conn.execute(update_query, [amount_cents, datetime.now().isoformat(), user_id])
            
            # 记录账单
            ledger_query = """
            INSERT INTO ledger (user_id, type, amount_cents, ref_type, remark, created_at)
            VALUES (?, 'recharge', ?, 'manual', ?, ?)
            """
            conn.execute(ledger_query, [
                user_id, 
                amount_cents, 
                f"管理员充值 - 操作员ID: {operator_id}",
                datetime.now().isoformat()
            ])
            
            # 记录操作日志
            import json
            log_query = """
            INSERT INTO logs (user_id, actor_id, action, detail_json, created_at)
            VALUES (?, ?, 'balance_recharge', ?, ?)
            """
            
            log_details = {
                "amount_cents": amount_cents,
                "old_balance_cents": old_balance,
                "new_balance_cents": old_balance + amount_cents,
                "operator_id": operator_id
            }
            
            conn.execute(log_query, [
                user_id,
                operator_id,
                json.dumps(log_details, ensure_ascii=False),
                datetime.now().isoformat()
            ])
            
            return {
                "success": True,
                "old_balance_cents": old_balance,
                "new_balance_cents": old_balance + amount_cents,
                "recharge_amount_cents": amount_cents
            }
    
    def _is_admin(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        with self.db.connection as conn:
            query = "SELECT is_admin FROM users WHERE id = ?"
            result = conn.execute(query, [user_id]).fetchone()
            return result and result["is_admin"]