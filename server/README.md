# GangHaoFan Server

FastAPI + DuckDB backend for the mini program.

## Quick start (Windows PowerShell)

### Option A: Conda (recommended)
```powershell
# in repo root
conda env create -f server/environment.yml
conda activate ghf-server
python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```

如果你不想激活环境，可使用一次性运行（避免 PATH/激活问题）：
```powershell
conda run -n ghf-server python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
```


API base: http://127.0.0.1:8000/api/v1

- Health: GET /api/v1/health
- Login (dev): POST /api/v1/auth/login { code }
- Auth: pass Authorization: Bearer <token>

Data file: `server/data/ganghaofan.duckdb` (auto-created).

Multi-DB (by passphrase key):
- Configure mappings in `server/config/passphrases.json` or env var `GHF_PASSPHRASE_MAP`.
- On server startup, all configured keys are proactively initialized:
	- DB files at `server/data/ganghaofan_{key}.duckdb` are created if missing.
	- Schema is ensured/updated idempotently.
- Client passes `X-DB-Key: <key>` automatically after you set the passphrase in the app.

Dev mock login (optional):
- Edit `server/config/dev_mock.json`:
	- `mock_enabled`: true/false
	- `open_id`: fixed openid to use when mock is enabled
	- `nickname`: nickname to prefill in users table on first access
- Alternatively set env `GHF_MOCK_AUTH` to a JSON string with the same fields.
- When enabled, `/auth/login` returns a token for the fixed open_id.

## Notes
- Immediate debit on order create; refund on cancel; modify = cancel + create
- Boolean options only; balance can be negative
- Transactions wrap ledger/balance/order writes

## Deploy
See doc/agent_to_do/step_5_dev_deploy.md

## Troubleshooting
- PackagesNotFoundError: duckdb=1.1.0
	- 说明：conda 通道无该精确版本。
	- 解决：environment.yml 已调整为通过 pip 安装 duckdb。请重新创建环境：
		```powershell
		conda env remove -n ghf-server
		conda env create -f server/environment.yml
		conda activate ghf-server
		```
- ModuleNotFoundError: No module named 'server'
	- 说明：当前工作目录不在仓库根目录。
	- 解决：请在仓库根目录运行：
		```powershell
		python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000
		```
		如果你坚持在 `server/` 目录内运行，请改用：
		```powershell
		python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
		```
- ImportError / 包缺失
	- 确认已激活环境并安装依赖：
		```powershell
		conda activate ghf-server
		python -c "import fastapi, duckdb, jose, pydantic; print('deps ok')"
		```
	- 若仍缺少 jose 或 duckdb，可在已激活环境中手动安装：
		```powershell
		conda activate ghf-server
		python -m pip install python-jose duckdb
		```
 - 看不到“test”空间的日历
	 - 说明：`test` 是独立库，首次为空。
	 - 解决：服务启动时已自动创建并初始化 `server/data/ganghaofan_test.duckdb`。请在“管”视图发布餐次，或复制默认库数据（可选）。
