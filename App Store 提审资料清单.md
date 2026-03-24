# App Store 提审资料清单

这份清单给产品、运营和提审同学使用。
目标是保证中国大陆首发所需材料一次性补齐。

## 1. App Store Connect 基础信息

1. App 名称：`BetweenUs`
2. Bundle ID：`com.betweenus.app`
3. SKU：建议填 `betweenus-ios-cn`
4. 支持 URL：`https://betweenus.app/support/`
5. 营销 URL：`https://betweenus.app/`
6. 隐私政策 URL：`https://betweenus.app/legal/privacy/`
7. 用户协议 URL：`https://betweenus.app/legal/terms/`
8. 隐私选择 URL：`https://betweenus.app/legal/privacy-choices/`
9. 客服邮箱：`qinyuhao84@gmail.com`
10. 中国大陆 `ICP Filing Number`：等备案通过后填写

## 2. 推荐直接填写的商店文案

1. 副标题：`冲突复盘助手`
2. 关键词：`关系复盘,沟通,冲突分析,录音转写,复盘报告`
3. 描述：
   `BetweenUs 帮你在冲突之后快速整理事实、诉求和下一步行动。你可以录下刚刚发生的内容，系统会自动转写并生成一份克制、清楚、可执行的复盘报告。`

## 2.5 当前预览地址

1. 当前已上线预览：`https://betweenus-site.vercel.app/`
2. 这个地址只用于预览和联调，不作为中国大陆正式发布地址。

## 3. 截图与视觉素材

1. App Icon
2. iPhone 截图
3. 如有需要，补充 App Preview 视频

## 4. 审核备注建议

建议写清楚三件事：

1. 审核员可使用 `Sign in with Apple` 直接进入 App。
2. 正式用户也支持手机号验证码登录。
3. App 内数字商品采用 `Apple IAP` 次数包，不使用外部支付。
4. 法务文档与支持页已上线到：
   - 预览：`https://betweenus-site.vercel.app/`
   - 正式：中国大陆发布使用 `https://betweenus.app/`

## 5. App Privacy 需要申报的数据

至少要覆盖：

1. 联系方式：手机号
2. 用户标识符：用户 ID、Apple 登录标识
3. 音频数据：用户录音
4. 用户内容：转写文本、复盘内容
5. 购买信息：Apple 交易信息
6. 诊断信息：如果你有收集崩溃或故障日志

## 6. 提审前最后确认

1. 法律文档链接已经能正常打开。
2. Release 构建只走 HTTPS。
3. 删除账号入口在 App 内可见且可用。
4. Apple IAP 商品已审核通过或已可测试。
5. 中国大陆上架信息已填写完整。
