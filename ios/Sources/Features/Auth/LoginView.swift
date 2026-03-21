import SwiftUI

struct LoginView: View {
    @EnvironmentObject private var appState: AppState
    @State private var phone: String = ""
    @State private var code: String = ""
    @State private var cooldownSeconds: Int = 0

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("BetweenUs")
                            .betweenUsDisplayTitle()
                        Text("把争执变成可修复的理解。")
                            .betweenUsBodyMuted()
                    }
                    .padding(.top, 36)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("手机号登录")
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(BetweenUsTheme.textPrimary)

                        inputBlock(
                            title: "手机号",
                            placeholder: "请输入 11 位手机号",
                            icon: "iphone",
                            text: $phone
                        )
                        .accessibilityIdentifier("login.phoneField")
                        .onChange(of: phone) { _, newValue in
                            phone = sanitizePhone(newValue)
                        }

                        HStack(alignment: .bottom, spacing: 10) {
                            inputBlock(
                                title: "验证码",
                                placeholder: "请输入验证码",
                                icon: "number",
                                text: $code
                            )
                            .accessibilityIdentifier("login.codeField")
                            .onChange(of: code) { _, newValue in
                                code = sanitizeCode(newValue)
                            }

                            Button(cooldownSeconds > 0 ? "\(cooldownSeconds)s" : "获取") {
                                Task {
                                    if let retryAfter = await appState.requestSMSCode(phone: phone) {
                                        cooldownSeconds = retryAfter
                                    }
                                }
                            }
                            .buttonStyle(BetweenUsPrimaryButtonStyle())
                            .frame(width: 90)
                            .disabled(!isPhoneStrictlyValid || cooldownSeconds > 0 || appState.authLoading)
                            .accessibilityIdentifier("login.sendCodeButton")
                        }

                        if !phone.isEmpty && !isPhoneStrictlyValid {
                            Text("请输入以 1 开头的 11 位手机号。")
                                .font(.footnote)
                                .foregroundStyle(.red)
                        }

                        Button("登录") {
                            Task {
                                _ = await appState.loginWithSMS(phone: phone, code: code)
                            }
                        }
                        .buttonStyle(BetweenUsPrimaryButtonStyle())
                        .disabled(!isPhoneStrictlyValid || code.count < 4 || appState.authLoading)
                        .accessibilityIdentifier("login.submitButton")

                        Text("登录即表示你同意《用户协议》与《隐私政策》。")
                            .font(.footnote)
                            .foregroundStyle(BetweenUsTheme.textTertiary)

#if DEBUG
                        if let devCode = appState.loginDebugCode {
                            Text("调试验证码：\(devCode)")
                                .font(.footnote.monospacedDigit())
                                .foregroundStyle(BetweenUsTheme.brandBlue)
                                .textSelection(.enabled)
                        }

                        Button("调试：一键登录") {
                            Task {
                                _ = await appState.quickLoginForDebug()
                            }
                        }
                        .buttonStyle(BetweenUsPrimaryButtonStyle())
                        .disabled(appState.authLoading)
#endif
                    }
                    .betweenUsCardStyle()

                    if let authError = appState.authErrorMessage {
                        Text(authError)
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .textSelection(.enabled)
                            .betweenUsCardStyle()
                    }

#if DEBUG
                    VStack(alignment: .leading, spacing: 8) {
                        Text("调试配置")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textPrimary)
                        TextField("http://127.0.0.1:8000", text: $appState.serverBaseURL)
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .textFieldStyle(.roundedBorder)
                            .onSubmit {
                                appState.persistServerBaseURL()
                            }
                    }
                    .betweenUsCardStyle()
#endif
                }
                .padding(20)
            }
        }
        .task {
            await startCooldownTimer()
        }
    }

    private func inputBlock(title: String, placeholder: String, icon: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(BetweenUsTheme.textSecondary)

            HStack(spacing: 10) {
                Image(systemName: icon)
                    .foregroundStyle(BetweenUsTheme.brandBlue)
                    .frame(width: 18)
                TextField(placeholder, text: text)
                    .keyboardType(title == "手机号" ? .numberPad : .numberPad)
                    .textContentType(title == "手机号" ? .telephoneNumber : .oneTimeCode)
                    .textInputAutocapitalization(.never)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 13)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color.white.opacity(0.86))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(BetweenUsTheme.brandBlue.opacity(0.14), lineWidth: 1)
            )
        }
    }

    private var isPhoneStrictlyValid: Bool {
        let chars = Array(phone)
        guard chars.count == 11 else { return false }
        return chars.first == "1"
    }

    private func sanitizePhone(_ raw: String) -> String {
        String(raw.filter { $0.isNumber }.prefix(11))
    }

    private func sanitizeCode(_ raw: String) -> String {
        String(raw.filter { $0.isNumber }.prefix(6))
    }

    private func startCooldownTimer() async {
        while !Task.isCancelled {
            if cooldownSeconds > 0 {
                cooldownSeconds -= 1
            }
            do {
                try await Task.sleep(nanoseconds: 1_000_000_000)
            } catch {
                break
            }
        }
    }
}
