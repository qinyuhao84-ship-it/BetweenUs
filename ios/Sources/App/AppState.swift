import Foundation

@MainActor
final class AppState: ObservableObject {
    @Published var currentUserId: String = ""
    @Published var accessToken: String = ""
    @Published var phoneNumber: String = ""
    @Published var phoneMasked: String = ""
    @Published var nickname: String = ""
    @Published var authLoading: Bool = false
    @Published var authErrorMessage: String?
    @Published var loginDebugCode: String?
    @Published var serverBaseURL: String = "http://127.0.0.1:8000"
    @Published var runtimeStatus: RuntimeStatusResponse?
    @Published var runtimeStatusError: String?
    @Published var entitlements: EntitlementResponse?
    @Published var topupPackages: [TopupPackageResponse] = []
    @Published var billingLoading: Bool = false
    @Published var billingErrorMessage: String?
    @Published var latestPaymentOrder: CreatePaymentOrderResponse?
    @Published var sessions: [SessionSummary] = []
    @Published var reports: [String: ConflictReport] = [:]
    @Published var historyLoading: Bool = false
    @Published var historyErrorMessage: String?

    private let defaults = UserDefaults.standard
    private enum StorageKey {
        static let currentUserId = "betweenus.auth.user_id"
        static let accessToken = "betweenus.auth.access_token"
        static let phoneNumber = "betweenus.auth.phone"
        static let phoneMasked = "betweenus.auth.phone_masked"
        static let nickname = "betweenus.auth.nickname"
        static let serverBaseURL = "betweenus.server.base_url"
    }

    init() {
        loadStoredState()
    }

    var isLoggedIn: Bool {
        !currentUserId.isEmpty && !accessToken.isEmpty
    }

    var runtimeStatusMessage: String {
        guard let runtimeStatus else {
            return runtimeStatusError ?? "尚未获取 AI 运行状态"
        }
        if runtimeStatus.isFullyRealPipeline {
            return "真实链路：已启用（ASR + DeepSeek）"
        }
        return "当前为演示链路：至少一个环节在 mock 模式"
    }

    func requestSMSCode(phone: String) async -> Int? {
        guard let baseURL = URL(string: serverBaseURL) else {
            authErrorMessage = "服务地址无效"
            return nil
        }
        authLoading = true
        authErrorMessage = nil
        defer { authLoading = false }

        do {
            let client = APIClient(baseURL: baseURL)
            let response = try await client.sendSMSCode(phone: phone)
            loginDebugCode = response.dev_code
            return response.retry_after_seconds
        } catch {
            authErrorMessage = error.localizedDescription
            return nil
        }
    }

    func loginWithSMS(phone: String, code: String) async -> Bool {
        guard let baseURL = URL(string: serverBaseURL) else {
            authErrorMessage = "服务地址无效"
            return false
        }
        authLoading = true
        authErrorMessage = nil
        defer { authLoading = false }

        do {
            let client = APIClient(baseURL: baseURL)
            let auth = try await client.loginWithSMS(phone: phone, code: code)
            currentUserId = auth.user_id
            accessToken = auth.access_token
            phoneNumber = auth.phone ?? phone
            phoneMasked = auth.phone_masked ?? maskPhone(phone)
            persistAuthState()
            await refreshProfile()
            await refreshRuntimeStatus()
            await refreshEntitlements()
            return true
        } catch {
            authErrorMessage = error.localizedDescription
            return false
        }
    }

    func refreshProfile() async {
        guard isLoggedIn else { return }
        guard let baseURL = URL(string: serverBaseURL) else {
            authErrorMessage = "服务地址无效"
            return
        }
        do {
            let client = APIClient(baseURL: baseURL)
            let profile = try await client.fetchCurrentUser(accessToken: accessToken)
            currentUserId = profile.user_id
            phoneNumber = profile.phone
            phoneMasked = profile.phone_masked
            nickname = profile.nickname
            persistAuthState()
        } catch {
            authErrorMessage = error.localizedDescription
        }
    }

    func updateNickname(_ value: String) async -> Bool {
        guard isLoggedIn else {
            authErrorMessage = "请先登录"
            return false
        }
        guard let baseURL = URL(string: serverBaseURL) else {
            authErrorMessage = "服务地址无效"
            return false
        }
        authLoading = true
        authErrorMessage = nil
        defer { authLoading = false }
        do {
            let client = APIClient(baseURL: baseURL)
            let profile = try await client.updateCurrentUserNickname(accessToken: accessToken, nickname: value)
            nickname = profile.nickname
            persistAuthState()
            return true
        } catch {
            authErrorMessage = error.localizedDescription
            return false
        }
    }

