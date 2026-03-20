import SwiftUI

struct RecordView: View {
    @EnvironmentObject private var appState: AppState
    @StateObject private var viewModel = RecordViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("目标是帮助你看见真正诉求，而不是判输赢。")
                    .font(.headline)
                    .foregroundStyle(.secondary)

                VStack(alignment: .leading, spacing: 12) {
                    Text(viewModel.statusText)
                        .font(.title3.weight(.semibold))
                    ProgressView(value: Double(viewModel.progressPercent), total: 100)
                    Text("进度 \(viewModel.progressPercent)%")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .monospacedDigit()
                }
                .padding(16)
                .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16, style: .continuous))

                Button {
                    if viewModel.isRecording {
                        viewModel.stopAndAnalyze(appState: appState)
                    } else {
                        viewModel.startRecording()
                    }
                } label: {
                    HStack {
                        Image(systemName: viewModel.isRecording ? "stop.circle.fill" : "record.circle.fill")
                        Text(viewModel.isRecording ? "结束录音并开始复盘" : "开始录音")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(viewModel.isRecording ? .red : .blue)

                if let error = viewModel.errorMessage {
                    Text(error)
                        .foregroundStyle(.red)
                        .textSelection(.enabled)
                }

                if let report = viewModel.latestReport {
                    NavigationLink {
                        ReportDetailView(report: report)
                    } label: {
                        Label("查看最新复盘报告", systemImage: "doc.text.magnifyingglass")
                    }
                }
            }
            .padding(20)
        }
    }
}
