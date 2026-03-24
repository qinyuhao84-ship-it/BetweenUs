# BetweenUs Backend

## 本地启动

```bash
uv sync --dev
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

异步 Worker：

```bash
redis-server
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

## 当前后端能力

- `手机号验证码登录` 与 `Sign in with Apple`
- `登录后绑定手机号`
- `账号删除`，删除时级联清理用户资料、会话、报告、额度、验证码和残留音频
- `Apple IAP` 交易验签、幂等入账、退款/撤销同步
- `App Store Server Notifications` 回调处理
- `录音上传 -> 火山 ASR -> DeepSeek 报告生成`
- `健康检查 /healthz` 与 `就绪检查 /readyz`

## 关键配置

### 基础配置

- `DATABASE_URL`：发布必须使用 `postgresql://...`
- `JWT_SECRET_KEY`：必须设置强随机密钥
- `ALLOW_INSECURE_HEADER_AUTH`：默认 `false`，生产禁止开启
- `AI_PROVIDER_MODE`：发布环境固定为 `real`

### AI 与音频

- `ASR_PROVIDER`：推荐 `volc_recording_bigmodel`
- `ASR_VOLC_APP_ID` / `ASR_VOLC_ACCESS_TOKEN`：火山录音识别鉴权
- `ASR_VOLC_UPLOAD_PROVIDER=volc_tos`：正式链路固定走火山 TOS
- `VOLC_TOS_ENDPOINT` / `VOLC_TOS_REGION` / `VOLC_TOS_BUCKET`：火山 TOS 存储
- `VOLC_TOS_ACCESS_KEY_ID` / `VOLC_TOS_ACCESS_KEY_SECRET`：火山 TOS 凭据
- `LLM_API_KEY`：复盘生成服务密钥（默认兼容 DeepSeek）

### 登录与短信

- `APPLE_CLIENT_ID` / `APPLE_TEAM_ID` / `APPLE_KEY_ID` / `APPLE_PRIVATE_KEY`：Apple 登录服务端校验
- `SMS_PROVIDER=aliyun`：正式环境固定阿里云短信
- `SMS_ALIYUN_ACCESS_KEY_ID` / `SMS_ALIYUN_ACCESS_KEY_SECRET`：阿里云 AccessKey
- `SMS_ALIYUN_SIGN_NAME` / `SMS_ALIYUN_TEMPLATE_CODE`：阿里云短信签名与模板
- `SMS_ALIYUN_SCHEME_NAME`：如果阿里云控制台配置了方案名，则填这里

### Apple IAP

- `APPLE_IAP_BUNDLE_ID`：iOS App 的 Bundle ID
- `APPLE_IAP_ENVIRONMENT`：`local_testing` / `sandbox` / `production`
- `APPLE_IAP_ROOT_CA_PATHS`：正式验签时使用的 Apple 根证书路径，多个证书用逗号分隔
- `APPLE_IAP_APP_APPLE_ID`：生产环境必填

## 核心接口

### 认证

- `POST /v1/auth/sms/send`
- `POST /v1/auth/sms/login`
- `POST /v1/auth/apple-login`
- `POST /v1/auth/phone-bind`
- `GET /v1/auth/me`
- `PATCH /v1/auth/me`
- `DELETE /v1/auth/me`

### 会话与报告

- `POST /v1/sessions`
- `POST /v1/sessions/{session_id}/audio`
- `POST /v1/sessions/{session_id}/complete`
- `GET /v1/sessions/{session_id}`
- `GET /v1/reports/{session_id}`

### Apple IAP

- `GET /v1/billing/packages`
- `GET /v1/billing/entitlements`
- `POST /v1/billing/iap/verify`
- `POST /v1/billing/app-store-notifications`

## 运维脚本

- 就绪检查：`backend/scripts/check_backend_ready.sh`
- PostgreSQL 备份：`backend/scripts/backup_postgres.sh`

## 建议的发布顺序

1. 先把 App 备案、域名备案、短信模板审核通过。
2. 再配置 Apple 登录、Apple IAP、阿里云短信、火山 TOS、火山 ASR、DeepSeek。
3. 用 `check_backend_ready.sh` 确认 API 已经可用。
4. 用 TestFlight 先跑通 `Apple 登录 -> 录音 -> 报告 -> IAP -> 删除账号` 全链路。
