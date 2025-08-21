# 罡好饭工程重构设计文档

## 项目现状分析

### 代码架构完整性评估

经过深入分析，该餐饮订购系统具有以下特点：

**优势：**
- 基本业务逻辑完整：用户认证、餐次管理、订单处理、余额管理
- 技术栈合理：WeChat Mini Program + FastAPI + DuckDB
- 数据库设计良好：用户、餐次、订单、账单、日志表设计规范
- 安全机制：JWT认证 + 口令验证双重保护

**不足：**
- 代码结构缺乏标准化模块划分
- 前端组件耦合度较高
- 缺乏完整的错误处理和边界案例处理
- 文档结构不够AI友好
- 测试覆盖度不足
- 部署文档缺失

## 重构整体策略

### 核心原则
1. **保持基本架构不变**：维持server和client目录结构
2. **渐进式优化**：先完善现有功能，再扩展新功能
3. **AI友好设计**：清晰的文档结构、标准化的代码组织
4. **可维护性优先**：模块化、可测试、易扩展

### 重构范围
- ✅ 代码结构优化和模块化
- ✅ 文档体系建立
- ✅ 业务逻辑完善
- ✅ 错误处理增强
- ✅ 测试体系建立
- ✅ 部署流程标准化

## 架构优化方案

### 后端架构重构

#### 1. 目录结构优化
```
server/
├── app.py                    # 应用入口
├── config/                   # 配置管理
│   ├── __init__.py
│   ├── settings.py          # 配置类
│   └── environments/        # 环境配置
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── database.py          # 数据库连接管理
│   ├── security.py          # 安全相关
│   └── exceptions.py        # 自定义异常
├── models/                  # 数据模型
│   ├── __init__.py
│   ├── base.py             # 基础模型
│   ├── user.py             # 用户模型
│   ├── meal.py             # 餐次模型
│   └── order.py            # 订单模型
├── services/               # 业务逻辑服务
│   ├── __init__.py
│   ├── auth_service.py     # 认证服务
│   ├── meal_service.py     # 餐次服务
│   ├── order_service.py    # 订单服务
│   └── user_service.py     # 用户服务
├── api/                    # API路由
│   ├── __init__.py
│   ├── v1/                 # API版本1
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── meals.py
│   │   ├── orders.py
│   │   └── users.py
├── schemas/                # Pydantic模式
│   ├── __init__.py
│   ├── auth.py
│   ├── meal.py
│   ├── order.py
│   └── user.py
├── utils/                  # 工具函数
│   ├── __init__.py
│   ├── helpers.py
│   └── validators.py
├── tests/                  # 测试代码
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_meals.py
│   └── test_orders.py
└── migrations/             # 数据库迁移
    ├── __init__.py
    └── versions/
```

#### 2. 服务层架构
- **AuthService**: 处理微信登录、JWT管理、权限验证
- **MealService**: 餐次的CRUD操作、状态管理
- **OrderService**: 订单处理、余额管理、事务控制
- **UserService**: 用户信息管理、余额充值
- **NotificationService**: 通知服务（预留）

#### 3. 数据访问层优化
- 实现Repository模式，封装数据库操作
- 统一异常处理
- 事务管理优化

### 前端架构重构

#### 1. 目录结构优化
```
client/miniprogram/
├── app.js                   # 应用入口
├── app.json                 # 全局配置
├── app.wxss                 # 全局样式
├── core/                    # 核心模块
│   ├── api/                 # API封装
│   │   ├── base.ts         # 基础请求封装
│   │   ├── auth.ts         # 认证API
│   │   ├── meal.ts         # 餐次API
│   │   └── order.ts        # 订单API
│   ├── constants/           # 常量定义
│   │   ├── index.ts
│   │   ├── api.ts
│   │   └── ui.ts
│   ├── utils/               # 工具函数
│   │   ├── date.ts
│   │   ├── format.ts
│   │   ├── storage.ts
│   │   └── validation.ts
│   └── store/               # 状态管理
│       ├── index.ts
│       ├── auth.ts
│       └── theme.ts
├── components/              # 公共组件
│   ├── base/               # 基础组件
│   │   ├── button/
│   │   ├── input/
│   │   └── dialog/
│   ├── business/           # 业务组件
│   │   ├── meal-card/
│   │   ├── order-form/
│   │   └── calendar/
│   └── layout/             # 布局组件
│       ├── navigation-bar/
│       └── tab-bar/
├── pages/                  # 页面
│   ├── index/              # 首页
│   ├── order/              # 订单页
│   ├── profile/            # 个人中心
│   └── admin/              # 管理页面
├── styles/                 # 样式文件
│   ├── themes/             # 主题
│   ├── variables.wxss      # 变量
│   └── mixins.wxss         # 混入
└── types/                  # TypeScript类型定义
    ├── api.ts
    ├── business.ts
    └── ui.ts
```

