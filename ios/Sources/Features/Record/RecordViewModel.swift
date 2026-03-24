import Foundation
import SwiftUI

@MainActor
final class RecordViewModel: ObservableObject {
    @Published var isRecording = false
    @Published var statusText = "点击开始录音"
    @Published var progressPercent = 0
    @Published var progressDisplay: Double = 0
    @Published var errorMessage: String?
    @Published var latestReport: ConflictReport?

    private let recorderService = RecorderService()
    private var startedAt: Date?
    private let minRecordingSeconds: TimeInterval = 2

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
                setProgress(0, animated: false)
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

        let elapsed = Date().timeIntervalSince(startedAt ?? Date())
        if elapsed < minRecordingSeconds {
            errorMessage = "录音时间过短，请至少录制 2 秒再结束。"
            statusText = "等待录音"
            setProgress(0)
            try? FileManager.default.removeItem(at: audioURL)
            return
        }

        let duration = max(1, Int(Date().timeIntervalSince(startedAt ?? Date()) / 60.0))
        statusText = "正在分析，请稍候"
        setProgress(10)

        Task {
            defer {
                try? FileManager.default.removeItem(at: audioURL)
            }
            await analyzeAudio(audioURL: audioURL, duration: duration, title: "关系修复复盘", appState: appState)
        }
    }

    private func analyzeAudio(audioURL: URL, duration: Int, title: String, appState: AppState) async {
        do {
            guard let baseURL = URL(string: appState.serverBaseURL) else {
                throw APIClientError.serverError("服务地址无效")
            }
            let userID = appState.currentUserId
            let accessToken = try appState.requireAccessToken()

            let client = APIClient(baseURL: baseURL)
            let created = try await client.createSession(
                title: title,
                userID: userID,
                accessToken: accessToken
            )

            setProgress(20)
            _ = try await client.uploadSessionAudio(
                sessionID: created.session_id,
                audioURL: audioURL,
                userID: userID,
                accessToken: accessToken
            )

            setProgress(35)
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
            let suggestedTitle = appState.suggestedTitle(forSummary: report.summary)
            _ = try? await client.updateSessionTitle(
                sessionID: created.session_id,
                title: suggestedTitle,
                userID: userID,
                accessToken: accessToken
            )
            await appState.refreshHistory()
            setProgress(100)
            statusText = "分析完成"
        } catch {
            errorMessage = normalizedErrorMessage(error.localizedDescription)
            statusText = "分析失败"
        }
    }

    private func waitUntilCompleted(
        sessionID: String,
        userID: String,
        accessToken: String,
        client: APIClient
    ) async throws {
        for _ in 0 ..< 180 {
            let progress = try await client.fetchProgress(
                sessionID: sessionID,
                userID: userID,
                accessToken: accessToken
            )
            setProgress(progress.percent)
            statusText = statusTextForStage(progress.stage)
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

    private func statusTextForStage(_ stage: String) -> String {
        switch stage {
        case "queued":
            return "任务已提交，等待执行"
        case "transcribing":
            return "正在转写录音"
        case "analyzing":
            return "正在生成复盘报告"
        case "rendering":
            return "正在整理结果"
        case "completed":
            return "分析完成"
        case "failed":
            return "分析失败"
        default:
            return "正在分析，请稍候"
        }
    }

    private func normalizedErrorMessage(_ raw: String) -> String {
        if raw.contains("静音") {
            return "没有检测到有效语音，请靠近麦克风并重试。"
        }
        if raw.contains("invalid audio format") || raw.contains("audio convert failed") {
            return "录音格式无法识别，请重试一次。"
        }
        if raw.contains("任务系统暂时不可用") {
            return "任务队列暂时繁忙，请稍后再试。"
        }
        return raw
    }

    private func setProgress(_ value: Int, animated: Bool = true) {
        let clamped = min(max(value, 0), 100)
        progressPercent = clamped
        if animated {
            withAnimation(.interactiveSpring(response: 0.45, dampingFraction: 0.9, blendDuration: 0.25)) {
                progressDisplay = Double(clamped) / 100.0
            }
        } else {
            progressDisplay = Double(clamped) / 100.0
        }
    }
}
