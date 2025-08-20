# Phase 2: 功能完善详细执行方案（已调整）

## 概述
Phase 2 专注于完善核心业务功能，补全缺失的功能模块，并处理各种边界场景。目标是让系统功能更加完整和健壮。

## 调整说明
根据需求调整了以下内容：
- **移除订单修改时间窗口限制**：只要管理员没有锁定且餐次没结束，订单都可以修改
- **简化余额验证**：余额不足时仅提示但不阻止下单，允许负余额（面向熟人内部系统）
- **移除平均单次消费统计**：在用户统计和导出功能中移除此指标
- **移除自动重试机制**：操作失败时直接提示失败，等用户/管理员决定是否重试

## 执行时间线: 第3-4周

---

## Week 3: 核心功能增强

### Day 1-2: 用户系统完善

#### 目标
完善用户相关功能，特别是订单历史查询和个人信息管理。

#### 具体操作

##### 1. 增强用户订单历史功能

**修改文件: `server/services/user_service.py`**
```python
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from ..core.database import db_manager
from ..core.exceptions import ValidationError, BusinessRuleError
from ..models.user import User, UserUpdate

class UserService:
    """用户服务 - 增强版"""
    
    def __init__(self):
        self.db = db_manager
    
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
                o.quantity,
                o.selected_options,
                o.total_price_cents,
                o.status as order_status,
                o.created_at as order_time,
                m.date as meal_date,
                m.slot as meal_slot,
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
            
            total_count = conn.execute(count_query, params).fetchone()['total']
            
            # 查询统计信息
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
            COALESCE(SUM(o.total_price_cents), 0) as total_spent_cents,
            COALESCE(SUM(o.quantity), 0) as total_meals,
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
            COALESCE(SUM(o.total_price_cents), 0) as total_cents
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
            COALESCE(SUM(o.total_price_cents), 0) as total_cents
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
            COALESCE(SUM(o.total_price_cents), 0) as daily_spent_cents
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
                description,
                related_order_id,
                created_at,
                balance_after_cents
            FROM ledger
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """
            
            history = conn.execute(history_query, [user_id, limit, offset]).fetchall()
            
            # 查询总数
            count_query = "SELECT COUNT(*) as total FROM ledger WHERE user_id = ?"
            total_count = conn.execute(count_query, [user_id]).fetchone()['total']
            
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
            SELECT user_id, openid, nickname, avatar_url, 
                   balance_cents, is_admin, created_at
            FROM users WHERE user_id = ?
            """
            user_info = dict(conn.execute(user_query, [user_id]).fetchone())
            
            # 订单统计（最近30天）
            thirty_days_ago = (datetime.now().date() - timedelta(days=30)).isoformat()
            stats_query = """
            SELECT 
                COUNT(*) as recent_orders,
                COALESCE(SUM(o.total_price_cents), 0) as recent_spent_cents,
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
                COALESCE(SUM(o.total_price_cents), 0) as total_spent_cents
            FROM orders o
            WHERE o.user_id = ? AND o.status = 'active'
            """
            
            total_stats = dict(conn.execute(total_stats_query, [user_id]).fetchone())
            
            return {
                "user_info": user_info,
                "recent_activity": recent_stats,
                "lifetime_stats": total_stats
            }
```

##### 2. 新增用户相关API路由

**修改文件: `server/api/v1/users.py`**
```python
from fastapi import APIRouter, Depends, Query
from datetime import date
from typing import Optional
from ...services.user_service import UserService
from ...services.auth_service import AuthService
from ...core.exceptions import PermissionDeniedError

router = APIRouter()

@router.get("/profile")
async def get_user_profile(
    current_user_id: int = Depends(get_current_user_id)
):
    """获取用户资料摘要"""
    user_service = UserService()
    return user_service.get_user_profile_summary(current_user_id)

@router.get("/orders/history")
async def get_order_history(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    status: Optional[str] = Query(None, description="订单状态"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取用户订单历史"""
    user_service = UserService()
    return user_service.get_user_order_history(
        user_id=current_user_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        limit=limit,
        offset=offset
    )

@router.get("/balance/history")
async def get_balance_history(
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user_id: int = Depends(get_current_user_id)
):
    """获取余额变动历史"""
    user_service = UserService()
    return user_service.get_user_balance_history(
        user_id=current_user_id,
        limit=limit,
        offset=offset
    )

@router.post("/balance/recharge")
async def recharge_balance(
    user_id: int,
    amount_cents: int,
    current_user_id: int = Depends(get_current_user_id),
    is_admin: bool = Depends(check_admin_permission)
):
    """充值用户余额（管理员操作）"""
    if not is_admin:
        raise PermissionDeniedError("需要管理员权限")
    
    user_service = UserService()
    return user_service.recharge_balance(user_id, amount_cents, current_user_id)
```

##### 3. 前端个人中心页面增强

