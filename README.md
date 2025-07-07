# FastAPI Project

一个基于FastAPI框架的现代化Web API项目，采用最佳实践和清晰的项目结构。

## 项目结构

```
c-assistant/
├── app/                    # 主应用包
│   ├── api/               # API路由
│   │   ├── deps.py        # 依赖注入
│   │   └── v1/            # API版本1
│   │       ├── api.py     # 主路由
│   │       └── endpoints/ # API端点
│   │           ├── auth.py    # 认证端点
│   │           └── users.py   # 用户端点
│   ├── core/              # 核心配置
│   │   ├── config.py      # 应用配置
│   │   └── security.py    # 安全工具
│   ├── crud/              # 数据库操作
│   │   ├── base.py        # 基础CRUD
│   │   └── crud_user.py   # 用户CRUD
│   ├── db/                # 数据库
│   │   ├── base.py        # 数据库基础
│   │   ├── base_class.py  # SQLAlchemy基础类
│   │   └── session.py     # 数据库会话
│   ├── models/            # 数据模型
│   │   └── user.py        # 用户模型
│   └── schemas/           # Pydantic模式
│       ├── token.py       # Token模式
│       └── user.py        # 用户模式
├── main.py                # 应用入口
├── requirements.txt       # 项目依赖
└── README.md             # 项目说明
```

## 功能特性

- **用户认证**: JWT token认证系统
- **用户管理**: 用户注册、登录、信息管理
- **数据库**: SQLAlchemy ORM，支持多种数据库
- **API文档**: 自动生成的Swagger/OpenAPI文档
- **类型安全**: 完整的类型注解和Pydantic验证

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行应用：
```bash
python main.py
```

3. 访问API文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API端点

### 认证
- `POST /api/v1/auth/login/access-token` - 用户登录
- `POST /api/v1/auth/test-token` - 测试token

### 用户
- `GET /api/v1/users/` - 获取用户列表
- `POST /api/v1/users/` - 创建新用户
- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新当前用户信息
- `GET /api/v1/users/{user_id}` - 获取指定用户信息

## 技术栈

- **FastAPI**: 现代、快速的Web框架
- **SQLAlchemy**: Python ORM
- **Pydantic**: 数据验证和序列化
- **JWT**: 用户认证
- **Uvicorn**: ASGI服务器
- **Pytest**: 测试框架 