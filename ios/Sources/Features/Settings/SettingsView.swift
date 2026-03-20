import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Form {
            Section("账号") {
                TextField("用户ID", text: $appState.currentUserId)
                    .textInputAutocapitalization(.never)
                Text("用于和后端隔离你的数据权限。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                Text(appState.accessToken.isEmpty ? "登录状态：未登录（首次复盘时自动登录）" : "登录状态：已获取访问令牌")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                if !appState.accessToken.isEmpty {
                    Button("重置登录态") {
                        appState.accessToken = ""
                    }
                }
            }

            Section("服务") {
                TextField("服务地址", text: $appState.serverBaseURL)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                Text("示例：http://127.0.0.1:8000")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                Button("立即同步历史记录") {
                    Task {
                        await appState.refreshHistory()
                    }
                }
            }

            Section("计费规则") {
                Text("按每 60 分钟记 1 单位，不足 60 分钟按 1 单位计。")
                Text("121 分钟会计为 \(UsageUnitPolicy.units(for: 121)) 单位。")
                    .monospacedDigit()
            }
        }
    }
}
