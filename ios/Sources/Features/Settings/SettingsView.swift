import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var pendingNickname: String = ""
    @State private var profileSaving: Bool = false
    @State private var bindPhone: String = ""
    @State private var bindCode: String = ""
    @State private var bindCooldownSeconds: Int = 0
    @State private var deletingAccount: Bool = false
    @State private var showDeleteConfirmation: Bool = false

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
            await startCooldownTimer()
        }
        .alert("确认删除账号？", isPresented: $showDeleteConfirmation) {
            Button("取消", role: .cancel) {}
            Button("删除账号", role: .destructive) {
                deletingAccount = true
                Task {
                    defer { deletingAccount = false }
                    _ = await appState.deleteAccount()
                }
            }
        } message: {
            Text("删除后，复盘历史、额度与账号信息会被清空，且无法恢复。")
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
                settingRow(label: "手机号", value: appState.phoneMasked.isEmpty ? "未绑定" : appState.phoneMasked)
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

                if appState.phoneNumber.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("绑定手机号")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(BetweenUsTheme.textPrimary)

                        TextField("请输入 11 位手机号", text: $bindPhone)
                            .keyboardType(.numberPad)
                            .textFieldStyle(.roundedBorder)
                            .onChange(of: bindPhone) { _, value in
                                bindPhone = String(value.filter(\.isNumber).prefix(11))
                            }

                        HStack(spacing: 10) {
                            TextField("验证码", text: $bindCode)
                                .keyboardType(.numberPad)
                                .textFieldStyle(.roundedBorder)
                                .onChange(of: bindCode) { _, value in
                                    bindCode = String(value.filter(\.isNumber).prefix(6))
                                }

                            Button(bindCooldownSeconds > 0 ? "\(bindCooldownSeconds)s" : "获取验证码") {
                                Task {
                                    if let retryAfter = await appState.requestSMSCode(phone: bindPhone) {
                                        bindCooldownSeconds = retryAfter
                                    }
                                }
                            }
                            .buttonStyle(BetweenUsPrimaryButtonStyle())
                            .frame(width: 110)
                            .disabled(bindPhone.count != 11 || bindCooldownSeconds > 0 || appState.authLoading)
                        }

                        Button("绑定手机号") {
                            Task {
                                _ = await appState.bindPhone(phone: bindPhone, code: bindCode)
                            }
                        }
                        .buttonStyle(BetweenUsPrimaryButtonStyle())
                        .disabled(bindPhone.count != 11 || bindCode.count < 4 || appState.authLoading)
                    }
                }

                Button("退出登录") {
                    appState.logout()
                }
                .buttonStyle(BetweenUsPrimaryButtonStyle(isDanger: true))

                Button {
                    showDeleteConfirmation = true
                } label: {
                    if deletingAccount {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                    } else {
                        Text("删除账号")
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(BetweenUsPrimaryButtonStyle(isDanger: true))
                .disabled(deletingAccount)
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
        VStack(alignment: .leading, spacing: 10) {
            Text("帮助与反馈")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            Link("隐私政策", destination: AppConfig.privacyPolicyURL)
                .font(.footnote)
            Link("用户协议", destination: AppConfig.userAgreementURL)
                .font(.footnote)
            Link("用户隐私选择", destination: AppConfig.privacyChoicesURL)
                .font(.footnote)
            Link("支持页面", destination: AppConfig.supportURL)
                .font(.footnote)
            Link("联系客服", destination: AppConfig.supportEmailURL)
                .font(.footnote)
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

    private func startCooldownTimer() async {
        while !Task.isCancelled {
            if bindCooldownSeconds > 0 {
                bindCooldownSeconds -= 1
            }
            do {
                try await Task.sleep(nanoseconds: 1_000_000_000)
            } catch {
                break
            }
        }
    }
}
