"""
数据一致性检查和修复服务
提供数据完整性检查和问题修复功能，确保系统数据的一致性
Phase 2 功能增强
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from ..core.database import db_manager
from ..core.exceptions import ValidationError, PermissionDeniedError


class ConsistencyCheckResult:
    """一致性检查结果"""
    
    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {}
    
    def add_issue(self, issue_type: str, description: str, details: Dict[str, Any] = None):
        """添加问题"""
        self.issues.append({
            'type': issue_type,
            'description': description,
            'details': details or {},
            'severity': 'error',
            'timestamp': datetime.now().isoformat()
        })
    
    def add_warning(self, warning_type: str, description: str, details: Dict[str, Any] = None):
        """添加警告"""
        self.warnings.append({
            'type': warning_type,
            'description': description,
            'details': details or {},
            'severity': 'warning',
            'timestamp': datetime.now().isoformat()
        })
    
    def set_statistics(self, stats: Dict[str, Any]):
        """设置统计信息"""
        self.statistics = stats
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'issues': self.issues,
            'warnings': self.warnings,
            'statistics': self.statistics,
            'summary': {
                'total_issues': len(self.issues),
                'total_warnings': len(self.warnings),
                'status': 'healthy' if len(self.issues) == 0 else 'issues_found',
                'checked_at': datetime.now().isoformat()
            }
        }


class ConsistencyService:
    """数据一致性服务"""
    
    def __init__(self):
        self.db = db_manager
    
    def check_data_consistency(self, operator_id: int, include_warnings: bool = True) -> Dict[str, Any]:
        """
        全面的数据一致性检查
        
        Args:
            operator_id: 操作员ID
            include_warnings: 是否包含警告信息
        
        Returns:
            检查结果字典
        """
        # 验证权限
        if not self._is_admin(operator_id):
            raise PermissionDeniedError("需要管理员权限")
        
        result = ConsistencyCheckResult()
        
        with self.db.connection as conn:
            # 基础统计信息
            stats = self._collect_basic_statistics(conn)
            result.set_statistics(stats)
            
            # 检查用户余额一致性
            self._check_user_balance_consistency(conn, result)
            
            # 检查订单状态一致性
            self._check_order_consistency(conn, result)
            
            # 检查餐次容量一致性
            self._check_meal_capacity_consistency(conn, result)
            
            # 检查账本记录完整性
            self._check_ledger_integrity(conn, result)
            
            # 检查孤儿数据
            self._check_orphaned_data(conn, result)
            
            if include_warnings:
                # 检查潜在问题（警告级别）
                self._check_potential_issues(conn, result)
        
        # 记录检查日志
        self._log_consistency_check(operator_id, result)
        
        return result.to_dict()
    
    def _collect_basic_statistics(self, conn) -> Dict[str, Any]:
        """收集基础统计信息"""
        stats = {}
        
        # 用户统计
        users_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN is_admin THEN 1 END) as admin_users,
                SUM(balance_cents) as total_balance_cents,
                MIN(balance_cents) as min_balance_cents,
                MAX(balance_cents) as max_balance_cents
            FROM users
        """).fetchone()
        
        stats['users'] = {
            'total': users_stats[0],
            'admins': users_stats[1],
            'total_balance_cents': users_stats[2] or 0,
            'min_balance_cents': users_stats[3] or 0,
            'max_balance_cents': users_stats[4] or 0
        }
        
        # 餐次统计
        meals_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_meals,
                COUNT(CASE WHEN status = 'published' THEN 1 END) as published_meals,
                COUNT(CASE WHEN status = 'locked' THEN 1 END) as locked_meals,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_meals,
                COUNT(CASE WHEN status = 'canceled' THEN 1 END) as canceled_meals
            FROM meals
        """).fetchone()
        
        stats['meals'] = {
            'total': meals_stats[0],
            'published': meals_stats[1],
            'locked': meals_stats[2],
            'completed': meals_stats[3],
            'canceled': meals_stats[4]
        }
        
        # 订单统计
        orders_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_orders,
                COUNT(CASE WHEN status = 'canceled' THEN 1 END) as canceled_orders,
                SUM(amount_cents) as total_order_amount_cents
            FROM orders
        """).fetchone()
        
        stats['orders'] = {
            'total': orders_stats[0],
            'active': orders_stats[1],
            'canceled': orders_stats[2],
            'total_amount_cents': orders_stats[3] or 0
        }
        
        # 账本统计
        ledger_stats = conn.execute("""
            SELECT 
                COUNT(*) as total_entries,
                SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END) as total_credits,
                SUM(CASE WHEN amount_cents < 0 THEN ABS(amount_cents) ELSE 0 END) as total_debits
            FROM ledger
        """).fetchone()
        
        stats['ledger'] = {
            'total_entries': ledger_stats[0],
            'total_credits': ledger_stats[1] or 0,
            'total_debits': ledger_stats[2] or 0
        }
        
        return stats
    
    def _check_user_balance_consistency(self, conn, result: ConsistencyCheckResult):
        """检查用户余额一致性"""
        # 检查用户余额与账本记录是否一致
        balance_check = conn.execute("""
            SELECT 
                u.id,
                u.open_id,
                u.nickname,
                u.balance_cents as user_balance,
                COALESCE(SUM(l.amount_cents), 0) as ledger_balance
            FROM users u
            LEFT JOIN ledger l ON u.id = l.user_id
            GROUP BY u.id, u.open_id, u.nickname, u.balance_cents
            HAVING u.balance_cents != COALESCE(SUM(l.amount_cents), 0)
        """).fetchall()
        
        for row in balance_check:
            result.add_issue(
                'balance_mismatch',
                f"用户 {row[2] or row[1][-8:]} 的余额不一致",
                {
                    'user_id': row[0],
                    'user_balance_cents': row[3],
                    'ledger_balance_cents': row[4],
                    'difference_cents': row[3] - row[4]
                }
            )
    
    def _check_order_consistency(self, conn, result: ConsistencyCheckResult):
        """检查订单状态一致性"""
        # 检查孤儿订单（引用不存在的餐次或用户）
        orphaned_orders = conn.execute("""
            SELECT o.order_id, o.user_id, o.meal_id, 'missing_meal' as issue_type
            FROM orders o
            LEFT JOIN meals m ON o.meal_id = m.meal_id
            WHERE m.meal_id IS NULL
            
            UNION ALL
            
            SELECT o.order_id, o.user_id, o.meal_id, 'missing_user' as issue_type
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE u.id IS NULL
        """).fetchall()
        
        for row in orphaned_orders:
            result.add_issue(
                'orphaned_order',
                f"订单 {row[0]} 引用了不存在的{'餐次' if row[3] == 'missing_meal' else '用户'}",
                {
                    'order_id': row[0],
                    'user_id': row[1],
                    'meal_id': row[2],
                    'issue_type': row[3]
                }
            )
        
        # 检查重复订单（同一用户同一餐次多个活跃订单）
        duplicate_orders = conn.execute("""
            SELECT user_id, meal_id, COUNT(*) as count
            FROM orders
            WHERE status = 'active'
            GROUP BY user_id, meal_id
            HAVING COUNT(*) > 1
        """).fetchall()
        
        for row in duplicate_orders:
            result.add_issue(
                'duplicate_orders',
                f"用户 {row[0]} 在餐次 {row[1]} 有 {row[2]} 个活跃订单",
                {
                    'user_id': row[0],
                    'meal_id': row[1],
                    'duplicate_count': row[2]
                }
            )
    
    def _check_meal_capacity_consistency(self, conn, result: ConsistencyCheckResult):
        """检查餐次容量一致性"""
        capacity_issues = conn.execute("""
            SELECT 
                m.meal_id,
                m.date,
                m.slot,
                m.capacity,
                COALESCE(SUM(o.qty), 0) as ordered_qty
            FROM meals m
            LEFT JOIN orders o ON m.meal_id = o.meal_id AND o.status = 'active'
            GROUP BY m.meal_id, m.date, m.slot, m.capacity
            HAVING COALESCE(SUM(o.qty), 0) > m.capacity
        """).fetchall()
        
        for row in capacity_issues:
            result.add_issue(
                'capacity_exceeded',
                f"餐次 {row[1]} {row[2]} 超出容量限制",
                {
                    'meal_id': row[0],
                    'date': str(row[1]),
                    'slot': row[2],
                    'capacity': row[3],
                    'ordered_qty': row[4],
                    'excess': row[4] - row[3]
                }
            )
    
    def _check_ledger_integrity(self, conn, result: ConsistencyCheckResult):
        """检查账本记录完整性"""
        # 检查订单是否有对应的账本记录
        missing_ledger = conn.execute("""
            SELECT o.order_id, o.user_id, o.amount_cents
            FROM orders o
            LEFT JOIN ledger l ON o.order_id = l.ref_id AND l.ref_type = 'order' AND l.type = 'debit'
            WHERE o.status = 'active' AND l.ledger_id IS NULL
        """).fetchall()
        
        for row in missing_ledger:
            result.add_issue(
                'missing_ledger_entry',
                f"订单 {row[0]} 缺少对应的账本扣费记录",
                {
                    'order_id': row[0],
                    'user_id': row[1],
                    'amount_cents': row[2]
                }
            )
    
    def _check_orphaned_data(self, conn, result: ConsistencyCheckResult):
        """检查孤儿数据"""
        # 检查没有关联对象的账本记录
        orphaned_ledger = conn.execute("""
            SELECT l.ledger_id, l.ref_type, l.ref_id
            FROM ledger l
            LEFT JOIN orders o ON l.ref_type = 'order' AND l.ref_id = o.order_id
            LEFT JOIN meals m ON l.ref_type = 'meal' AND l.ref_id = m.meal_id
            WHERE l.ref_type IN ('order', 'meal') 
                AND l.ref_id IS NOT NULL 
                AND o.order_id IS NULL 
                AND m.meal_id IS NULL
        """).fetchall()
        
        for row in orphaned_ledger:
            result.add_warning(
                'orphaned_ledger_entry',
                f"账本记录 {row[0]} 引用了不存在的{row[1]}",
                {
                    'ledger_id': row[0],
                    'ref_type': row[1],
                    'ref_id': row[2]
                }
            )
    
    def _check_potential_issues(self, conn, result: ConsistencyCheckResult):
        """检查潜在问题（警告级别）"""
        # 检查负余额用户
        negative_balance_users = conn.execute("""
            SELECT id, open_id, nickname, balance_cents
            FROM users
            WHERE balance_cents < 0
            ORDER BY balance_cents ASC
            LIMIT 10
        """).fetchall()
        
        for row in negative_balance_users:
            result.add_warning(
                'negative_balance',
                f"用户 {row[2] or row[1][-8:]} 余额为负数",
                {
                    'user_id': row[0],
                    'balance_cents': row[3]
                }
            )
        
        # 检查长时间未更新的已发布餐次
        stale_meals = conn.execute("""
            SELECT meal_id, date, slot, created_at
            FROM meals
            WHERE status = 'published' 
                AND date < CURRENT_DATE - INTERVAL '7 days'
            ORDER BY date ASC
            LIMIT 5
        """).fetchall()
        
        for row in stale_meals:
            result.add_warning(
                'stale_published_meal',
                f"餐次 {row[1]} {row[2]} 已过期但仍处于发布状态",
                {
                    'meal_id': row[0],
                    'date': str(row[1]),
                    'slot': row[2],
                    'created_at': str(row[3])
                }
            )
    
    def fix_balance_inconsistency(self, user_id: int, operator_id: int) -> Dict[str, Any]:
        """修复用户余额不一致问题"""
        if not self._is_admin(operator_id):
            raise PermissionDeniedError("需要管理员权限")
        
        with self.db.transaction() as conn:
            # 计算正确的余额
            correct_balance = conn.execute(
                "SELECT COALESCE(SUM(amount_cents), 0) FROM ledger WHERE user_id = ?",
                [user_id]
            ).fetchone()[0]
            
            # 获取当前余额
            current_balance = conn.execute(
                "SELECT balance_cents FROM users WHERE id = ?",
                [user_id]
            ).fetchone()
            
            if not current_balance:
                raise ValidationError("用户不存在")
            
            current_balance = current_balance[0]
            
            if current_balance != correct_balance:
                # 更新用户余额
                conn.execute(
                    "UPDATE users SET balance_cents = ? WHERE id = ?",
                    [correct_balance, user_id]
                )
                
                # 记录修复日志
                log_details = {
                    "action": "balance_fix",
                    "user_id": user_id,
                    "old_balance_cents": current_balance,
                    "correct_balance_cents": correct_balance,
                    "difference_cents": correct_balance - current_balance,
                    "operator_id": operator_id
                }
                
                conn.execute(
                    "INSERT INTO logs(user_id, actor_id, action, detail_json) VALUES (?,?,?,?)",
                    [user_id, operator_id, "consistency_fix", json.dumps(log_details)]
                )
                
                return {
                    "fixed": True,
                    "old_balance_cents": current_balance,
                    "new_balance_cents": correct_balance,
                    "difference_cents": correct_balance - current_balance
                }
            else:
                return {"fixed": False, "message": "余额已一致，无需修复"}
    
    def _log_consistency_check(self, operator_id: int, result: ConsistencyCheckResult):
        """记录一致性检查日志"""
        with self.db.connection as conn:
            log_details = {
                "action": "consistency_check",
                "total_issues": len(result.issues),
                "total_warnings": len(result.warnings),
                "statistics": result.statistics,
                "operator_id": operator_id
            }
            
            conn.execute(
                "INSERT INTO logs(actor_id, action, detail_json) VALUES (?,?,?)",
                [operator_id, "consistency_check", json.dumps(log_details)]
            )
    
    def _is_admin(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        with self.db.connection as conn:
            query = "SELECT is_admin FROM users WHERE id = ?"
            result = conn.execute(query, [user_id]).fetchone()
            return result and result[0]


# 全局服务实例
consistency_service = ConsistencyService()