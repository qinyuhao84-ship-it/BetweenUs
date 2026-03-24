# BetweenUs

BetweenUs 是一个面向中国大陆首发的 iOS App：
把情侣冲突里的情绪、诉求和行动建议整理成一份可执行的复盘报告。

当前仓库已经完成了从“本地演示”到“可提审版本”的核心切换：

- 登录：手机号验证码 + Sign in with Apple
- 支付：Apple IAP 次数包
- 语音：火山录音识别 + 火山 TOS 临时存储
- 报告：DeepSeek
- 安全：Keychain 存 token、账号删除、严格 HTTPS、Apple 交易验签

面向非技术使用者的最短路径见：[快速开始](./快速开始.md)。
正式上线前的落地动作见：[真实服务接入与发布清单](./真实服务接入与发布清单.md)。
提审材料参考见：[App Store 提审资料清单](./App Store 提审资料清单.md)。
法律文档样板见：[隐私政策](./隐私政策.md)、[用户协议](./用户协议.md)、[用户隐私选择](./用户隐私选择.md)。

## 目录

- `ios/`：SwiftUI iOS 工程
- `backend/`：FastAPI 后端、异步任务、Apple IAP 服务端验签

## 本地启动

### 后端

```bash
cd backend
uv sync --dev
uv run uvicorn app.main:app --reload --port 8000
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### iOS

```bash
cd ios
xcodegen generate --spec project.yml
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -project BetweenUs.xcodeproj -scheme BetweenUs -destination 'generic/platform=iOS Simulator' build
```

## 当前已实现能力

1. Apple 登录、手机号登录、登录后绑定手机号。
2. 录音上传、异步复盘、历史复盘、报告详情。
3. Apple IAP 次数包购买、服务端验签、重复交易幂等、退款/撤销回收。
4. 账号删除，删除时同步清空本地会话和后端数据。
5. Keychain 持久化登录态，Release 环境强制 HTTPS。
6. `/healthz` 和 `/readyz` 就绪检查，以及 PostgreSQL 备份脚本。

## 已验证

后端测试：

```bash
cd backend
uv run pytest
```

iOS 测试：

```bash
cd ios
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -project BetweenUs.xcodeproj -scheme BetweenUs -destination 'platform=iOS Simulator,name=iPhone 17' test
```
