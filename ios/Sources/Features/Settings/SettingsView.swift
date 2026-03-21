import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var pendingNickname: String = ""

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(spacing: 14) {
                    accountSection
                    runtimeSection
                    serviceSection
                    billingSection
                }
                .padding(20)
            }
        }
        .task {
            pendingNickname = appState.nickname
        }
    }

    private var accountSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("账号")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            if appState.isLoggedIn {
                accountRow(label: "手机号", value: appState.phoneMasked.isEmpty ? appState.phoneNumber : appState.phoneMasked)
                accountRow(label: "用户 ID", value: appState.currentUserId)

                TextField("昵称", text: $pendingNickname)
                    .textFieldStyle(.roundedBorder)

                Button("保存昵称") {
                    Task {
                        _ = await appState.updateNickname(pendingNickname)
                    }
                }
                .buttonStyle(BetweenUsPrimaryButtonStyle())

                Button("退出登录") {
                    appState.logout()
                }
                .buttonStyle(BetweenUsPrimaryButtonStyle(isDanger: true))
            } else {
                Text("未登录。请返回登录页完成手机号验证。")
                    .font(.footnote)
                    .foregroundStyle(BetweenUsTheme.textSecondary)
            }

            if let authError = appState.authErrorMessage {
                Text(authError)
                    .font(.footnote)
                    .foregroundStyle(Color.red)
                    .textSelection(.enabled)
            }
        }
        .betweenUsCardStyle()
    }

    private var runtimeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("AI 运行状态")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            Text(appState.runtimeStatusMessage)
                .font(.footnote)
                .foregroundStyle(
                    appState.runtimeStatus?.isFullyRealPipeline == true ? BetweenUsTheme.brandBlue : Color.orange
                )

            if let runtime = appState.runtimeStatus {
                accountRow(label: "ASR 提供方", value: runtime.asr_provider)
                accountRow(label: "ASR Mock", value: runtime.asr_mock_enabled ? "是" : "否")
                accountRow(label: "LLM Mock", value: runtime.llm_mock_enabled ? "是" : "否")
                accountRow(label: "队列 Eager", value: runtime.queue_eager_mode ? "是" : "否")
            }

            Button("刷新运行状态") {
                Task {
                    await appState.refreshRuntimeStatus()
                }
            }
            .buttonStyle(BetweenUsPrimaryButtonStyle())
        }
        .betweenUsCardStyle()
    }

    private var serviceSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("服务")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            TextField("服务地址", text: $appState.serverBaseURL)
                .textInputAutocapitalization(.never)
                .keyboardType(.URL)
                .textFieldStyle(.roundedBorder)
                .onSubmit {
                    appState.persistServerBaseURL()
                }

            Text("示例：http://127.0.0.1:8000")
                .font(.footnote)
                .foregroundStyle(BetweenUsTheme.textSecondary)

            Button("立即同步历史记录") {
                appState.persistServerBaseURL()
                Task {
                    await appState.refreshHistory()
                    await appState.refreshRuntimeStatus()
                }
            }
            .buttonStyle(BetweenUsPrimaryButtonStyle())
        }
        .betweenUsCardStyle()
    }

    private var billingSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("计费规则")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            Text("按每 60 分钟记 1 单位，不足 60 分钟按 1 单位计。")
                .foregroundStyle(BetweenUsTheme.textSecondary)

            Text("121 分钟会计为 \(UsageUnitPolicy.units(for: 121)) 单位。")
                .foregroundStyle(BetweenUsTheme.brandBlue)
                .monospacedDigit()
        }
        .betweenUsCardStyle()
    }

    private func accountRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(BetweenUsTheme.textSecondary)
            Spacer()
            Text(value)
                .foregroundStyle(BetweenUsTheme.textPrimary)
                .textSelection(.enabled)
        }
        .font(.footnote)
    }
}
