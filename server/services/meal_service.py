"""
餐次服务
处理餐次的CRUD操作和状态管理
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from ..core.database import db_manager
from ..core.exceptions import ValidationError, BusinessRuleError, PermissionDeniedError
from ..models.meal import Meal, MealCreate, MealUpdate, MealStatus, MealSlot

class MealService:
    """餐次服务"""
    
    def __init__(self):
        self.db = db_manager
    
    def create_meal(self, meal_data: MealCreate, creator_id: int) -> Meal:
        """创建餐次"""
        with self.db.transaction() as conn:
            # 验证创建者权限
            if not self._is_admin(creator_id):
                raise PermissionDeniedError("需要管理员权限")
            
            # 验证日期时段唯一性
            if self._meal_exists(meal_data.date, meal_data.slot):
                raise BusinessRuleError("该日期时段已存在餐次")
            
            # 创建餐次
            meal_id = self._insert_meal(conn, meal_data, creator_id)
            
            # 记录日志
            self._log_meal_operation(conn, meal_id, "create", creator_id)
            
            return self.get_meal(meal_id)
    
    def update_meal_status(self, meal_id: int, status: str, operator_id: int) -> Meal:
        """更新餐次状态"""
        with self.db.transaction() as conn:
            # 验证权限
            if not self._is_admin(operator_id):
                raise PermissionDeniedError("需要管理员权限")
            
            # 验证状态转换
            current_meal = self.get_meal(meal_id)
            if not current_meal:
                raise ValidationError("餐次不存在")
                
            self._validate_status_transition(current_meal.status, status)
            
            # 更新状态
            self._update_meal_status(conn, meal_id, status)
            
            # 记录日志
            self._log_meal_operation(conn, meal_id, f"status_change_{status}", operator_id)
            
            return self.get_meal(meal_id)
    
    def get_meals_by_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """按日期范围获取餐次"""
        with self.db.connection as conn:
            query = """
            SELECT 
                m.*,
                COALESCE(SUM(o.qty), 0) as ordered_qty
            FROM meals m
            LEFT JOIN orders o ON m.meal_id = o.meal_id AND o.status = 'active'
            WHERE m.date >= ? AND m.date <= ?
            GROUP BY m.meal_id, m.date, m.slot, m.title, m.description, 
                     m.base_price_cents, m.capacity, m.status, m.created_by
            ORDER BY m.date, m.slot
            """
            
            results = conn.execute(query, [start_date.isoformat(), end_date.isoformat()]).fetchall()
            return [dict(row) for row in results]
    
    def get_meal(self, meal_id: int) -> Optional[Meal]:
        """获取单个餐次"""
        with self.db.connection as conn:
            query = """
            SELECT 
                m.*,
                COALESCE(SUM(o.qty), 0) as ordered_qty
            FROM meals m
            LEFT JOIN orders o ON m.meal_id = o.meal_id AND o.status = 'active'
            WHERE m.meal_id = ?
            GROUP BY m.meal_id, m.date, m.slot, m.title, m.description, 
                     m.base_price_cents, m.capacity, m.status, m.created_by
            """
            
            result = conn.execute(query, [meal_id]).fetchone()
            if result:
                meal_data = dict(result)
                
                # 解析options_json
                import json
                options = []
                if meal_data.get("options_json"):
                    try:
                        options = json.loads(meal_data["options_json"])
                    except (json.JSONDecodeError, TypeError):
                        options = []
                
                return Meal(
                    meal_id=meal_data["meal_id"],
                    date=meal_data["date"],
                    slot=meal_data["slot"],
                    title=meal_data.get("title"),
                    description=meal_data.get("description"),
                    base_price_cents=meal_data["base_price_cents"],
                    capacity=meal_data["capacity"],
                    per_user_limit=meal_data.get("per_user_limit", 1),
                    options=options,
                    status=meal_data["status"],
                    created_by=meal_data.get("created_by"),
                    ordered_qty=meal_data.get("ordered_qty", 0)
                )
            return None
    
    def _is_admin(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        with self.db.connection as conn:
            query = "SELECT is_admin FROM users WHERE id = ?"
            result = conn.execute(query, [user_id]).fetchone()
            return result and result["is_admin"]
    
    def _meal_exists(self, date: date, slot: str) -> bool:
        """检查餐次是否已存在"""
        with self.db.connection as conn:
            query = "SELECT COUNT(*) as count FROM meals WHERE date = ? AND slot = ?"
            result = conn.execute(query, [date.isoformat(), slot]).fetchone()
            return result["count"] > 0
    
    def _validate_status_transition(self, current_status: str, new_status: str):
        """验证状态转换是否合法"""
        valid_transitions = {
            'published': ['locked', 'canceled'],
            'locked': ['completed', 'canceled'],
            'completed': [],
            'canceled': []
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise BusinessRuleError(f"无法从 {current_status} 转换到 {new_status}")
    
    def _insert_meal(self, conn, meal_data: MealCreate, creator_id: int) -> int:
        """插入餐次数据"""
        import json
        
        options_json = json.dumps([option.dict() for option in meal_data.options]) if meal_data.options else None
        
        query = """
        INSERT INTO meals (
            date, slot, title, description, base_price_cents, 
            capacity, per_user_limit, options_json, status, 
            created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'published', ?, ?, ?)
        """
        
        now = datetime.now().isoformat()
        result = conn.execute(query, [
            meal_data.date.isoformat(),
            meal_data.slot.value,
            meal_data.title,
            meal_data.description,
            meal_data.base_price_cents,
            meal_data.capacity,
            meal_data.per_user_limit,
            options_json,
            creator_id,
            now,
            now
        ])
        
        # DuckDB 获取插入的ID
        meal_id_result = conn.execute("SELECT lastval()").fetchone()
        return meal_id_result[0] if meal_id_result else None
    
    def _update_meal_status(self, conn, meal_id: int, status: str):
        """更新餐次状态"""
        query = """
        UPDATE meals 
        SET status = ?, updated_at = ?
        WHERE meal_id = ?
        """
        
        conn.execute(query, [status, datetime.now().isoformat(), meal_id])
    
    def _log_meal_operation(self, conn, meal_id: int, operation: str, operator_id: int):
        """记录操作日志"""
        import json
        
        log_query = """
        INSERT INTO logs (user_id, actor_id, action, detail_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """
        
        details = {
            "meal_id": meal_id,
            "operation": operation
        }
        
        conn.execute(log_query, [
            None,  # user_id (餐次操作不针对特定用户)
            operator_id,
            f"meal_{operation}",
            json.dumps(details, ensure_ascii=False),
            datetime.now().isoformat()
        ])