# BetweenUs

情侣冲突复盘 App（iOS + FastAPI）首阶段实现。

面向非技术使用者的最短路径见：[快速开始](./快速开始.md)。
Xcode 里如何测试见：[Xcode测试说明](./Xcode测试说明.md)。

## 目录

- `ios/`：Xcode iOS 工程（SwiftUI）
- `backend/`：FastAPI 后端（含定价与进度服务、接口测试）

## 1) 启动后端

```bash
cd backend
uv sync --dev
uv run uvicorn app.main:app --reload --port 8000
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

后端业务接口默认使用 `Authorization: Bearer <token>`。
如需临时兼容旧调试方式，需在后端开启 `ALLOW_INSECURE_HEADER_AUTH=true` 后才支持 `X-User-Id`。

## 2) 启动 iOS

```bash
cd ios
xcodegen generate --spec project.yml
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -project BetweenUs.xcodeproj -scheme BetweenUs -destination 'generic/platform=iOS Simulator' build
```

也可直接用 Xcode 打开 `ios/BetweenUs.xcodeproj` 运行模拟器。

## 3) 测试

后端：

```bash
cd backend
uv run pytest
```

iOS：

```bash
cd ios
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -project BetweenUs.xcodeproj -scheme BetweenUs -destination 'platform=iOS Simulator,name=iPhone 17' test
```

## 当前已实现能力

1. iOS 端：首次启动手机号验证码登录，录音后自动上传音频，触发异步复盘，实时展示任务进度与结果，并可从后端同步历史记录。
2. 后端：短信验证码登录、用户资料、会话创建/音频上传/异步复盘（ASR+LLM）/进度查询/会话详情/报告查询/计费权益查询与加购幂等。
3. 安全基线：JWT 鉴权、输入校验、用户数据隔离、无硬编码密钥。
4. 数据层：会话/报告/进度/余额已落数据库持久化（非内存）。
5. 测试：后端单元+集成测试通过，iOS 单元测试通过。
