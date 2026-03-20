import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(spacing: 14) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("账号")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textPrimary)

                        TextField("用户ID", text: $appState.currentUserId)
                            .textInputAutocapitalization(.never)
                            .textFieldStyle(.roundedBorder)

                        Text("用于和后端隔离你的数据权限。")
                            .font(.footnote)
                            .foregroundStyle(BetweenUsTheme.textSecondary)

                        Text(appState.accessToken.isEmpty ? "登录状态：未登录（首次复盘时自动登录）" : "登录状态：已获取访问令牌")
                            .font(.footnote)
                            .foregroundStyle(BetweenUsTheme.textSecondary)

                        if !appState.accessToken.isEmpty {
                            Button("重置登录态") {
                                appState.accessToken = ""
                            }
                            .buttonStyle(BetweenUsPrimaryButtonStyle(isDanger: true))
                        }
                    }
                    .betweenUsCardStyle()

                    VStack(alignment: .leading, spacing: 12) {
                        Text("服务")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textPrimary)

                        TextField("服务地址", text: $appState.serverBaseURL)
                            .textInputAutocapitalization(.never)
                            .keyboardType(.URL)
                            .textFieldStyle(.roundedBorder)

                        Text("示例：http://127.0.0.1:8000")
                            .font(.footnote)
                            .foregroundStyle(BetweenUsTheme.textSecondary)

                        Button("立即同步历史记录") {
                            Task {
                                await appState.refreshHistory()
                            }
                        }
                        .buttonStyle(BetweenUsPrimaryButtonStyle())
                    }
                    .betweenUsCardStyle()

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
                .padding(20)
            }
        }
    }
}
