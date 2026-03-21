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
                        Text("欢迎使用 BetweenUs")
                            .font(.largeTitle.weight(.bold))
                            .foregroundStyle(BetweenUsTheme.textPrimary)
                        Text("先完成手机号登录，再开始录音复盘。")
                            .foregroundStyle(BetweenUsTheme.textSecondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 32)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("手机号")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textPrimary)
                        TextField("请输入 11 位手机号", text: $phone)
                            .keyboardType(.numberPad)
                            .textInputAutocapitalization(.never)
                            .textFieldStyle(.roundedBorder)
                            .onChange(of: phone) { _, newValue in
                                phone = sanitizePhone(newValue)
                            }

                        Text("验证码")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textPrimary)
                        HStack(spacing: 8) {
                            TextField("请输入验证码", text: $code)
                                .keyboardType(.numberPad)
                                .textInputAutocapitalization(.never)
                                .textFieldStyle(.roundedBorder)
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
                            .disabled(!isPhoneValid || cooldownSeconds > 0 || appState.authLoading)
                        }

                        if let devCode = appState.loginDebugCode {
                            Text("开发环境验证码：\(devCode)")
                                .font(.footnote.monospacedDigit())
                                .foregroundStyle(BetweenUsTheme.brandBlue)
                                .textSelection(.enabled)
                        }

                        Button("登录") {
                            Task {
                                _ = await appState.loginWithSMS(phone: phone, code: code)
                            }
                        }
                        .buttonStyle(BetweenUsPrimaryButtonStyle())
                        .disabled(!isPhoneValid || code.count < 4 || appState.authLoading)
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

    private var isPhoneValid: Bool {
        phone.count == 11
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
