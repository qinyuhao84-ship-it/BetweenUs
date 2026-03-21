import Foundation

@MainActor
final class RecordViewModel: ObservableObject {
    @Published var isRecording = false
    @Published var statusText = "点击开始录音"
    @Published var progressPercent = 0
    @Published var errorMessage: String?
    @Published var latestReport: ConflictReport?

    private let recorderService = RecorderService()
    private var startedAt: Date?

    func startRecording() {
        Task {
            let granted = await recorderService.requestPermission()
            guard granted else {
                errorMessage = "麦克风权限未开启，请在系统设置中允许。"
                return
            }

            do {
                try recorderService.start()
                startedAt = Date()
                isRecording = true
                statusText = "录音中..."
                progressPercent = 0
                errorMessage = nil
            } catch {
                errorMessage = "启动录音失败：\(error.localizedDescription)"
            }
        }
    }

    func stopAndAnalyze(appState: AppState) {
        guard isRecording else { return }
        guard let audioURL = recorderService.stop() else {
            isRecording = false
            errorMessage = "录音文件未生成，请重试。"
            statusText = "分析失败"
            return
        }
        isRecording = false

        let duration = max(1, Int(Date().timeIntervalSince(startedAt ?? Date()) / 60.0))
        statusText = "正在分析，请稍候"
        progressPercent = 10

        Task {
            defer {
                try? FileManager.default.removeItem(at: audioURL)
            }
            do {
                guard let baseURL = URL(string: appState.serverBaseURL) else {
                    throw APIClientError.serverError("服务地址无效")
                }
                let userID = appState.currentUserId
                let accessToken = try appState.requireAccessToken()

                let client = APIClient(baseURL: baseURL)
                let created = try await client.createSession(
                    title: "自动复盘",
                    userID: userID,
                    accessToken: accessToken
                )

                progressPercent = 20
                _ = try await client.uploadSessionAudio(
                    sessionID: created.session_id,
                    audioURL: audioURL,
                    userID: userID,
                    accessToken: accessToken
                )

                progressPercent = 35
                _ = try await client.finishSession(
                    sessionID: created.session_id,
                    durationMinutes: duration,
                    userID: userID,
                    accessToken: accessToken
                )

                try await waitUntilCompleted(
                    sessionID: created.session_id,
                    userID: userID,
                    accessToken: accessToken,
                    client: client
                )
                let report = try await client.fetchReport(
                    sessionID: created.session_id,
                    userID: userID,
                    accessToken: accessToken
                )
                latestReport = report
                appState.save(report: report)
                await appState.refreshHistory()
                progressPercent = 100
                statusText = "分析完成"
            } catch {
                errorMessage = error.localizedDescription
                statusText = "分析失败"
            }
        }
    }

    func runAutomatedFlowIfNeeded(appState: AppState) async {
        guard ProcessInfo.processInfo.environment["BETWEENUS_AUTORUN_E2E"] == "1" else {
            return
        }
        guard !isRecording else { return }

        startRecording()

        for _ in 0 ..< 30 {
            if isRecording {
                break
            }
            try? await Task.sleep(nanoseconds: 100_000_000)
        }

        if isRecording {
            stopAndAnalyze(appState: appState)
        }
    }

    private func waitUntilCompleted(
        sessionID: String,
        userID: String,
        accessToken: String,
        client: APIClient
    ) async throws {
        for _ in 0 ..< 60 {
            let progress = try await client.fetchProgress(
                sessionID: sessionID,
                userID: userID,
                accessToken: accessToken
            )
            progressPercent = min(max(progress.percent, 0), 100)
            if progress.stage == "completed" {
                return
            }
            if progress.stage == "failed" {
                if let detail = try? await client.fetchSessionDetail(
                    sessionID: sessionID,
                    userID: userID,
                    accessToken: accessToken
                ), !detail.failure_reason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    throw APIClientError.serverError(detail.failure_reason)
                }
                throw APIClientError.serverError("复盘任务失败，请稍后重试。")
            }
            try await Task.sleep(nanoseconds: 1_000_000_000)
        }
        throw APIClientError.serverError("分析超时，请稍后在历史页查看结果。")
    }
}
