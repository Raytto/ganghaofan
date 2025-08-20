"""
导出服务
提供餐次订单导出功能，支持Excel格式导出和详细的统计信息
Phase 2 功能增强
"""

import json
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..core.database import db_manager
from ..core.exceptions import ValidationError, PermissionDeniedError

# 导出服务需要pandas来生成Excel文件
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class ExportService:
    """导出服务"""
    
    def __init__(self):
        self.db = db_manager
    
    def export_meal_orders_excel(self, meal_id: int, operator_id: int) -> bytes:
        """导出餐次订单为Excel文件"""
        # 验证权限
        if not self._is_admin(operator_id):
            raise PermissionDeniedError("需要管理员权限")
        
        if not PANDAS_AVAILABLE:
            raise ValidationError("系统未安装pandas库，无法导出Excel文件")
        
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
                
                # 用户统计工作表（移除平均单次消费）
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
            u.open_id as user_openid,
            o.qty as quantity,
            o.options_json as selected_options,
            o.amount_cents as total_price_cents,
            o.status,
            o.created_at as order_time,
            o.updated_at as last_modified
        FROM orders o
        JOIN users u ON o.user_id = u.id
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
            else:
                order['selected_options'] = []
        
        # 计算选项统计
        option_stats = self._calculate_detailed_option_statistics(orders_list)
        
        # 计算用户统计（移除平均单次消费）
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
                "用户数量", "导出时间"
            ],
            "数值": [
                meal['meal_id'],
                meal['date'],
                "午餐" if meal['slot'] == 'lunch' else "晚餐",
                meal['description'] or meal.get('title', ''),
                len(orders),
                sum(order['quantity'] for order in orders),
                sum(order['total_price_cents'] for order in orders) / 100,
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
                "用户ID": order['user_openid'][-8:] if order['user_openid'] else "未知",
                "订单数量": order['quantity'],
                "总价(元)": order['total_price_cents'] / 100,
                "订单时间": order['order_time'],
                "状态": order['status']
            }
            
            # 添加选项信息
            if order['selected_options']:
                try:
                    # 处理选项数据，可能是字符串列表或ID列表
                    options_list = order['selected_options']
                    if isinstance(options_list, list) and options_list:
                        # 简化处理：直接显示选项内容
                        options_str = ", ".join([
                            str(opt) for opt in options_list
                        ])
                        base_info["选择的选项"] = options_str
                    else:
                        base_info["选择的选项"] = "无"
                except:
                    base_info["选择的选项"] = "解析失败"
            else:
                base_info["选择的选项"] = "无"
            
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
                "选择用户数": stats['unique_users']
            })
        
        # 按选择次数排序
        stats_data.sort(key=lambda x: x['选择次数'], reverse=True)
        
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name="选项统计", index=False)
    
    def _create_user_statistics_sheet(self, writer, user_stats: List[Dict]):
        """创建用户统计工作表（移除平均单次消费）"""
        if not user_stats:
            empty_df = pd.DataFrame({"提示": ["暂无用户数据"]})
            empty_df.to_excel(writer, sheet_name="用户统计", index=False)
            return
        
        # 转换为DataFrame格式
        user_data = []
        for user in user_stats:
            user_data.append({
                "用户昵称": user['nickname'] or "未设置",
                "用户ID": user['openid'][-8:] if user['openid'] else "未知",
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
                # 简化处理选项名称
                option_name = str(option) if option else 'unknown'
                
                if option_name not in option_stats:
                    option_stats[option_name] = {
                        'count': 0,
                        'total_quantity': 0,
                        'unique_users': set()
                    }
                
                stats = option_stats[option_name]
                stats['count'] += 1
                stats['total_quantity'] += order['quantity']
                stats['unique_users'].add(order['user_id'])
        
        # 转换set为count
        for option_name, stats in option_stats.items():
            stats['unique_users'] = len(stats['unique_users'])
        
        return option_stats
    
    def _calculate_user_statistics(self, orders: List[Dict]) -> List[Dict]:
        """计算用户统计信息（移除平均单次消费）"""
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
            query = "SELECT is_admin FROM users WHERE id = ?"
            result = conn.execute(query, [user_id]).fetchone()
            return result and result['is_admin']


# 全局服务实例
export_service = ExportService()