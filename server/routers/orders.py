from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from ..utils.security import get_open_id
from ..services.order_service import order_service, OrderServiceError

router = APIRouter()


class CreateOrderReq(BaseModel):
    meal_id: int
    qty: int
    options: List[str] = []  # list of option_id (boolean options)


class UpdateOrderReq(BaseModel):
    qty: int
    options: List[str] = []


@router.post("/orders")
def create_order(body: CreateOrderReq, open_id: str = Depends(get_open_id)):
    """
    创建新订单
    
    Args:
        body: 订单创建请求体，包含餐次ID、数量和配菜选项
        open_id: 用户微信openid
        
    Returns:
        dict: 包含订单ID、金额和余额的订单信息
        
    Raises:
        HTTPException: 各种业务错误情况
    """
    try:
        return order_service.create_order(
            open_id, body.meal_id, body.qty, body.options
        )
    except OrderServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.patch("/orders/{order_id}")
def update_order(
    order_id: int, body: UpdateOrderReq, open_id: str = Depends(get_open_id)
):
    """
    修改订单（通过取消旧订单+创建新订单实现）
    
    Args:
        order_id: 要修改的订单ID
        body: 新的订单信息
        open_id: 用户微信openid
        
    Returns:
        dict: 新订单的信息
        
    Raises:
        HTTPException: 各种业务错误情况
    """
    try:
        return order_service.update_order(
            open_id, order_id, body.qty, body.options
        )
    except OrderServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.delete("/orders/{order_id}")
def delete_order(order_id: int, open_id: str = Depends(get_open_id)):
    """
    取消订单并退款
    
    Args:
        order_id: 要取消的订单ID
        open_id: 用户微信openid
        
    Returns:
        dict: 包含取消结果和余额的信息
        
    Raises:
        HTTPException: 各种业务错误情况
    """
    try:
        return order_service.cancel_order(open_id, order_id)
    except OrderServiceError as e:
        raise HTTPException(status_code=400, detail=e.message)