**修改文件: `client/miniprogram/pages/profile/profile.ts`**
```typescript
/**
 * 个人中心页面 - 增强版
 */
import { UserAPI } from '../../core/api/user';
import { ThemeStore } from '../../core/store/theme';
import { AuthStore } from '../../core/store/auth';
import { formatCurrency, formatDate } from '../../core/utils/format';

Page({
  data: {
    userInfo: null,
    userStats: null,
    balanceHistory: [],
    orderHistory: [],
    theme: null,
    loading: true,
    
    // 标签页状态
    activeTab: 'overview', // overview, orders, balance
    
    // 分页状态
    orderPage: { limit: 20, offset: 0, hasMore: true },
    balancePage: { limit: 20, offset: 0, hasMore: true }
  },

  onLoad() {
    this.initPage();
  },

  onShow() {
    this.refreshData();
  },

  onPullDownRefresh() {
    this.refreshData().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onReachBottom() {
    this.loadMoreData();
  },

  async initPage() {
    // 初始化主题
    const theme = ThemeStore.getCurrentTheme();
    this.setData({ theme });

    // 订阅主题变化
    ThemeStore.subscribeThemeChange((newTheme) => {
      this.setData({ theme: newTheme });
    });

    await this.refreshData();
  },

  async refreshData() {
    try {
      this.setData({ loading: true });

      // 并行加载数据
      const [profileResult, orderResult, balanceResult] = await Promise.all([
        this.loadUserProfile(),
        this.loadOrderHistory(true),
        this.loadBalanceHistory(true)
      ]);

      this.setData({
        loading: false
      });

    } catch (error) {
      console.error('加载用户数据失败:', error);
      this.setData({ loading: false });
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      });
    }
  },

  async loadUserProfile() {
    const result = await UserAPI.getUserProfile();
    if (result.success) {
      this.setData({
        userInfo: result.data.user_info,
        userStats: {
          recent: result.data.recent_activity,
          lifetime: result.data.lifetime_stats
        }
      });
      
      // 更新全局用户信息
      AuthStore.updateBalance(result.data.user_info.balance_cents);
    }
    return result;
  },

  async loadOrderHistory(refresh = false) {
    const { orderPage } = this.data;
    
    if (refresh) {
      orderPage.offset = 0;
      orderPage.hasMore = true;
    }

    if (!orderPage.hasMore) return;

    const result = await UserAPI.getOrderHistory({
      limit: orderPage.limit,
      offset: orderPage.offset
    });

    if (result.success) {
      const newOrders = result.data.orders;
      const existingOrders = refresh ? [] : this.data.orderHistory;
      
      this.setData({
        orderHistory: [...existingOrders, ...newOrders],
        orderPage: {
          ...orderPage,
          offset: orderPage.offset + newOrders.length,
          hasMore: result.data.page_info.has_more
        }
      });
    }

    return result;
  },

  async loadBalanceHistory(refresh = false) {
    const { balancePage } = this.data;
    
    if (refresh) {
      balancePage.offset = 0;
      balancePage.hasMore = true;
    }

    if (!balancePage.hasMore) return;

    const result = await UserAPI.getBalanceHistory({
      limit: balancePage.limit,
      offset: balancePage.offset
    });

    if (result.success) {
      const newHistory = result.data.history;
      const existingHistory = refresh ? [] : this.data.balanceHistory;
      
      this.setData({
        balanceHistory: [...existingHistory, ...newHistory],
        balancePage: {
          ...balancePage,
          offset: balancePage.offset + newHistory.length,
          hasMore: result.data.page_info.has_more
        }
      });
    }

    return result;
  },

  async loadMoreData() {
    if (this.data.loading) return;

    switch (this.data.activeTab) {
      case 'orders':
        await this.loadOrderHistory(false);
        break;
      case 'balance':
        await this.loadBalanceHistory(false);
        break;
    }
  },

  onTabSwitch(e: any) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({ activeTab: tab });

    // 懒加载数据
    if (tab === 'orders' && this.data.orderHistory.length === 0) {
      this.loadOrderHistory(true);
    } else if (tab === 'balance' && this.data.balanceHistory.length === 0) {
      this.loadBalanceHistory(true);
    }
  },

  onToggleTheme() {
    ThemeStore.toggleTheme();
  },

  onViewOrderDetail(e: any) {
    const orderId = e.currentTarget.dataset.orderId;
    wx.navigateTo({
      url: `/pages/order/detail?orderId=${orderId}`
    });
  },

  onExportData() {
    wx.showActionSheet({
      itemList: ['导出订单历史', '导出余额记录'],
      success: (res) => {
        if (res.tapIndex === 0) {
          this.exportOrderHistory();
        } else if (res.tapIndex === 1) {
          this.exportBalanceHistory();
        }
      }
    });
  },

  async exportOrderHistory() {
    // 实现订单历史导出
    wx.showLoading({ title: '导出中...' });
    
    try {
      const result = await UserAPI.exportOrderHistory();
      if (result.success) {
        // 下载或分享文件
        wx.showToast({
          title: '导出成功',
          icon: 'success'
        });
      }
    } catch (error) {
      wx.showToast({
        title: '导出失败',
        icon: 'error'
      });
    } finally {
      wx.hideLoading();
    }
  },

  async exportBalanceHistory() {
    // 实现余额历史导出
    wx.showLoading({ title: '导出中...' });
    
    try {
      const result = await UserAPI.exportBalanceHistory();
      if (result.success) {
        wx.showToast({
          title: '导出成功',
          icon: 'success'
        });
      }
    } catch (error) {
      wx.showToast({
        title: '导出失败',
        icon: 'error'
      });
    } finally {
      wx.hideLoading();
    }
  },

  onShareProfile() {
    return {
      title: '我的罡好饭账户',
      path: '/pages/index/index'
    };
  }
});
```

### Day 3-4: 订单系统优化

#### 目标
细化订单状态管理，实现订单修改时间窗口控制和批量处理功能。

#### 具体操作

##### 1. 简化订单状态系统

**修改文件: `server/models/order.py`**
```python
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from .base import BaseModel as AppBaseModel, TimestampMixin

class OrderStatus:
    """订单状态常量"""
    ACTIVE = "active"           # 活跃订单（可修改/取消）
    LOCKED = "locked"           # 锁定订单（不可修改，但有效）
    COMPLETED = "completed"     # 已完成
    CANCELED = "canceled"       # 已取消（用户操作）
    REFUNDED = "refunded"       # 已退款（系统/管理员操作）
    
    @classmethod
    def get_transitions(cls) -> dict:
        """获取状态流转关系"""
        return {
            cls.ACTIVE: [cls.LOCKED, cls.CANCELED, cls.REFUNDED],
            cls.LOCKED: [cls.ACTIVE, cls.COMPLETED, cls.REFUNDED],
            cls.COMPLETED: [],  # 终态
            cls.CANCELED: [],   # 终态
            cls.REFUNDED: []    # 终态
        }
    
    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """检查状态是否可以流转"""
        transitions = cls.get_transitions()
        return to_status in transitions.get(from_status, [])

class OrderBase(BaseModel):
    meal_id: int
    quantity: int = 1
    selected_options: List[Dict[str, Any]] = []
    total_price_cents: int
    notes: Optional[str] = None  # 新增：订单备注

class OrderCreate(OrderBase):
    """订单创建模型"""
    pass

class OrderUpdate(BaseModel):
    """订单更新模型"""
    quantity: Optional[int] = None
    selected_options: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None

class OrderModify(BaseModel):
    """订单修改模型（用于原子性修改）"""
    new_quantity: int
    new_selected_options: List[Dict[str, Any]] = []
    new_notes: Optional[str] = None

class Order(OrderBase, TimestampMixin):
    """完整订单模型"""
    order_id: int
    user_id: int
    status: str = OrderStatus.ACTIVE
    
    class Config:
        from_attributes = True

class OrderBatch(BaseModel):
    """批量订单操作模型"""
    order_ids: List[int]
    action: str  # 'complete', 'cancel', 'refund'
    reason: Optional[str] = None
```

