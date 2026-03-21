import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var pendingNickname: String = ""
    @State private var profileSaving: Bool = false

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            List {
                Section {
                    profileHeader
                }
                .listRowBackground(Color.clear)

                Section("账号管理") {
                    accountSection
                }

                Section("AI 服务状态") {
                    runtimeSection
                }

                Section("连接与同步") {
                    serviceSection
                }

                Section("计费与说明") {
                    billingSection
                }
            }
            .scrollContentBackground(.hidden)
            .listStyle(.insetGrouped)
        }
        .task {
            pendingNickname = appState.nickname
        }
    }

    private var profileHeader: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(
                    LinearGradient(
                        colors: [BetweenUsTheme.brandCta, BetweenUsTheme.brandBlue],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .frame(width: 52, height: 52)
                .overlay {
                    Text(profileInitial)
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.white)
                }

            VStack(alignment: .leading, spacing: 4) {
                Text(appState.isLoggedIn ? (appState.nickname.isEmpty ? "未设置昵称" : appState.nickname) : "未登录")
                    .font(.headline)
                    .foregroundStyle(BetweenUsTheme.textPrimary)
                Text(appState.phoneMasked.isEmpty ? "登录后可管理你的账号信息" : appState.phoneMasked)
                    .font(.footnote)
                    .foregroundStyle(BetweenUsTheme.textSecondary)
                Text("账号中心")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(BetweenUsTheme.brandBlue)
            }
            Spacer()
        }
        .betweenUsCardStyle()
    }

    private var accountSection: some View {
        Group {
            if appState.isLoggedIn {
                VStack(alignment: .leading, spacing: 14) {
                    settingRow(label: "手机号", value: appState.phoneMasked.isEmpty ? appState.phoneNumber : appState.phoneMasked)
                    settingRow(label: "账号 ID", value: appState.currentUserId)
                    settingRow(label: "当前昵称", value: appState.nickname.isEmpty ? "未设置" : appState.nickname)

                    TextField("设置昵称", text: $pendingNickname)
                        .textFieldStyle(.roundedBorder)

                    Button {
                        profileSaving = true
                        Task {
                            defer { profileSaving = false }
                            _ = await appState.updateNickname(pendingNickname)
                        }
                    } label: {
                        if profileSaving {
                            ProgressView()
                                .frame(maxWidth: .infinity)
                        } else {
                            Text("保存昵称")
                                .frame(maxWidth: .infinity)
                        }
                    }
                    .buttonStyle(BetweenUsPrimaryButtonStyle())
                    .disabled(profileSaving)

                    Button("退出登录") {
                        appState.logout()
                    }
                    .buttonStyle(BetweenUsPrimaryButtonStyle(isDanger: true))
                }
            } else {
                Text("未登录。请先返回登录页完成手机号验证。")
                    .font(.footnote)
                    .foregroundStyle(BetweenUsTheme.textSecondary)
            }

            if let authError = appState.authErrorMessage {
                Text(authError)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .textSelection(.enabled)
            }
        }
    }

    private var runtimeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Circle()
                    .fill(appState.runtimeStatus?.isFullyRealPipeline == true ? BetweenUsTheme.brandTeal : Color.orange)
                    .frame(width: 10, height: 10)
                Text(appState.runtimeStatusMessage)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(
                        appState.runtimeStatus?.isFullyRealPipeline == true ? BetweenUsTheme.brandTeal : Color.orange
                    )
            }

            if let runtime = appState.runtimeStatus {
                settingRow(label: "ASR 提供方", value: runtime.asr_provider)
                settingRow(label: "ASR Mock", value: runtime.asr_mock_enabled ? "开启" : "关闭")
                settingRow(label: "LLM Mock", value: runtime.llm_mock_enabled ? "开启" : "关闭")
                settingRow(label: "队列 Eager", value: runtime.queue_eager_mode ? "开启" : "关闭")
            }

            Button("刷新运行状态") {
                Task {
                    await appState.refreshRuntimeStatus()
                }
            }
            .buttonStyle(BetweenUsPrimaryButtonStyle())
        }
    }

    private var serviceSection: some View {
        VStack(alignment: .leading, spacing: 12) {
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
    }

    private var billingSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("按每 60 分钟记 1 单位，不足 60 分钟按 1 单位计。")
                .foregroundStyle(BetweenUsTheme.textSecondary)

            Text("121 分钟会计为 \(UsageUnitPolicy.units(for: 121)) 单位。")
                .foregroundStyle(BetweenUsTheme.brandBlue)
                .monospacedDigit()
        }
    }

    private var profileInitial: String {
        if !appState.nickname.isEmpty {
            return String(appState.nickname.prefix(1))
        }
        if !appState.phoneMasked.isEmpty {
            return String(appState.phoneMasked.prefix(1))
        }
        return "我"
    }

    private func settingRow(label: String, value: String) -> some View {
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