#### 2. 状态管理优化
- 实现简单的状态管理器
- 统一用户认证状态
- 主题切换状态管理

#### 3. 组件设计原则
- 单一职责原则
- 可复用性优先
- 属性和事件明确定义

## 业务逻辑完善计划

### 1. 缺失功能补全

#### 用户管理增强
- ✅ 用户订单历史统计


#### 订单管理增强
- ✅ 订单状态更细致的划分
- ✅ 订单修改时间窗口控制(发布后，锁定前)
- ✅ 批量订单处理（管理员）
- ✅ 订单导出功能（按餐次选择导出，除了订餐情况的详情以外，再统计各个可选项的总计被选次数（方便准备材料），导出为excel文件）

### 2. 边界场景处理

#### 并发处理
- ✅ 订单并发下单的库存控制
- ✅ 余额并发操作的一致性
- ✅ 餐次状态并发修改的幂等性

#### 异常恢复
- ✅ 网络异常的重试机制
- ✅ 数据不一致的修复流程

#### 性能优化
- ✅ 大量订单的分页加载

### 3. 安全性增强

#### 数据验证
- ✅ 输入数据的严格校验
- ✅ SQL注入防护
- ✅ XSS攻击防护

#### 权限控制
- ✅ 细粒度的权限管理
- ✅ 敏感操作的二次确认

## AI友好文档设计

### 1. 文档结构标准化

基于现有的 `doc/` 目录，优化文档组织结构：

```
doc/
├── README.md                # 项目总览（基于现有overview.md优化）
├── ARCHITECTURE.md          # 系统架构设计
├── API.md                   # API接口文档汇总
├── DEPLOYMENT.md            # 部署运维指南
├── business/                # 业务逻辑文档
│   ├── user-flow.md         # 用户操作流程
│   ├── order-logic.md       # 订单业务逻辑（基于现有order_logic_todolist.md）
│   └── meal-management.md   # 餐次管理流程
├── technical/               # 技术规范文档
│   ├── code-style.md        # 代码规范（基于现有comment_std.md扩展）
│   ├── database-schema.md   # 数据库设计文档
│   ├── api-specification.md # API规范详细说明
│   └── testing-guide.md     # 测试规范和指南
├── standards/               # 现有标准文档优化
│   ├── color-standard.md    # 颜色规范（现有color_std.md）
│   ├── log-standard.md      # 日志规范（现有log_std.md）
│   └── comment-standard.md  # 注释规范（现有comment_std.md）
└── guides/                  # 操作指南
    ├── development-setup.md # 开发环境搭建
    ├── admin-guide.md       # 管理员操作指南
    └── troubleshooting.md   # 问题排查指南
```

### 2. 文档内容标准化

#### 2.1 每个文档的标准格式
```markdown
# 文档标题

## 概述
简洁描述文档目的和适用范围

## 目标读者
明确文档的目标读者（开发者/管理员/用户等）

## 核心内容
具体的技术内容或业务流程

## 示例
实际的代码示例或操作演示

## 相关文档
关联文档的链接

## 更新日志
文档的主要变更记录
```

