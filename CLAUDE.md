# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python/FastAPI)
```bash
# Create and activate conda environment
conda env create -f server/environment.yml
conda activate ghf-server

# Start backend server (from project root)
python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000

# Alternative one-time run without environment activation
conda run -n ghf-server python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000

# Health check
curl http://127.0.0.1:8000/api/v1/health

# Run tests
cd server && python -m pytest qa_case/
```

### Frontend (WeChat Mini Program)
```bash
# Install dependencies (client directory)
cd client && npm install

# Development: Open WeChat Developer Tools
# Import project from client/miniprogram directory
# Configure API base URL: http://127.0.0.1:8000/api/v1
```

### Database Management
- Database file: `server/data/ganghaofan.duckdb` (auto-created)
- Configuration: `server/config/db.json`
- Initialization: Automatic on server startup

## Architecture Overview

### Tech Stack
- **Frontend**: WeChat Mini Program (TypeScript, Skyline rendering)
- **Backend**: FastAPI (Python 3.11+) + DuckDB database
- **Authentication**: JWT tokens + WeChat login integration

### Project Structure
```
client/miniprogram/          # WeChat Mini Program frontend
├── pages/
│   ├── index/              # Calendar homepage (main UI)
│   ├── order/              # Order management page
│   ├── admin/              # Admin management interface  
│   ├── profile/            # User profile and settings
│   └── calender/           # Alternative calendar view
├── components/
│   ├── navigation-bar/     # Custom navigation component
│   ├── order-dialog/       # Order placement dialog
│   ├── publish-dialog/     # Meal publishing dialog (admin)
│   └── slot-card/          # Calendar time slot cards
└── utils/
    ├── api.ts              # Network requests and API wrapper
    ├── date.ts             # Date utility functions
    ├── passphrase.ts       # Passphrase management
    └── theme.ts            # Theme switching utilities

server/                     # FastAPI backend service
├── app.py                  # Application entry point
├── db.py                   # Database connection and schema
├── config.py               # Configuration management
├── routers/                # API route modules
│   ├── auth.py             # Authentication routes
│   ├── meals.py            # Meal management API
│   ├── orders.py           # Order processing API
│   ├── users.py            # User management API
│   └── meals_utils/        # Meal business logic modules
├── utils/
│   └── security.py         # JWT and security utilities
└── config/
    ├── db.json             # Database configuration
    ├── passphrases.json    # Access control passphrases
    └── dev_mock.json       # Development mock settings
```

### Key Business Concepts

#### Meal Management System
- **Meal Slots**: Each day has lunch and dinner slots (工作日订餐系统)
- **Status Flow**: `published` → `locked` → `completed` (or `canceled`)
- **Capacity Management**: Each meal has quantity limits and per-user restrictions
- **Admin Controls**: Publish meals, lock orders, mark complete, cancel with refunds

#### Order Processing
- **Single Order Policy**: One order per user per meal slot  
- **Immediate Charging**: Orders are charged to user balance immediately
- **Modification Flow**: Cancel old order + create new order (atomic transaction)
- **Refund Logic**: Automatic refunds when meals are canceled or orders modified

#### User & Balance System
- **WeChat Integration**: Users authenticated via WeChat openid
- **Balance Tracking**: All transactions recorded in ledger table
- **Admin Features**: Admin users can publish meals and manage orders

### Database Schema

#### Core Tables
- `users`: User profiles, balance tracking, admin flags
- `meals`: Meal definitions with pricing, capacity, options
- `orders`: User orders with quantities and selected options  
- `ledger`: Financial transaction log (debits/refunds)
- `logs`: System operation audit trail

#### Key Relationships  
- Users → Orders (one-to-many)
- Meals → Orders (one-to-many)
- Users → Ledger (balance history)

### Authentication & Security
- **JWT Tokens**: Obtained via WeChat login code exchange
- **Passphrase System**: Database access controlled via passphrase mapping
- **Admin Detection**: Based on development mode or stored flags
- **Request Headers**: `Authorization: Bearer <token>` + `X-DB-Key: <passphrase_key>`

### Frontend Architecture

#### Theme System
- **Dark Mode Default**: Customizable via profile page
- **Color Standards**: Defined in `doc/color_std.md`
- **Dynamic Switching**: Live theme updates across all pages

#### State Management
- **Global App State**: Theme, admin flags, login status
- **Local Storage**: User preferences, DB keys, tokens  
- **Component Communication**: Event-based updates

#### API Integration
- **Centralized Wrapper**: All requests go through `utils/api.ts`
- **Error Handling**: Consistent error display and retry logic
- **Batch Loading**: Calendar data loaded in 3-month windows

## Development Workflow

### Adding New Features
1. **Backend**: Create router in `server/routers/`, add to `app.py`
2. **Frontend**: Add API wrapper in `utils/api.ts`, implement UI
3. **Database**: Add migrations to `db.py` schema if needed
4. **Testing**: Add test cases to `server/qa_case/`

### Meal Status Management
- Use `meals_utils` modules for business logic
- All status changes require admin authentication  
- Atomic transactions for order/balance operations
- Comprehensive logging for audit trail

### UI Component Development
- Follow existing component patterns (`navigation-bar`, dialogs)
- Use Skyline-compatible CSS (Flexbox, avoid Grid)
- Implement theme-aware styling
- Handle safe areas and scrolling properly

## Configuration Files

### Required Setup Files
- `server/config/db.json`: Database path configuration
- `server/config/passphrases.json`: Access control mappings (empty allowed for dev)
- `server/config/dev_mock.json`: Development login mocking (optional)

### Environment Variables
- Development vs production detection via WeChat Mini Program environment
- Conda environment: `ghf-server` with Python 3.11+

## Common Development Patterns

### Error Handling
- Frontend: Toast messages for user errors, retry prompts for network issues
- Backend: HTTPException with appropriate status codes and messages
- Database: Transaction rollbacks on failures

### Data Validation  
- Frontend: Input validation before API calls
- Backend: Pydantic models for request/response validation
- Database: Constraints and foreign keys for data integrity

### Logging Strategy
- System operations logged to `logs` table with JSON details
- User actions tracked with before/after states
- Admin actions include actor identification

This codebase implements a complete meal ordering system for workplace dining, with careful attention to user experience, data consistency, and administrative controls.