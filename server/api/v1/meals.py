"""
餐次管理路由模块
重构自原 routers/meals.py，使用新的架构
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import io

from ...schemas.meal import (
    MealCreateRequest,
    MealUpdateRequest, 
    MealResponse,
    MealCalendarRequest,
    MealBatchCalendarRequest,
    MealOperationResponse
)
from ...core.security import get_open_id, get_current_user_id, check_admin_permission
from ...core.database import db_manager
from ...core.exceptions import DatabaseError, ValidationError, MealNotFoundError, PermissionDeniedError
from ...services.export_service import ExportService
from ...services.meal_service import MealService

router = APIRouter()


@router.get("/calendar")
def get_calendar(
    month: str,
    open_id: str = Depends(get_open_id)
):
    """获取指定月份的餐次日历数据"""
    try:
        # 基本的月份格式验证
        if len(month) != 7 or month[4] != "-":
            raise ValidationError("月份格式错误，应为 YYYY-MM")
        
        # 查询餐次数据
        meals = db_manager.execute_query(
            """
            SELECT meal_id, date, slot, title, base_price_cents, options_json, 
                   capacity, per_user_limit, status,
                   (SELECT COALESCE(SUM(qty),0) FROM orders o WHERE o.meal_id = m.meal_id AND o.status='active') AS ordered_qty
            FROM meals m
            WHERE strftime(date, '%Y-%m') = ?
            ORDER BY date, slot
            """,
            [month]
        )
        
        # TODO: 计算用户订餐状态
        # 现在先返回基础数据
        meal_list = []
        for row in meals:
            meal_list.append({
                "meal_id": row[0],
                "date": str(row[1]),
                "slot": row[2],
                "title": row[3],
                "base_price_cents": row[4],
                "options": row[5] if row[5] else [],
                "capacity": row[6],
                "per_user_limit": row[7],
                "status": row[8],
                "ordered_qty": row[9],
                "my_ordered": False  # TODO: 实现用户订餐状态查询
            })
        
        return {"month": month, "meals": meal_list}
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日历数据失败: {str(e)}")


@router.get("/calendar/batch")
def get_calendar_batch(
    months: str,
    open_id: str = Depends(get_open_id)
):
    """批量获取多个月份的餐次日历数据"""
    try:
        # 解析并验证月份参数
        month_list = [m.strip() for m in months.split(",") if m.strip()]
        if not month_list:
            raise ValidationError("月份参数不能为空")
        
        for month in month_list:
            if len(month) != 7 or month[4] != "-":
                raise ValidationError(f"月份格式错误: {month}")
        
        # 查询数据
        placeholders = ",".join(["?"] * len(month_list))
        rows = db_manager.execute_query(
            f"""
            SELECT strftime(date, '%Y-%m') AS ym,
                   meal_id, date, slot, title, base_price_cents, options_json, 
                   capacity, per_user_limit, status,
                   (SELECT COALESCE(SUM(qty),0) FROM orders o WHERE o.meal_id = m.meal_id AND o.status='active') AS ordered_qty
            FROM meals m
            WHERE strftime(date, '%Y-%m') IN ({placeholders})
            ORDER BY date, slot
            """,
            month_list
        )
        
        # 按月份组织数据
        result = {month: [] for month in month_list}
        for row in rows:
            ym = row[0]
            if ym in result:
                result[ym].append({
                    "meal_id": row[1],
                    "date": str(row[2]),
                    "slot": row[3],
                    "title": row[4],
                    "base_price_cents": row[5],
                    "options": row[6] if row[6] else [],
                    "capacity": row[7],
                    "per_user_limit": row[8],
                    "status": row[9],
                    "ordered_qty": row[10],
                    "my_ordered": False  # TODO: 实现用户订餐状态查询
                })
        
        return {"months": result}
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取批量日历数据失败: {str(e)}")


@router.get("/meals/{meal_id}")
def get_meal(meal_id: int, open_id: str = Depends(get_open_id)):
    """获取餐次详情"""
    try:
        meal_row = db_manager.execute_one(
            """
            SELECT meal_id, date, slot, title, description, base_price_cents, 
                   options_json, capacity, per_user_limit, status,
                   (SELECT COALESCE(SUM(qty),0) FROM orders o WHERE o.meal_id = m.meal_id AND o.status='active') AS ordered_qty
            FROM meals m WHERE meal_id=?
            """,
            [meal_id]
        )
        
        if not meal_row:
            raise MealNotFoundError(f"餐次不存在: {meal_id}")
        
        return {
            "meal_id": meal_row[0],
            "date": str(meal_row[1]),
            "slot": meal_row[2],
            "title": meal_row[3],
            "description": meal_row[4],
            "base_price_cents": meal_row[5],
            "options": meal_row[6] if meal_row[6] else [],
            "capacity": meal_row[7],
            "per_user_limit": meal_row[8],
            "status": meal_row[9],
            "ordered_qty": meal_row[10],
            "my_ordered": False  # TODO: 实现用户订餐状态查询
        }
        
    except MealNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取餐次详情失败: {str(e)}")


# Phase 2 新增功能：导出API

@router.get("/{meal_id}/export")
async def export_meal_orders(
    meal_id: int,
    current_user_id: int = Depends(get_current_user_id),
    is_admin: bool = Depends(check_admin_permission)
):
    """导出餐次订单为Excel文件"""
    try:
        if not is_admin:
            raise PermissionDeniedError("需要管理员权限")
        
        export_service = ExportService()
        excel_data = export_service.export_meal_orders_excel(meal_id, current_user_id)
        
        # 获取餐次信息用于文件名
        meal_info = db_manager.execute_one(
            "SELECT date, slot FROM meals WHERE meal_id = ?",
            [meal_id]
        )
        
        if meal_info:
            meal_date = str(meal_info[0])
            meal_slot = meal_info[1]
            filename = f"餐次订单_{meal_date}_{meal_slot}_{meal_id}.xlsx"
        else:
            filename = f"餐次订单_{meal_id}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/")
def create_meal(
    meal_data: MealCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    is_admin: bool = Depends(check_admin_permission)
):
    """创建餐次（管理员功能）"""
    try:
        print(f"DEBUG: Creating meal with data: {meal_data}")
        print(f"DEBUG: User ID: {current_user_id}, is_admin: {is_admin}")
        if not is_admin:
            raise PermissionDeniedError("需要管理员权限")
        
        meal_service = MealService()
        
        # 转换请求数据到 MealCreate 模型
        from ...models.meal import MealCreate, MealOption
        meal_create_data = MealCreate(
            meal_date=meal_data.meal_date,
            slot=meal_data.slot,
            title=meal_data.title,
            description=meal_data.description,
            base_price_cents=meal_data.base_price_cents,
            capacity=meal_data.capacity,
            per_user_limit=meal_data.per_user_limit,
            options=[MealOption(
                id=opt.id,
                name=opt.name,
                price_cents=opt.price_cents
            ) for opt in meal_data.options]
        )
        
        # 创建餐次
        meal = meal_service.create_meal(meal_create_data, current_user_id)
        
        return {
            "meal_id": meal.meal_id,
            "date": str(meal.meal_date),
            "slot": meal.slot,
            "title": meal.title,
            "description": meal.description,
            "base_price_cents": meal.base_price_cents,
            "options": meal.options,
            "capacity": meal.capacity,
            "per_user_limit": meal.per_user_limit,
            "status": meal.status,
            "message": "餐次创建成功"
        }
        
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"DEBUG: Exception in create_meal: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建餐次失败: {str(e)}")


# TODO: 实现餐次更新、状态管理等功能
# 现在先保持基本的查询功能，后续会补充完整的管理功能