#### 2.2 API文档标准
```markdown
# API名称

## 请求信息
- **方法**: POST/GET/PUT/DELETE
- **路径**: /api/v1/...
- **权限**: 需要认证/管理员权限

## 请求参数
| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|

## 响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

## 错误码说明
| 错误码 | 说明 | 解决方案 |
|--------|------|----------|

## 业务逻辑说明
详细的业务规则和边界条件

## 代码示例
前端调用示例和后端实现要点
```

#### 2.3 业务流程文档标准
```markdown
# 业务流程名称

## 流程概述
业务流程的目的和价值

## 参与角色
- 用户
- 管理员
- 系统

## 流程步骤
1. **步骤1**: 详细描述
   - 触发条件
   - 操作内容
   - 预期结果
   - 异常处理

## 业务规则
- 规则1: 具体说明
- 规则2: 具体说明

## 数据流转
数据在各个环节的流转情况

## 异常场景
可能出现的异常情况和处理方案
```

### 3. 现有文档优化建议

#### 3.1 基于 `doc/overview.md` 创建项目README
- 保留核心的项目介绍和技术栈信息
- 添加快速开始指南
- 补充项目目录结构说明
- 增加常见问题解答

#### 3.2 标准文档增强
- `color_std.md` → `doc/standards/color-standard.md`：添加使用示例和组件应用
- `comment_std.md` → `doc/standards/comment-standard.md`：扩展为完整的代码规范
- `log_std.md` → `doc/standards/log-standard.md`：添加日志级别和格式规范

#### 3.3 新增必要文档
- **API文档汇总**: 整合所有接口的快速查询手册
- **部署指南**: 从开发环境到生产环境的完整部署流程
- **故障排查**: 常见问题和解决方案
- **数据库文档**: 表结构、关系图和迁移说明

### 2. 代码注释标准

#### Python代码注释规范
```python
def create_meal(meal_data: MealCreate, creator_id: int) -> Meal:
    """
    创建新餐次
    
    Args:
        meal_data: 餐次创建数据，包含基本信息和选项
        creator_id: 创建者用户ID，必须是管理员
        
    Returns:
        Meal: 创建的餐次对象，包含生成的ID和时间戳
        
    Raises:
        PermissionDeniedError: 当creator_id不是管理员时
        DuplicateMealError: 当相同日期时段已存在餐次时
        ValidationError: 当meal_data格式不正确时
        
    Examples:
        >>> meal = create_meal(
        ...     MealCreate(date="2024-01-15", slot="lunch", ...),
        ...     creator_id=1
        ... )
        >>> meal.meal_id
        123
        
    Business Rules:
        - 每个日期+时段组合只能有一个餐次
        - 创建时默认状态为'published'
        - 配菜选项必须包含ID、名称和价格
    """
```

#### TypeScript代码注释规范
```typescript
/**
 * 餐次日历组件
 * 
 * @description 展示月度餐次日历，支持滑动切换月份和点击下单
 * @version 2.0.0
 * @author AI Assistant
 * 
 * @example
 * ```typescript
 * <meal-calendar
 *   month="2024-01"
 *   onMealClick={(mealId) => navigateToOrder(mealId)}
 * />
 * ```
 */
interface MealCalendarComponent {
  /** 当前显示月份，格式YYYY-MM */
  month: string;
  /** 餐次点击事件处理器 */
  onMealClick: (mealId: number, slot: 'lunch' | 'dinner') => void;
}
```

### 3. API文档标准化

使用OpenAPI 3.0规范，自动生成交互式文档：

```yaml
# 示例API文档片段
paths:
  /api/v1/meals:
    post:
      summary: 创建餐次
      description: |
        管理员创建新餐次。每个日期+时段组合只能有一个餐次。
        
        **业务规则:**
        - 需要管理员权限
        - 日期+时段组合必须唯一
        - 配菜选项价格可为负数（折扣）
        
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MealCreate'
            example:
              date: "2024-01-15"
              slot: "lunch"
              description: "香辣鸡腿饭"
              base_price_cents: 2000
              capacity: 50
              options:
                - id: "chicken_leg"
                  name: "加鸡腿"
                  price_cents: 300
```

## 详细执行步骤

