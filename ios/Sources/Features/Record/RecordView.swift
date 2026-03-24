import SwiftUI

struct RecordView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = RecordViewModel()

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if !appState.isLoggedIn {
                        Text("请先在登录页完成手机号验证，再开始录音。")
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(Color.red)
                            .betweenUsCardStyle()
                    }

                    heroSection

                    statusSection

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
                    .accessibilityIdentifier("record.toggleButton")
                    .disabled(!appState.isLoggedIn)

                    if let error = viewModel.errorMessage {
                        VStack(alignment: .leading, spacing: 8) {
                            Label("本次复盘中断", systemImage: "exclamationmark.triangle.fill")
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(Color.red)
                            Text(error)
                                .font(.footnote)
                                .foregroundStyle(Color.red)
                                .textSelection(.enabled)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
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
                        .accessibilityIdentifier("record.latestReportButton")
                        .betweenUsCardStyle()
                    }
                }
                .padding(20)
            }
        }
    }

    private var heroSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "heart.text.square.fill")
                    .foregroundStyle(BetweenUsTheme.brandPink)
                Text("先听懂彼此，再一起变好")
                    .font(.headline)
                    .foregroundStyle(BetweenUsTheme.textPrimary)
            }

            Text("你负责真实表达，我们负责把情绪噪音翻译成清晰、温和、可执行的修复步骤。")
                .font(.subheadline.weight(.medium))
                .foregroundStyle(BetweenUsTheme.textSecondary)
                .lineSpacing(2)

            HStack(spacing: 8) {
                promisePill(icon: "ear.fill", text: "听见没说出口的在意")
                promisePill(icon: "checkmark.seal.fill", text: "给出可执行下一步")
            }
        }
        .betweenUsCardStyle()
    }

    private var statusSection: some View {
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

            BetweenUsSmoothProgressBar(progress: viewModel.progressDisplay)
        }
        .betweenUsCardStyle()
    }

    @ViewBuilder
    private func promisePill(icon: String, text: String) -> some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
                .font(.caption.weight(.semibold))
            Text(text)
                .font(.caption.weight(.semibold))
                .lineLimit(1)
        }
        .foregroundStyle(BetweenUsTheme.textPrimary)
        .padding(.horizontal, 10)
        .padding(.vertical, 7)
        .background(
            Capsule()
                .fill(Color.white.opacity(0.7))
        )
    }
}
