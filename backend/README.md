# BetweenUs Backend

## 本地启动

```bash
uv sync --dev
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

异步 Worker（新链路必需）：

```bash
redis-server
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

## 关键配置

- `DATABASE_URL`：开发可用 `sqlite:///./betweenus.db`；生产必须使用 `postgresql://...`
- `JWT_SECRET_KEY`：生产环境必须设置强随机密钥
- `ALLOW_INSECURE_HEADER_AUTH`：默认 `false`，不建议在生产开启
- `ASR_API_KEY`：真实语音转写服务密钥（OpenAI 兼容）
- `LLM_API_KEY`：复盘生成服务密钥（默认兼容 DeepSeek）
- `CELERY_BROKER_URL`：异步任务队列地址（默认 Redis）
- `AI_PROVIDER_MODE`：`auto`（默认）有密钥走真实链路，无密钥走 mock；也可强制 `real` 或 `mock`

## 当前能力

- 会话创建 / 完成 / 进度查询
- 会话录音上传（`POST /v1/sessions/{session_id}/audio`）
- 报告查询
- 订阅额度与按次额度结算（数据库持久化）
- IAP 幂等防重（数据库持久化）
- Bearer Token 鉴权（JWT）
