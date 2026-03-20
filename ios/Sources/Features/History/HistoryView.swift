import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(spacing: 12) {
                    if appState.historyLoading && appState.sessions.isEmpty {
                        ProgressView("正在加载历史记录")
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .betweenUsCardStyle()
                    }

                    if let error = appState.historyErrorMessage, appState.sessions.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(error)
                                .font(.footnote)
                                .foregroundStyle(.red)
                                .textSelection(.enabled)

                            Button("重试加载") {
                                Task {
                                    await appState.refreshHistory()
                                }
                            }
                            .buttonStyle(BetweenUsPrimaryButtonStyle())
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .betweenUsCardStyle()
                    }

                    if appState.sessions.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("暂无复盘记录")
                                .font(.headline)
                                .foregroundStyle(BetweenUsTheme.textPrimary)
                            Text("做一次录音复盘后，这里会自动出现历史。")
                                .font(.footnote)
                                .foregroundStyle(BetweenUsTheme.textSecondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .betweenUsCardStyle()
                    }

                    ForEach(appState.sessions) { session in
                        if let report = appState.reports[session.id] {
                            NavigationLink {
                                ReportDetailView(report: report)
                            } label: {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(session.title)
                                        .font(.headline)
                                        .foregroundStyle(BetweenUsTheme.textPrimary)
                                        .lineLimit(2)

                                    HStack {
                                        Image(systemName: "clock")
                                            .foregroundStyle(BetweenUsTheme.brandBlue)
                                        Text(session.createdAt.formatted(date: .abbreviated, time: .shortened))
                                            .font(.caption)
                                            .foregroundStyle(BetweenUsTheme.textSecondary)
                                    }
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .betweenUsCardStyle()
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(20)
            }
        }
        .refreshable {
            await appState.refreshHistory()
        }
        .task {
            if appState.sessions.isEmpty {
                await appState.refreshHistory()
            }
        }
    }
}