##### 2. 增强订单服务

**修改文件: `server/services/order_service.py`**
```python
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from ..core.database import db_manager
from ..core.exceptions import *
from ..models.order import Order, OrderCreate, OrderUpdate, OrderModify, OrderBatch, OrderStatus
from ..models.meal import Meal

class OrderService:
    """订单服务 - 增强版"""
    
    def __init__(self):
        self.db = db_manager
        # 订单修改窗口（发布后2小时内可修改）
        self.modify_window_hours = 2
    
    def create_order(self, order_data: OrderCreate, user_id: int) -> Order:
        """创建订单 - 简化版本"""
        with self.db.transaction() as conn:
            # 获取餐次信息（加锁）
            meal = self._get_meal_with_lock(conn, order_data.meal_id)
            
            # 验证餐次状态和时间窗口
            self._validate_meal_for_ordering(meal)
            
            # 验证容量限制
            if self._check_capacity_exceeded(conn, order_data.meal_id, order_data.quantity):
                raise MealCapacityExceededError("餐次容量不足")
            
            # 验证用户订单限制
            existing_order = self._get_user_order_for_meal(conn, user_id, order_data.meal_id)
            if existing_order:
                raise BusinessRuleError("用户已有该餐次的订单，请先取消现有订单")
            
            # 计算总价
            total_price = self._calculate_total_price(meal, order_data)
            order_data.total_price_cents = total_price
            
            # 检查余额（仅提示，不阻止下单）
            current_balance = self._get_user_balance(conn, user_id)
            if current_balance < total_price:
                # 记录负余额警告日志，但允许继续下单
                self._log_order_operation(conn, None, "negative_balance_warning", user_id, {
                    "current_balance": current_balance,
                    "order_amount": total_price,
                    "deficit": total_price - current_balance
                })
            
            # 创建订单
            order_id = self._insert_order(conn, order_data, user_id)
            
            # 扣除余额（允许负余额）
            self._deduct_balance(conn, user_id, total_price, order_id)
            
            # 记录日志
            self._log_order_operation(conn, order_id, "create", user_id, {
                "meal_id": order_data.meal_id,
                "quantity": order_data.quantity,
                "total_price_cents": total_price
            })
            
            return self.get_order(order_id)
    
    def modify_order_atomic(self, order_id: int, modify_data: OrderModify, user_id: int) -> Order:
        """原子性修改订单（简化条件）"""
        with self.db.transaction() as conn:
            # 获取现有订单
            existing_order = self._get_order_with_lock(conn, order_id)
            
            # 验证权限
            if existing_order['user_id'] != user_id:
                raise PermissionDeniedError("无权限修改此订单")
            
            # 获取餐次信息
            meal = self._get_meal_with_lock(conn, existing_order['meal_id'])
            
            # 验证修改条件：只要管理员没有锁定且餐次没结束即可修改
            if meal['status'] not in ['published']:
                raise BusinessRuleError("餐次已结束或取消，无法修改订单")
            
            # 计算新的总价
            new_total_price = self._calculate_total_price_for_modify(meal, modify_data)
            price_difference = new_total_price - existing_order['total_price_cents']
            
            # 验证容量（考虑当前订单释放的容量）
            capacity_change = modify_data.new_quantity - existing_order['quantity']
            if capacity_change > 0:
                available_capacity = self._get_available_capacity(conn, meal['meal_id'])
                if capacity_change > available_capacity:
                    raise MealCapacityExceededError("容量不足，无法增加数量")
            
            # 执行修改
            self._update_order(conn, order_id, {
                'quantity': modify_data.new_quantity,
                'selected_options': modify_data.new_selected_options,
                'total_price_cents': new_total_price,
                'notes': modify_data.new_notes,
                'updated_at': datetime.now()
            })
            
            # 处理余额变化（允许负余额）
            if price_difference != 0:
                if price_difference > 0:
                    # 额外扣费
                    self._deduct_balance(conn, user_id, price_difference, order_id, "订单修改额外费用")
                else:
                    # 退款
                    self._refund_balance(conn, user_id, abs(price_difference), order_id, "订单修改退款")
            
            # 记录日志
            self._log_order_operation(conn, order_id, "modify", user_id, {
                "old_quantity": existing_order['quantity'],
                "new_quantity": modify_data.new_quantity,
                "price_difference_cents": price_difference,
                "old_total_price_cents": existing_order['total_price_cents'],
                "new_total_price_cents": new_total_price
            })
            
            return self.get_order(order_id)
    
    def batch_process_orders(self, batch_data: OrderBatch, operator_id: int) -> Dict[str, Any]:
        """批量处理订单（管理员功能）"""
        with self.db.transaction() as conn:
            # 验证管理员权限
            if not self._is_admin(operator_id):
                raise PermissionDeniedError("需要管理员权限")
            
            results = {
                "success_count": 0,
                "failed_count": 0,
                "details": []
            }
            
            for order_id in batch_data.order_ids:
                try:
                    if batch_data.action == "complete":
                        self._complete_order(conn, order_id, operator_id, batch_data.reason)
                    elif batch_data.action == "cancel":
                        self._cancel_order_admin(conn, order_id, operator_id, batch_data.reason)
                    elif batch_data.action == "refund":
                        self._refund_order(conn, order_id, operator_id, batch_data.reason)
                    else:
                        raise ValidationError(f"不支持的操作: {batch_data.action}")
                    
                    results["success_count"] += 1
                    results["details"].append({
                        "order_id": order_id,
                        "status": "success",
                        "message": f"操作 {batch_data.action} 成功"
                    })
                    
                except Exception as e:
                    results["failed_count"] += 1
                    results["details"].append({
                        "order_id": order_id,
                        "status": "failed",
                        "message": str(e)
                    })
            
            # 记录批量操作日志
            self._log_batch_operation(conn, batch_data, operator_id, results)
            
            return results
    
    
    def get_orders_by_meal(self, meal_id: int, include_canceled: bool = False) -> List[Dict[str, Any]]:
        """获取餐次的所有订单（管理员功能）"""
        with self.db.connection as conn:
            where_clause = "meal_id = ?"
            params = [meal_id]
            
            if not include_canceled:
                where_clause += " AND status != ?"
                params.append(OrderStatus.CANCELED)
            
            query = f"""
            SELECT 
                o.*,
                u.nickname as user_nickname,
                u.openid as user_openid
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE {where_clause}
            ORDER BY o.created_at DESC
            """
            
            orders = conn.execute(query, params).fetchall()
            return [dict(order) for order in orders]
    
    def export_meal_orders(self, meal_id: int) -> Dict[str, Any]:
        """导出餐次订单（Excel格式数据）"""
        with self.db.connection as conn:
            # 获取餐次信息
            meal = self._get_meal(conn, meal_id)
            
            # 获取订单列表
            orders = self.get_orders_by_meal(meal_id, include_canceled=False)
            
            # 统计选项使用情况
            option_stats = self._calculate_option_statistics(orders)
            
            # 生成导出数据
            export_data = {
                "meal_info": {
                    "meal_id": meal_id,
                    "date": meal['date'],
                    "slot": meal['slot'],
                    "description": meal['description'],
                    "total_orders": len(orders),
                    "total_quantity": sum(order['quantity'] for order in orders),
                    "total_revenue_cents": sum(order['total_price_cents'] for order in orders)
                },
                "orders": orders,
                "option_statistics": option_stats,
                "export_time": datetime.now().isoformat()
            }
            
            return export_data
    
    def _calculate_option_statistics(self, orders: List[Dict[str, Any]]) -> Dict[str, int]:
        """计算选项统计信息"""
        option_counts = {}
        
        for order in orders:
            if order['selected_options']:
                import json
                options = json.loads(order['selected_options']) if isinstance(order['selected_options'], str) else order['selected_options']
                
                for option in options:
                    option_name = option.get('name', option.get('id', 'unknown'))
                    option_counts[option_name] = option_counts.get(option_name, 0) + order['quantity']
        
        return option_counts
```