    func refreshRuntimeStatus() async {
        guard let baseURL = URL(string: serverBaseURL) else {
            runtimeStatusError = "服务地址无效"
            return
        }
        do {
            let client = APIClient(baseURL: baseURL)
            runtimeStatus = try await client.fetchRuntimeStatus()
            runtimeStatusError = nil
        } catch {
            runtimeStatusError = error.localizedDescription
        }
    }

#if DEBUG
    func quickLoginForDebug(phone: String = "13800138002") async -> Bool {
        guard let baseURL = URL(string: serverBaseURL) else {
            authErrorMessage = "服务地址无效"
            return false
        }
        authLoading = true
        authErrorMessage = nil
        defer { authLoading = false }

        do {
            let client = APIClient(baseURL: baseURL)
            let sms = try await client.sendSMSCode(phone: phone)
            guard let code = sms.dev_code, !code.isEmpty else {
                throw APIClientError.serverError("开发环境未返回验证码，无法一键登录")
            }
            let auth = try await client.loginWithSMS(phone: phone, code: code)
            currentUserId = auth.user_id
            accessToken = auth.access_token
            phoneNumber = auth.phone ?? phone
            phoneMasked = auth.phone_masked ?? maskPhone(phone)
            persistAuthState()
            await refreshProfile()
            await refreshRuntimeStatus()
            await refreshEntitlements()
            return true
        } catch {
            authErrorMessage = error.localizedDescription
            return false
        }
    }
#endif

    func persistServerBaseURL() {
        defaults.set(serverBaseURL, forKey: StorageKey.serverBaseURL)
    }

    func logout() {
        currentUserId = ""
        accessToken = ""
        phoneNumber = ""
        phoneMasked = ""
        nickname = ""
        loginDebugCode = nil
        authErrorMessage = nil
        entitlements = nil
        topupPackages = []
        billingErrorMessage = nil
        latestPaymentOrder = nil
        sessions = []
        reports = [:]
        historyErrorMessage = nil
        removeStoredAuthState()
    }

    func refreshEntitlements() async {
        guard isLoggedIn else {
            entitlements = nil
            return
        }
        guard let baseURL = URL(string: serverBaseURL) else {
            billingErrorMessage = "服务地址无效"
            return
        }
        do {
            let client = APIClient(baseURL: baseURL)
            entitlements = try await client.fetchEntitlements(accessToken: accessToken)
            billingErrorMessage = nil
        } catch {
            billingErrorMessage = error.localizedDescription
        }
    }

    func refreshTopupPackages() async {
        guard isLoggedIn else {
            topupPackages = []
            return
        }
        guard let baseURL = URL(string: serverBaseURL) else {
            billingErrorMessage = "服务地址无效"
            return
        }
        do {
            let client = APIClient(baseURL: baseURL)
            topupPackages = try await client.listTopupPackages(accessToken: accessToken)
            billingErrorMessage = nil
        } catch {
            billingErrorMessage = error.localizedDescription
        }
    }

    func createTopupOrder(packageID: String, channel: String) async -> CreatePaymentOrderResponse? {
        guard isLoggedIn else {
            billingErrorMessage = "请先登录"
            return nil
        }
        guard let baseURL = URL(string: serverBaseURL) else {
            billingErrorMessage = "服务地址无效"
            return nil
        }

        billingLoading = true
        billingErrorMessage = nil
        defer { billingLoading = false }

        do {
            let client = APIClient(baseURL: baseURL)
            let order = try await client.createPaymentOrder(
                packageID: packageID,
                channel: channel,
                accessToken: accessToken
            )
            latestPaymentOrder = order
            return order
        } catch {
            billingErrorMessage = error.localizedDescription
            return nil
        }
    }

    func confirmTopupOrder(orderNo: String, providerOrderID: String = "") async -> Bool {
        guard isLoggedIn else {
            billingErrorMessage = "请先登录"
            return false
        }
        guard let baseURL = URL(string: serverBaseURL) else {
            billingErrorMessage = "服务地址无效"
            return false
        }

        billingLoading = true
        billingErrorMessage = nil
        defer { billingLoading = false }

        do {
            let client = APIClient(baseURL: baseURL)
            let response = try await client.confirmPaymentOrder(
                orderNo: orderNo,
                providerOrderID: providerOrderID,
                accessToken: accessToken
            )
            entitlements = response.entitlement
            latestPaymentOrder = nil
            return response.success
        } catch {
            billingErrorMessage = error.localizedDescription
            return false
        }
    }

    func requireAccessToken() throws -> String {
        if !isLoggedIn {
            throw APIClientError.serverError("请先完成手机号登录")
        }
        return accessToken
    }

    func save(report: ConflictReport) {
        reports[report.sessionID] = report
        let fallbackTitle = suggestedTitle(forSummary: report.summary)
        let summary = SessionSummary(
            id: report.sessionID,
            title: fallbackTitle,
            createdAt: Date(),
            status: "completed"
        )
        sessions.removeAll { $0.id == summary.id }
        sessions.insert(summary, at: 0)
    }

    func updateSessionTitle(sessionID: String, newTitle: String) async -> Bool {
        guard isLoggedIn else {
            authErrorMessage = "请先登录"
            return false
        }
        let normalized = newTitle
            .components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty else {
            historyErrorMessage = "标题不能为空"
            return false
        }
        guard let baseURL = URL(string: serverBaseURL) else {
            historyErrorMessage = "服务地址无效"
            return false
        }

        do {
            let client = APIClient(baseURL: baseURL)
            let detail = try await client.updateSessionTitle(
                sessionID: sessionID,
                title: String(normalized.prefix(60)),
                userID: currentUserId,
                accessToken: accessToken
            )
            sessions = sessions.map {
                guard $0.id == sessionID else { return $0 }
                return SessionSummary(id: $0.id, title: detail.title, createdAt: $0.createdAt, status: $0.status)
            }
            return true
        } catch {
            historyErrorMessage = error.localizedDescription
            return false
        }
    }