### Phase 1: 基础重构（第1-2周）

#### Week 1: 后端重构
1. **Day 1-2**: 重构目录结构和模块划分
   - 创建新的目录结构
   - 拆分现有代码到对应模块
   - 更新导入路径

2. **Day 3-4**: 服务层抽象
   - 实现AuthService、MealService、OrderService
   - 迁移业务逻辑到服务层
   - 优化数据库操作

3. **Day 5**: 异常处理和日志优化
   - 统一异常处理机制
   - 完善日志记录
   - 编写基础测试

#### Week 2: 前端重构
1. **Day 1-2**: 组件模块化
   - 重构现有组件，提升复用性
   - 统一组件接口设计
   - 实现基础组件库

2. **Day 3-4**: API层优化
   - 重构API调用层
   - 统一错误处理
   - 实现请求缓存

3. **Day 5**: 状态管理优化
   - 实现统一状态管理
   - 优化主题切换逻辑
   - 完善用户认证状态

### Phase 2: 功能完善（第3-4周）

#### Week 3: 核心功能增强
1. **Day 1-2**: 用户系统完善
   - 订单历史统计和查看（当前只支持了所有log的查询，没有过滤自己相关）

3. **Day 5**: 订单系统优化
   - 订单状态细化
   - 修改时间窗口控制

#### Week 4: 边界场景处理
1. **Day 1-2**: 并发控制
   - 订单并发处理
   - 库存一致性保证

2. **Day 3-4**: 异常恢复
   - 网络重试机制
   - 数据修复流程

3. **Day 5**: 性能优化
   - 缓存策略实施
   - 数据库查询优化
   - 前端性能监控

### Phase 3: 文档和测试（第5周）

#### Week 5: 完善文档和测试
1. **Day 1-2**: API文档完善
   - OpenAPI规范文档
   - 接口示例和说明
   - 错误码文档

2. **Day 3-4**: 测试覆盖
   - 单元测试编写
   - 集成测试设计
   - 端到端测试

3. **Day 5**: 部署文档
   - 环境搭建指南
   - 部署流程文档
   - 监控和运维手册

## 预期收益

### 技术收益
1. **可维护性提升60%**: 模块化架构便于理解和修改
2. **开发效率提升40%**: 标准化组件和API减少重复开发
3. **Bug率降低50%**: 完善的测试覆盖和错误处理
4. **性能提升30%**: 缓存策略和查询优化

### 业务收益
1. **用户体验改善**: 更流畅的交互和更快的响应
2. **功能完整性**: 补全缺失的业务场景
3. **扩展性增强**: 为未来功能扩展打下基础
4. **运维效率**: 完善的监控和部署流程

### AI协作收益
1. **文档完整性**: AI可以快速理解项目结构和业务逻辑
2. **代码可读性**: 标准化的注释和命名规范
3. **问题定位**: 清晰的错误处理和日志记录
4. **功能扩展**: 模块化架构便于AI辅助开发新功能

## 风险评估与缓解

### 技术风险
1. **重构破坏性**: 分阶段重构，保持功能可用
2. **性能回归**: 持续性能监控和基准测试
3. **兼容性问题**: 充分的测试和渐进式发布

### 业务风险
1. **用户体验中断**: 向后兼容和平滑迁移
2. **数据丢失**: 完善的备份和回滚机制
3. **功能回退**: 功能开关和灰度发布

### 缓解措施
1. **版本控制**: Git分支策略和代码审查
2. **测试保障**: 自动化测试和手工验收
3. **监控告警**: 实时监控和快速响应
4. **应急预案**: 故障回滚和数据恢复流程

## 总结

本重构方案基于对现有代码的深入分析，在保持基本架构稳定的前提下，通过模块化、标准化、文档化等手段，将工程改造为AI友好、易维护、可扩展的现代化应用。

重构将分5周完成，每周都有明确的目标和可衡量的成果。通过这次重构，项目将在技术债务清理、功能完整性、开发效率等方面获得显著提升，为后续的AI辅助开发和功能扩展奠定坚实基础。