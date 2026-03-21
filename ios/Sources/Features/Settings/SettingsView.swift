import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var pendingNickname: String = ""
    @State private var profileSaving: Bool = false

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(spacing: 14) {
                    profileHeader
                    accountCard
                    walletCard
                    supportCard
                }
                .padding(20)
                .padding(.bottom, 110)
            }
        }
        .task {
            pendingNickname = appState.nickname
            await appState.refreshEntitlements()
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
                .frame(width: 56, height: 56)
                .overlay {
                    Text(profileInitial)
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.white)
                }

            VStack(alignment: .leading, spacing: 4) {
                Text(appState.isLoggedIn ? (appState.nickname.isEmpty ? "未设置昵称" : appState.nickname) : "未登录")
                    .font(.headline)
                    .foregroundStyle(BetweenUsTheme.textPrimary)
                Text(appState.phoneMasked.isEmpty ? "登录后可管理账号信息" : appState.phoneMasked)
                    .font(.footnote)
                    .foregroundStyle(BetweenUsTheme.textSecondary)
            }

            Spacer()
        }
        .betweenUsCardStyle()
    }

    private var accountCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("账号管理")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            if appState.isLoggedIn {
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
        .betweenUsCardStyle()
    }

    private var walletCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("充值与套餐")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            settingRow(label: "订阅额度", value: "\(appState.entitlements?.subscription_units_left ?? 0) 单位")
            settingRow(label: "余额额度", value: "\(appState.entitlements?.payg_units_left ?? 0) 单位")

            NavigationLink {
                RechargeView()
            } label: {
                HStack {
                    Text("进入充值中心")
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    Image(systemName: "chevron.right")
                }
                .foregroundStyle(BetweenUsTheme.textPrimary)
            }
            .buttonStyle(.plain)
        }
        .betweenUsCardStyle()
    }

    private var supportCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("帮助与反馈")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)
            Text("如需关闭账号或查询隐私政策，请联系 support@betweenus.app")
                .font(.footnote)
                .foregroundStyle(BetweenUsTheme.textSecondary)

#if DEBUG
            VStack(alignment: .leading, spacing: 8) {
                Text("调试配置")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(BetweenUsTheme.textSecondary)
                TextField("http://127.0.0.1:8000", text: $appState.serverBaseURL)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        appState.persistServerBaseURL()
                    }
            }
#endif
        }
        .betweenUsCardStyle()
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