    func suggestedTitle(forSummary summary: String) -> String {
        let cleaned = summary
            .replacingOccurrences(of: "【冲突主线】", with: "")
            .replacingOccurrences(of: "【双方表述】", with: "")
            .replacingOccurrences(of: "【深层诉求】", with: "")
            .replacingOccurrences(of: "【当前卡点】", with: "")
            .replacingOccurrences(of: "\n", with: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        let separators = CharacterSet(charactersIn: "。！？；\n")
        let firstSentence = cleaned.components(separatedBy: separators).first?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let candidate = String(firstSentence.prefix(16))
        if candidate.count >= 6 {
            return candidate
        }
        return "关系修复复盘"
    }

    func refreshHistory() async {
        guard isLoggedIn else {
            historyErrorMessage = "请先登录手机号账号"
            sessions = []
            reports = [:]
            return
        }
        guard let baseURL = URL(string: serverBaseURL) else {
            historyErrorMessage = "服务地址无效"
            return
        }

        historyLoading = true
        historyErrorMessage = nil
        defer { historyLoading = false }

        do {
            let client = APIClient(baseURL: baseURL)
            let remoteSessions = try await client.listSessions(userID: currentUserId, accessToken: accessToken)

            let completedSessions = remoteSessions
                .filter { $0.status == "completed" }
                .sorted { $0.created_at > $1.created_at }

            var fetchedReports: [String: ConflictReport] = [:]
            var fetchedSummaries: [SessionSummary] = []

            for item in completedSessions {
                do {
                    let report = try await client.fetchReport(
                        sessionID: item.session_id,
                        userID: currentUserId,
                        accessToken: accessToken
                    )
                    fetchedReports[item.session_id] = report
                    var resolvedTitle = item.title.trimmingCharacters(in: .whitespacesAndNewlines)
                    let suggested = suggestedTitle(forSummary: report.summary)
                    if shouldAutoRenameTitle(resolvedTitle) {
                        resolvedTitle = suggested
                        _ = try? await client.updateSessionTitle(
                            sessionID: item.session_id,
                            title: suggested,
                            userID: currentUserId,
                            accessToken: accessToken
                        )
                    }
                    fetchedSummaries.append(
                        SessionSummary(
                            id: item.session_id,
                            title: resolvedTitle.isEmpty ? suggested : resolvedTitle,
                            createdAt: item.created_at,
                            status: item.status
                        )
                    )
                } catch {
                    // 单条报告失败不阻断整个历史列表加载。
                    continue
                }
            }

            reports = fetchedReports
            sessions = fetchedSummaries
        } catch {
            historyErrorMessage = error.localizedDescription
        }
    }

    private func loadStoredState() {
        currentUserId = defaults.string(forKey: StorageKey.currentUserId) ?? ""
        accessToken = defaults.string(forKey: StorageKey.accessToken) ?? ""
        phoneNumber = defaults.string(forKey: StorageKey.phoneNumber) ?? ""
        phoneMasked = defaults.string(forKey: StorageKey.phoneMasked) ?? ""
        nickname = defaults.string(forKey: StorageKey.nickname) ?? ""
        if let storedBaseURL = defaults.string(forKey: StorageKey.serverBaseURL), !storedBaseURL.isEmpty {
            serverBaseURL = storedBaseURL
        }
    }

    private func persistAuthState() {
        defaults.set(currentUserId, forKey: StorageKey.currentUserId)
        defaults.set(accessToken, forKey: StorageKey.accessToken)
        defaults.set(phoneNumber, forKey: StorageKey.phoneNumber)
        defaults.set(phoneMasked, forKey: StorageKey.phoneMasked)
        defaults.set(nickname, forKey: StorageKey.nickname)
        defaults.set(serverBaseURL, forKey: StorageKey.serverBaseURL)
    }

    private func removeStoredAuthState() {
        defaults.removeObject(forKey: StorageKey.currentUserId)
        defaults.removeObject(forKey: StorageKey.accessToken)
        defaults.removeObject(forKey: StorageKey.phoneNumber)
        defaults.removeObject(forKey: StorageKey.phoneMasked)
        defaults.removeObject(forKey: StorageKey.nickname)
    }

    private func maskPhone(_ phone: String) -> String {
        guard phone.count == 11 else { return phone }
        let prefix = phone.prefix(3)
        let suffix = phone.suffix(4)
        return "\(prefix)****\(suffix)"
    }

    private func shouldAutoRenameTitle(_ title: String) -> Bool {
        let normalized = title.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if normalized.isEmpty {
            return true
        }
        let genericTitles = [
            "自动复盘",
            "示例音频复盘",
            "冲突复盘",
            "untitled",
        ]
        return genericTitles.contains(where: { normalized == $0.lowercased() })
    }
}
