import Foundation

@MainActor
final class AppState: ObservableObject {
    @Published var currentUserId: String = "u_demo_ios"
    @Published var accessToken: String = ""
    @Published var serverBaseURL: String = "http://127.0.0.1:8000"
    @Published var sessions: [SessionSummary] = []
    @Published var reports: [String: ConflictReport] = [:]
    @Published var historyLoading: Bool = false
    @Published var historyErrorMessage: String?

    func save(report: ConflictReport) {
        reports[report.sessionID] = report
        let summary = SessionSummary(
            id: report.sessionID,
            title: report.summary,
            createdAt: Date(),
            status: "completed"
        )
        sessions.removeAll { $0.id == summary.id }
        sessions.insert(summary, at: 0)
    }

    func refreshHistory() async {
        guard let baseURL = URL(string: serverBaseURL) else {
            historyErrorMessage = "服务地址无效"
            return
        }

        historyLoading = true
        historyErrorMessage = nil
        defer { historyLoading = false }

        do {
            let client = APIClient(baseURL: baseURL)
            let token = try await ensureAuthorized(client: client)
            let remoteSessions = try await client.listSessions(userID: currentUserId, accessToken: token)

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
                        accessToken: token
                    )
                    fetchedReports[item.session_id] = report
                    fetchedSummaries.append(
                        SessionSummary(
                            id: item.session_id,
                            title: report.summary,
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

    private func ensureAuthorized(client: APIClient) async throws -> String {
        if !accessToken.isEmpty {
            return accessToken
        }

        let seed = "ios-demo-\(currentUserId)"
        let auth = try await client.appleLogin(identityToken: seed)
        currentUserId = auth.user_id
        accessToken = auth.access_token
        return auth.access_token
    }
}
