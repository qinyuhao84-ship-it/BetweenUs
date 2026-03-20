import SwiftUI

struct RecordView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = RecordViewModel()

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 8) {
                            Image(systemName: "heart.fill")
                                .foregroundStyle(BetweenUsTheme.brandPink)
                            Text("温柔复盘")
                                .font(.headline)
                                .foregroundStyle(BetweenUsTheme.textPrimary)
                        }
                        Text("目标是帮助你看见真正诉求，而不是判输赢。")
                            .font(.subheadline.weight(.medium))
                            .foregroundStyle(BetweenUsTheme.textSecondary)
                    }
                    .betweenUsCardStyle()

                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text("当前状态")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(BetweenUsTheme.textSecondary)
                            Spacer()
                            Text("进度 \(viewModel.progressPercent)%")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(BetweenUsTheme.brandBlue)
                                .monospacedDigit()
                        }

                        Text(viewModel.statusText)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(BetweenUsTheme.textPrimary)

                        ProgressView(value: Double(viewModel.progressPercent), total: 100)
                            .tint(BetweenUsTheme.brandBlue)
                    }
                    .betweenUsCardStyle()

                    Button {
                        if viewModel.isRecording {
                            viewModel.stopAndAnalyze(appState: appState)
                        } else {
                            viewModel.startRecording()
                        }
                    } label: {
                        HStack(spacing: 10) {
                            Image(systemName: viewModel.isRecording ? "stop.circle.fill" : "record.circle.fill")
                            Text(viewModel.isRecording ? "结束录音并开始复盘" : "开始录音")
                        }
                        .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(BetweenUsPrimaryButtonStyle(isDanger: viewModel.isRecording))

                    if let error = viewModel.errorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(Color.red)
                            .textSelection(.enabled)
                            .betweenUsCardStyle()
                    }

                    if let report = viewModel.latestReport {
                        NavigationLink {
                            ReportDetailView(report: report)
                        } label: {
                            HStack {
                                Label("查看最新复盘报告", systemImage: "doc.text.magnifyingglass")
                                    .font(.headline)
                                    .foregroundStyle(BetweenUsTheme.textPrimary)
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .foregroundStyle(BetweenUsTheme.textSecondary)
                            }
                        }
                        .buttonStyle(.plain)
                        .betweenUsCardStyle()
                    }
                }
                .padding(20)
            }
        }
    }
}
