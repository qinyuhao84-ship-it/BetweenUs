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
                VStack(alignment: .leading, spacing: 16) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("BetweenUs")
                            .betweenUsDisplayTitle()
                        Text("把“谁对谁错”改成“我们如何更好地理解彼此”。")
                            .betweenUsBodyMuted()
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 30)

                    VStack(spacing: 10) {
                        valueRow(icon: "heart.text.square.fill", text: "不判输赢，只找真正诉求")
                        valueRow(icon: "waveform.path.ecg", text: "真实录音转写，过程可核对")
                        valueRow(icon: "hands.sparkles.fill", text: "给出可执行的修复行动")
                    }
                    .betweenUsCardStyle()

                    VStack(alignment: .leading, spacing: 12) {
                        Text("手机号")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textPrimary)
                        TextField("请输入 11 位手机号", text: $phone)
                            .keyboardType(.numberPad)
                            .textContentType(.telephoneNumber)
                            .textInputAutocapitalization(.never)
                            .textFieldStyle(.roundedBorder)
                            .accessibilityIdentifier("login.phoneField")
                            .onChange(of: phone) { _, newValue in
                                phone = sanitizePhone(newValue)
                            }

                        Text("验证码")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textPrimary)
                        HStack(spacing: 8) {
                            TextField("请输入验证码", text: $code)
                                .keyboardType(.numberPad)
                                .textContentType(.oneTimeCode)
                                .textInputAutocapitalization(.never)
                                .textFieldStyle(.roundedBorder)
                                .accessibilityIdentifier("login.codeField")
                                .onChange(of: code) { _, newValue in
                                    code = sanitizeCode(newValue)
                                }

                            Button(cooldownSeconds > 0 ? "\(cooldownSeconds)s" : "获取验证码") {
                                Task {
                                    if let retryAfter = await appState.requestSMSCode(phone: phone) {
                                        cooldownSeconds = retryAfter
                                    }
                                }
                            }
                            .buttonStyle(BetweenUsPrimaryButtonStyle())
                            .frame(width: 120)
                            .accessibilityIdentifier("login.sendCodeButton")
                            .disabled(!isPhoneStrictlyValid || cooldownSeconds > 0 || appState.authLoading)
                        }

                        if let devCode = appState.loginDebugCode {
                            Text("开发环境验证码：\(devCode)")
                                .font(.footnote.monospacedDigit())
                                .foregroundStyle(BetweenUsTheme.brandBlue)
                                .textSelection(.enabled)
                                .accessibilityIdentifier("login.devCodeText")
                        }

                        if !phone.isEmpty && !isPhoneStrictlyValid {
                            Text("手机号格式不正确，请输入以 1 开头的 11 位手机号。")
                                .font(.footnote)
                                .foregroundStyle(Color.red)
                        }

                        Button("登录") {
                            Task {
                                _ = await appState.loginWithSMS(phone: phone, code: code)
                            }
                        }
                        .buttonStyle(BetweenUsPrimaryButtonStyle())
                        .accessibilityIdentifier("login.submitButton")
                        .disabled(!isPhoneStrictlyValid || code.count < 4 || appState.authLoading)

#if DEBUG
                        Button("开发测试：一键登录") {
                            Task {
                                _ = await appState.quickLoginForDebug()
                            }
                        }
                        .buttonStyle(BetweenUsPrimaryButtonStyle())
                        .accessibilityIdentifier("login.debugQuickLoginButton")
                        .disabled(appState.authLoading)
#endif
                    }
                    .betweenUsCardStyle()

                    if let authError = appState.authErrorMessage {
                        Text(authError)
                            .font(.footnote)
                            .foregroundStyle(Color.red)
                            .textSelection(.enabled)
                            .betweenUsCardStyle()
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("服务地址")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textPrimary)
                        TextField("http://127.0.0.1:8000", text: $appState.serverBaseURL)
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .textFieldStyle(.roundedBorder)
                            .accessibilityIdentifier("login.serverField")
                            .onSubmit {
                                appState.persistServerBaseURL()
                            }
                    }
                    .betweenUsCardStyle()
                }
                .padding(20)
            }
        }
        .task {
            await startCooldownTimer()
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

    @ViewBuilder
    private func valueRow(icon: String, text: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .foregroundStyle(BetweenUsTheme.brandBlue)
            Text(text)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(BetweenUsTheme.textPrimary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