### Day 5: 订单导出功能

#### 目标
实现订单导出功能，支持Excel格式导出和详细的统计信息。

#### 具体操作

##### 1. 创建导出服务

**新建文件: `server/services/export_service.py`**
```python
import json
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from ..core.database import db_manager
from ..core.exceptions import ValidationError, PermissionDeniedError

class ExportService:
    """导出服务"""
    
    def __init__(self):
        self.db = db_manager
    
    def export_meal_orders_excel(self, meal_id: int, operator_id: int) -> bytes:
        """导出餐次订单为Excel文件"""
        # 验证权限
        if not self._is_admin(operator_id):
            raise PermissionDeniedError("需要管理员权限")
        
        with self.db.connection as conn:
            # 获取餐次信息
            meal = self._get_meal(conn, meal_id)
            if not meal:
                raise ValidationError("餐次不存在")
            
            # 获取订单数据
            orders_data = self._get_meal_orders_for_export(conn, meal_id)
            
            # 创建Excel文件
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # 餐次概况工作表
                self._create_meal_summary_sheet(writer, meal, orders_data)
                
                # 订单详情工作表
                self._create_orders_detail_sheet(writer, orders_data['orders'])
                
                # 选项统计工作表
                self._create_options_statistics_sheet(writer, orders_data['option_stats'])
                
                # 用户统计工作表
                self._create_user_statistics_sheet(writer, orders_data['user_stats'])
            
            excel_buffer.seek(0)
            return excel_buffer.getvalue()
    
    def _get_meal_orders_for_export(self, conn, meal_id: int) -> Dict[str, Any]:
        """获取用于导出的餐次订单数据"""
        
        # 基础订单查询
        orders_query = """
        SELECT 
            o.order_id,
            o.user_id,
            u.nickname as user_nickname,
            u.openid as user_openid,
            o.quantity,
            o.selected_options,
            o.total_price_cents,
            o.notes,
            o.status,
            o.created_at as order_time,
            o.updated_at as last_modified
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        WHERE o.meal_id = ? AND o.status = 'active'
        ORDER BY o.created_at ASC
        """
        
        orders = conn.execute(orders_query, [meal_id]).fetchall()
        orders_list = [dict(order) for order in orders]
        
        # 处理订单选项数据
        for order in orders_list:
            if order['selected_options']:
                try:
                    order['selected_options'] = json.loads(order['selected_options'])
                except (json.JSONDecodeError, TypeError):
                    order['selected_options'] = []
        
        # 计算选项统计
        option_stats = self._calculate_detailed_option_statistics(orders_list)
        
        # 计算用户统计
        user_stats = self._calculate_user_statistics(orders_list)
        
        return {
            "orders": orders_list,
            "option_stats": option_stats,
            "user_stats": user_stats
        }
    
    def _create_meal_summary_sheet(self, writer, meal: Dict, orders_data: Dict):
        """创建餐次概况工作表"""
        orders = orders_data['orders']
        
        summary_data = {
            "项目": [
                "餐次ID", "日期", "时段", "描述", 
                "总订单数", "总份数", "总收入(元)", 
                "平均单价(元)", "用户数量", "导出时间"
            ],
            "数值": [
                meal['meal_id'],
                meal['date'],
                "午餐" if meal['slot'] == 'lunch' else "晚餐",
                meal['description'],
                len(orders),
                sum(order['quantity'] for order in orders),
                sum(order['total_price_cents'] for order in orders) / 100,
                (sum(order['total_price_cents'] for order in orders) / len(orders) / 100) if orders else 0,
                len(set(order['user_id'] for order in orders)),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="餐次概况", index=False)
    
    def _create_orders_detail_sheet(self, writer, orders: List[Dict]):
        """创建订单详情工作表"""
        if not orders:
            empty_df = pd.DataFrame({"提示": ["暂无订单数据"]})
            empty_df.to_excel(writer, sheet_name="订单详情", index=False)
            return
        
        # 准备订单详情数据
        detail_data = []
        
        for order in orders:
            # 基础订单信息
            base_info = {
                "订单ID": order['order_id'],
                "用户昵称": order['user_nickname'] or "未设置",
                "用户ID": order['user_openid'][-8:],  # 只显示后8位
                "订单数量": order['quantity'],
                "总价(元)": order['total_price_cents'] / 100,
                "订单时间": order['order_time'],
                "备注": order['notes'] or "",
                "状态": order['status']
            }
            
            # 添加选项信息
            if order['selected_options']:
                options_str = ", ".join([
                    f"{opt['name']}" for opt in order['selected_options']
                ])
                base_info["选择的选项"] = options_str
                
                # 计算选项总价
                options_price = sum(opt.get('price_cents', 0) for opt in order['selected_options'])
                base_info["选项总价(元)"] = options_price * order['quantity'] / 100
                base_info["基础价格(元)"] = (order['total_price_cents'] - options_price * order['quantity']) / 100
            else:
                base_info["选择的选项"] = "无"
                base_info["选项总价(元)"] = 0
                base_info["基础价格(元)"] = order['total_price_cents'] / 100
            
            detail_data.append(base_info)
        
        detail_df = pd.DataFrame(detail_data)
        detail_df.to_excel(writer, sheet_name="订单详情", index=False)
    
    def _create_options_statistics_sheet(self, writer, option_stats: Dict):
        """创建选项统计工作表"""
        if not option_stats:
            empty_df = pd.DataFrame({"提示": ["暂无选项数据"]})
            empty_df.to_excel(writer, sheet_name="选项统计", index=False)
            return
        
        # 转换为DataFrame格式
        stats_data = []
        for option_name, stats in option_stats.items():
            stats_data.append({
                "选项名称": option_name,
                "选择次数": stats['count'],
                "总份数": stats['total_quantity'],
                "总收入(元)": stats['total_revenue_cents'] / 100,
                "平均单价(元)": stats['avg_price_cents'] / 100,
                "选择用户数": stats['unique_users']
            })
        
        # 按选择次数排序
        stats_data.sort(key=lambda x: x['选择次数'], reverse=True)
        
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name="选项统计", index=False)
    
    def _create_user_statistics_sheet(self, writer, user_stats: List[Dict]):
        """创建用户统计工作表"""
        if not user_stats:
            empty_df = pd.DataFrame({"提示": ["暂无用户数据"]})
            empty_df.to_excel(writer, sheet_name="用户统计", index=False)
            return
        
        # 转换为DataFrame格式
        user_data = []
        for user in user_stats:
            user_data.append({
                "用户昵称": user['nickname'] or "未设置",
                "用户ID": user['openid'][-8:],
                "订单数量": user['order_count'],
                "订餐总份数": user['total_quantity'],
                "消费总额(元)": user['total_spent_cents'] / 100,
                "首次订单时间": user['first_order_time'],
                "最后订单时间": user['last_order_time']
            })
        
        # 按消费总额排序
        user_data.sort(key=lambda x: x['消费总额(元)'], reverse=True)
        
        user_df = pd.DataFrame(user_data)
        user_df.to_excel(writer, sheet_name="用户统计", index=False)
    
    def _calculate_detailed_option_statistics(self, orders: List[Dict]) -> Dict[str, Dict]:
        """计算详细的选项统计信息"""
        option_stats = {}
        
        for order in orders:
            if not order['selected_options']:
                continue
            
            for option in order['selected_options']:
                option_name = option.get('name', option.get('id', 'unknown'))
                option_price = option.get('price_cents', 0)
                
                if option_name not in option_stats:
                    option_stats[option_name] = {
                        'count': 0,
                        'total_quantity': 0,
                        'total_revenue_cents': 0,
                        'unique_users': set(),
                        'price_cents': option_price
                    }
                
                stats = option_stats[option_name]
                stats['count'] += 1
                stats['total_quantity'] += order['quantity']
                stats['total_revenue_cents'] += option_price * order['quantity']
                stats['unique_users'].add(order['user_id'])
        
        # 转换set为count并计算平均价格
        for option_name, stats in option_stats.items():
            stats['unique_users'] = len(stats['unique_users'])
            stats['avg_price_cents'] = stats['price_cents']
        
        return option_stats
    
    def _calculate_user_statistics(self, orders: List[Dict]) -> List[Dict]:
        """计算用户统计信息"""
        user_stats = {}
        
        for order in orders:
            user_id = order['user_id']
            
            if user_id not in user_stats:
                user_stats[user_id] = {
                    'user_id': user_id,
                    'nickname': order['user_nickname'],
                    'openid': order['user_openid'],
                    'order_count': 0,
                    'total_quantity': 0,
                    'total_spent_cents': 0,
                    'order_times': []
                }
            
            stats = user_stats[user_id]
            stats['order_count'] += 1
            stats['total_quantity'] += order['quantity']
            stats['total_spent_cents'] += order['total_price_cents']
            stats['order_times'].append(order['order_time'])
        
        # 计算衍生指标（移除平均单次消费）
        result = []
        for user_id, stats in user_stats.items():
            stats['first_order_time'] = min(stats['order_times'])
            stats['last_order_time'] = max(stats['order_times'])
            del stats['order_times']  # 移除临时数据
            result.append(stats)
        
        return result
    
    def _get_meal(self, conn, meal_id: int) -> Optional[Dict]:
        """获取餐次信息"""
        query = "SELECT * FROM meals WHERE meal_id = ?"
        result = conn.execute(query, [meal_id]).fetchone()
        return dict(result) if result else None
    
    def _is_admin(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        with self.db.connection as conn:
            query = "SELECT is_admin FROM users WHERE user_id = ?"
            result = conn.execute(query, [user_id]).fetchone()
            return result and result['is_admin']
```

##### 2. 添加导出API路由

**修改文件: `server/api/v1/meals.py`**
```python
from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from ...services.export_service import ExportService
import io

router = APIRouter()

@router.get("/{meal_id}/export")
async def export_meal_orders(
    meal_id: int,
    current_user_id: int = Depends(get_current_user_id),
    is_admin: bool = Depends(check_admin_permission)
):
    """导出餐次订单为Excel文件"""
    if not is_admin:
        raise PermissionDeniedError("需要管理员权限")
    
    export_service = ExportService()
    excel_data = export_service.export_meal_orders_excel(meal_id, current_user_id)
    
    # 获取餐次信息用于文件名
    meal_service = MealService()
    meal = meal_service.get_meal(meal_id)
    
    filename = f"餐次订单_{meal.date}_{meal.slot}_{meal_id}.xlsx"
    
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

---

## Week 4: 边界场景处理

### Day 1-2: 并发控制

#### 目标
实现订单并发处理和库存一致性保证。

#### 具体操作

##### 1. 数据库层面的并发控制

**修改文件: `server/core/database.py`**
```python
import duckdb
from contextlib import contextmanager
from typing import Generator
from ..config.settings import settings
import threading
import time

class DatabaseManager:
    def __init__(self):
        self.db_path = settings.database_url.replace("duckdb://", "")
        self._connection = None
        self._lock = threading.RLock()
    
    @contextmanager
    def transaction(self, isolation_level: str = "SERIALIZABLE") -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        数据库事务上下文管理器
        
        Args:
            isolation_level: 事务隔离级别，支持 READ_COMMITTED, SERIALIZABLE
        """
        with self._lock:
            conn = self.connection
            try:
                # 设置事务隔离级别
                conn.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                conn.begin()
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                # 检查是否是并发冲突
                if "conflict" in str(e).lower() or "serialization" in str(e).lower():
                    raise ConcurrencyError(f"并发冲突，请重试: {str(e)}")
                raise
    
    @contextmanager 
    def optimistic_lock(self, table: str, record_id: int, version_field: str = "version") -> Generator[dict, None, None]:
        """
        乐观锁实现
        
        Args:
            table: 表名
            record_id: 记录ID
            version_field: 版本字段名
        """
        with self.connection as conn:
            # 读取当前版本
            query = f"SELECT * FROM {table} WHERE {table}_id = ?"
            record = dict(conn.execute(query, [record_id]).fetchone())
            original_version = record.get(version_field, 0)
            
            yield record
            
            # 更新时检查版本
            update_query = f"""
            UPDATE {table} 
            SET {version_field} = {version_field} + 1 
            WHERE {table}_id = ? AND {version_field} = ?
            """
            
            result = conn.execute(update_query, [record_id, original_version])
            if result.rowcount == 0:
                raise ConcurrencyError("记录已被其他用户修改，请刷新后重试")
```

##### 2. 订单服务并发控制

**修改文件: `server/services/order_service.py`** (添加并发控制方法)
```python
import time
import random
from typing import Dict, Any

class OrderService:
    def __init__(self):
        self.db = db_manager
    
    def create_order(self, order_data: OrderCreate, user_id: int) -> Order:
        """创建订单 - 简化版并发控制"""
        with self.db.transaction(isolation_level="SERIALIZABLE") as conn:
            # 使用悲观锁获取餐次信息
            meal = self._get_meal_with_lock(conn, order_data.meal_id)
            
            # 验证餐次状态
            self._validate_meal_for_ordering(meal)
            
            # 原子性检查和更新容量
            current_capacity = self._get_current_capacity_atomic(conn, order_data.meal_id)
            if current_capacity < order_data.quantity:
                raise MealCapacityExceededError(f"餐次容量不足，当前剩余: {current_capacity}")
            
            # 检查用户重复订单（带锁）
            if self._check_duplicate_order_atomic(conn, user_id, order_data.meal_id):
                raise BusinessRuleError("您已有该餐次的订单")
            
            # 计算总价
            total_price = self._calculate_total_price(meal, order_data)
            
            # 原子性检查和扣除余额
            if not self._deduct_balance_atomic(conn, user_id, total_price):
                raise InsufficientBalanceError("余额不足")
            
            # 创建订单
            modify_deadline = self._calculate_modify_deadline(meal)
            order_id = self._insert_order_atomic(conn, order_data, user_id, total_price, modify_deadline)
            
            # 记录日志
            self._log_order_operation(conn, order_id, "create", user_id, {
                "meal_id": order_data.meal_id,
                "quantity": order_data.quantity,
                "total_price_cents": total_price,
                "remaining_capacity": current_capacity - order_data.quantity
            })
            
            return self.get_order(order_id)
    
    def _get_meal_with_lock(self, conn, meal_id: int) -> Dict[str, Any]:
        """获取餐次信息（悲观锁）"""
        query = """
        SELECT * FROM meals 
        WHERE meal_id = ? 
        FOR UPDATE
        """
        result = conn.execute(query, [meal_id]).fetchone()
        if not result:
            raise ValidationError("餐次不存在")
        return dict(result)
    
    def _get_current_capacity_atomic(self, conn, meal_id: int) -> int:
        """原子性获取当前可用容量"""
        # 获取餐次总容量
        meal_query = "SELECT capacity FROM meals WHERE meal_id = ?"
        meal_capacity = conn.execute(meal_query, [meal_id]).fetchone()['capacity']
        
        # 获取已订购数量
        order_query = """
        SELECT COALESCE(SUM(quantity), 0) as ordered_quantity
        FROM orders 
        WHERE meal_id = ? AND status = 'active'
        """
        ordered_quantity = conn.execute(order_query, [meal_id]).fetchone()['ordered_quantity']
        
        return meal_capacity - ordered_quantity
    
    def _check_duplicate_order_atomic(self, conn, user_id: int, meal_id: int) -> bool:
        """原子性检查重复订单"""
        query = """
        SELECT COUNT(*) as count
        FROM orders 
        WHERE user_id = ? AND meal_id = ? AND status = 'active'
        FOR UPDATE
        """
        result = conn.execute(query, [user_id, meal_id]).fetchone()
        return result['count'] > 0
    
    def _deduct_balance_atomic(self, conn, user_id: int, amount_cents: int) -> bool:
        """原子性扣除余额"""
        # 检查当前余额（带锁）
        balance_query = """
        SELECT balance_cents 
        FROM users 
        WHERE user_id = ?
        FOR UPDATE
        """
        current_balance = conn.execute(balance_query, [user_id]).fetchone()['balance_cents']
        
        if current_balance < amount_cents:
            return False
        
        # 扣除余额
        update_query = """
        UPDATE users 
        SET balance_cents = balance_cents - ?
        WHERE user_id = ? AND balance_cents >= ?
        """
        result = conn.execute(update_query, [amount_cents, user_id, amount_cents])
        
        if result.rowcount == 0:
            return False
        
        # 记录账单
        self._insert_ledger_record(conn, user_id, -amount_cents, f"订单扣费", None)
        
        return True
    
    def _insert_order_atomic(self, conn, order_data: OrderCreate, user_id: int, total_price: int, modify_deadline) -> int:
        """原子性插入订单"""
        import json
        
        query = """
        INSERT INTO orders (
            user_id, meal_id, quantity, selected_options, 
            total_price_cents, notes, status, can_modify, 
            modify_deadline, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', true, ?, ?)
        """
        
        selected_options_json = json.dumps(order_data.selected_options) if order_data.selected_options else None
        
        result = conn.execute(query, [
            user_id, order_data.meal_id, order_data.quantity,
            selected_options_json, total_price, 
            getattr(order_data, 'notes', None),
            modify_deadline.isoformat() if modify_deadline else None,
            datetime.now().isoformat()
        ])
        
        return conn.lastrowid if hasattr(conn, 'lastrowid') else result.lastrowid
```

### Day 3-4: 异常恢复

#### 目标
实现网络异常重试机制和数据不一致修复流程。

#### 具体操作

##### 1. 简化前端错误处理（移除自动重试）

**修改文件: `client/miniprogram/core/api/base.ts`** (简化版本)
```typescript
/**
 * API客户端 - 简化错误处理
 */
class ApiClient {
  async request<T = any>(config: RequestConfig): Promise<ApiResponse<T>> {
    try {
      const response = await this.makeRequestWithTimeout(config);
      return this.processResponse<T>(response);
      
    } catch (error) {
      console.error('API请求失败:', error);
      return this.handleError(error);
    }
  }
  
  private async makeRequestWithTimeout(config: RequestConfig): Promise<any> {
    const timeout = config.timeout || this.defaultTimeout;
    
    return new Promise((resolve, reject) => {
      let timeoutId: number;
      let isResolved = false;
      
      // 设置超时
      timeoutId = setTimeout(() => {
        if (!isResolved) {
          isResolved = true;
          reject(new Error('Request timeout'));
        }
      }, timeout);
      
      // 发起请求
      wx.request({
        url: config.url,
        method: config.method,
        data: config.data,
        header: config.header,
        success: (response) => {
          if (!isResolved) {
            isResolved = true;
            clearTimeout(timeoutId);
            resolve(response);
          }
        },
        fail: (error) => {
          if (!isResolved) {
            isResolved = true;
            clearTimeout(timeoutId);
            reject(error);
          }
        }
      });
    });
  }
  
  private handleError(error: any): ApiResponse {
    // 根据错误类型显示相应提示
    let message = '操作失败';
    
    if (error?.errMsg?.includes('timeout')) {
      message = '请求超时，请检查网络连接';
    } else if (error?.error_code === 'CONCURRENCY_ERROR') {
      message = '系统繁忙，请稍后重试';
    } else if (error?.statusCode >= 500) {
      message = '服务器错误，请稍后重试';
    } else if (error?.statusCode === 401) {
      message = '登录已过期，请重新登录';
      this.handleUnauthorized();
    }
    
    // 显示错误提示
    wx.showToast({
      title: message,
      icon: 'error',
      duration: 3000
    });
    
    return {
      success: false,
      message,
      error_code: error?.error_code || 'NETWORK_ERROR'
    };
  }
}
```

##### 2. 数据一致性检查和修复服务

**新建文件: `server/services/consistency_service.py`**
```python
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from ..core.database import db_manager
from ..core.exceptions import ValidationError

class ConsistencyService:
    """数据一致性检查和修复服务"""
    
    def __init__(self):
        self.db = db_manager
    
    def check_all_consistency(self) -> Dict[str, Any]:
        """全面的一致性检查"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # 余额一致性检查
        results["checks"]["balance"] = self.check_balance_consistency()
        
        # 订单容量一致性检查
        results["checks"]["capacity"] = self.check_capacity_consistency()
        
        # 订单状态一致性检查
        results["checks"]["order_status"] = self.check_order_status_consistency()
        
        # 账单记录一致性检查
        results["checks"]["ledger"] = self.check_ledger_consistency()
        
        return results
    
    def check_balance_consistency(self) -> Dict[str, Any]:
        """检查用户余额一致性"""
        with self.db.connection as conn:
            # 查询所有用户的计算余额 vs 实际余额
            query = """
            SELECT 
                u.user_id,
                u.nickname,
                u.balance_cents as recorded_balance,
                COALESCE(SUM(l.amount_cents), 0) as calculated_balance,
                u.balance_cents - COALESCE(SUM(l.amount_cents), 0) as difference
            FROM users u
            LEFT JOIN ledger l ON u.user_id = l.user_id
            GROUP BY u.user_id, u.nickname, u.balance_cents
            HAVING ABS(u.balance_cents - COALESCE(SUM(l.amount_cents), 0)) > 0
            """
            
            inconsistent_users = conn.execute(query).fetchall()
            
            return {
                "status": "pass" if not inconsistent_users else "fail",
                "inconsistent_count": len(inconsistent_users),
                "details": [dict(user) for user in inconsistent_users]
            }
    
    def check_capacity_consistency(self) -> Dict[str, Any]:
        """检查餐次容量一致性"""
        with self.db.connection as conn:
            query = """
            SELECT 
                m.meal_id,
                m.date,
                m.slot,
                m.capacity as max_capacity,
                COALESCE(SUM(o.quantity), 0) as ordered_quantity,
                m.capacity - COALESCE(SUM(o.quantity), 0) as available_capacity,
                CASE 
                    WHEN COALESCE(SUM(o.quantity), 0) > m.capacity THEN 'OVER_CAPACITY'
                    ELSE 'OK'
                END as status
            FROM meals m
            LEFT JOIN orders o ON m.meal_id = o.meal_id AND o.status = 'active'
            GROUP BY m.meal_id, m.date, m.slot, m.capacity
            HAVING COALESCE(SUM(o.quantity), 0) > m.capacity
            """
            
            over_capacity_meals = conn.execute(query).fetchall()
            
            return {
                "status": "pass" if not over_capacity_meals else "fail",
                "over_capacity_count": len(over_capacity_meals),
                "details": [dict(meal) for meal in over_capacity_meals]
            }
    
    def check_order_status_consistency(self) -> Dict[str, Any]:
        """检查订单状态一致性"""
        with self.db.connection as conn:
            # 检查订单状态与餐次状态的一致性
            query = """
            SELECT 
                o.order_id,
                o.status as order_status,
                m.status as meal_status,
                m.date as meal_date,
                o.created_at,
                CASE 
                    WHEN m.status = 'canceled' AND o.status = 'active' THEN 'MEAL_CANCELED_ORDER_ACTIVE'
                    WHEN m.status = 'completed' AND o.status = 'active' THEN 'MEAL_COMPLETED_ORDER_ACTIVE'
                    WHEN m.date < ? AND o.status = 'active' AND m.status = 'published' THEN 'EXPIRED_ORDER'
                    ELSE 'OK'
                END as inconsistency_type
            FROM orders o
            JOIN meals m ON o.meal_id = m.meal_id
            WHERE (
                (m.status = 'canceled' AND o.status = 'active') OR
                (m.status = 'completed' AND o.status = 'active') OR
                (m.date < ? AND o.status = 'active' AND m.status = 'published')
            )
            """
            
            yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
            inconsistent_orders = conn.execute(query, [yesterday, yesterday]).fetchall()
            
            return {
                "status": "pass" if not inconsistent_orders else "fail",
                "inconsistent_count": len(inconsistent_orders),
                "details": [dict(order) for order in inconsistent_orders]
            }
    
    def check_ledger_consistency(self) -> Dict[str, Any]:
        """检查账单记录一致性"""
        with self.db.connection as conn:
            # 检查是否有订单没有对应的账单记录
            query = """
            SELECT 
                o.order_id,
                o.user_id,
                o.total_price_cents,
                l.ledger_id,
                l.amount_cents
            FROM orders o
            LEFT JOIN ledger l ON o.order_id = l.related_order_id 
                AND l.amount_cents = -o.total_price_cents
            WHERE o.status = 'active' AND l.ledger_id IS NULL
            """
            
            missing_ledger_records = conn.execute(query).fetchall()
            
            return {
                "status": "pass" if not missing_ledger_records else "fail",
                "missing_count": len(missing_ledger_records),
                "details": [dict(record) for record in missing_ledger_records]
            }
    
    def repair_balance_inconsistency(self, user_id: int) -> Dict[str, Any]:
        """修复用户余额不一致"""
        with self.db.transaction() as conn:
            # 重新计算用户余额
            ledger_query = """
            SELECT COALESCE(SUM(amount_cents), 0) as calculated_balance
            FROM ledger 
            WHERE user_id = ?
            """
            calculated_balance = conn.execute(ledger_query, [user_id]).fetchone()['calculated_balance']
            
            # 获取当前记录的余额
            user_query = "SELECT balance_cents FROM users WHERE user_id = ?"
            recorded_balance = conn.execute(user_query, [user_id]).fetchone()['balance_cents']
            
            # 更新余额
            update_query = "UPDATE users SET balance_cents = ? WHERE user_id = ?"
            conn.execute(update_query, [calculated_balance, user_id])
            
            # 记录修复日志
            self._log_repair_operation(conn, "balance_repair", {
                "user_id": user_id,
                "old_balance": recorded_balance,
                "new_balance": calculated_balance,
                "difference": calculated_balance - recorded_balance
            })
            
            return {
                "success": True,
                "old_balance": recorded_balance,
                "new_balance": calculated_balance,
                "difference": calculated_balance - recorded_balance
            }
    
    def repair_over_capacity_meal(self, meal_id: int, strategy: str = "cancel_latest") -> Dict[str, Any]:
        """修复超容量餐次"""
        with self.db.transaction() as conn:
            # 获取餐次信息
            meal_query = "SELECT * FROM meals WHERE meal_id = ?"
            meal = dict(conn.execute(meal_query, [meal_id]).fetchone())
            
            # 获取所有订单
            orders_query = """
            SELECT * FROM orders 
            WHERE meal_id = ? AND status = 'active'
            ORDER BY created_at DESC
            """
            orders = conn.execute(orders_query, [meal_id]).fetchall()
            
            total_quantity = sum(order['quantity'] for order in orders)
            excess_quantity = total_quantity - meal['capacity']
            
            if excess_quantity <= 0:
                return {"success": True, "message": "餐次容量正常，无需修复"}
            
            # 执行修复策略
            if strategy == "cancel_latest":
                return self._cancel_latest_orders(conn, orders, excess_quantity, meal_id)
            elif strategy == "reduce_proportional":
                return self._reduce_orders_proportional(conn, orders, excess_quantity, meal_id)
            else:
                raise ValidationError(f"不支持的修复策略: {strategy}")
    
    def _cancel_latest_orders(self, conn, orders: List[dict], excess_quantity: int, meal_id: int) -> Dict[str, Any]:
        """取消最新的订单直到容量正常"""
        canceled_orders = []
        remaining_excess = excess_quantity
        
        for order in orders:
            if remaining_excess <= 0:
                break
            
            if order['quantity'] <= remaining_excess:
                # 完全取消这个订单
                self._cancel_order_with_refund(conn, order['order_id'], "容量修复")
                canceled_orders.append({
                    "order_id": order['order_id'],
                    "user_id": order['user_id'],
                    "quantity": order['quantity'],
                    "action": "canceled"
                })
                remaining_excess -= order['quantity']
            else:
                # 部分取消
                new_quantity = order['quantity'] - remaining_excess
                new_total_price = int(order['total_price_cents'] * new_quantity / order['quantity'])
                refund_amount = order['total_price_cents'] - new_total_price
                
                # 更新订单
                update_query = """
                UPDATE orders 
                SET quantity = ?, total_price_cents = ?, updated_at = ?
                WHERE order_id = ?
                """
                conn.execute(update_query, [
                    new_quantity, new_total_price, 
                    datetime.now().isoformat(), order['order_id']
                ])
                
                # 退款
                self._refund_balance(conn, order['user_id'], refund_amount, order['order_id'], "容量修复部分退款")
                
                canceled_orders.append({
                    "order_id": order['order_id'],
                    "user_id": order['user_id'],
                    "old_quantity": order['quantity'],
                    "new_quantity": new_quantity,
                    "refund_amount": refund_amount,
                    "action": "reduced"
                })
                remaining_excess = 0
        
        # 记录修复日志
        self._log_repair_operation(conn, "capacity_repair", {
            "meal_id": meal_id,
            "strategy": "cancel_latest",
            "excess_quantity": excess_quantity,
            "canceled_orders": canceled_orders
        })
        
        return {
            "success": True,
            "strategy": "cancel_latest",
            "processed_orders": canceled_orders,
            "excess_resolved": excess_quantity - remaining_excess
        }
    
    def _log_repair_operation(self, conn, operation_type: str, details: Dict[str, Any]):
        """记录修复操作日志"""
        import json
        
        log_query = """
        INSERT INTO logs (operation_type, details, created_at)
        VALUES (?, ?, ?)
        """
        
        conn.execute(log_query, [
            f"consistency_repair_{operation_type}",
            json.dumps(details, ensure_ascii=False),
            datetime.now().isoformat()
        ])
```

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "phase1_plan", "status": "completed", "content": "Create Phase 1 detailed execution plan (\u57fa\u7840\u91cd\u6784)"}, {"id": "phase2_plan", "status": "completed", "content": "Create Phase 2 detailed execution plan (\u529f\u80fd\u5b8c\u5584)"}, {"id": "phase3_plan", "status": "in_progress", "content": "Create Phase 3 detailed execution plan (\u6587\u6863\u548c\u6d4b\u8bd5)"}]