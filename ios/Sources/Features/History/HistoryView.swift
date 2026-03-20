import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                if appState.historyLoading && appState.sessions.isEmpty {
                    ProgressView("正在加载历史记录")
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                if let error = appState.historyErrorMessage, appState.sessions.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(error)
                            .foregroundStyle(.red)
                            .textSelection(.enabled)
                        Button("重试加载") {
                            Task {
                                await appState.refreshHistory()
                            }
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                if appState.sessions.isEmpty {
                    Text("暂无复盘记录")
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                ForEach(appState.sessions) { session in
                    if let report = appState.reports[session.id] {
                        NavigationLink {
                            ReportDetailView(report: report)
                        } label: {
                            VStack(alignment: .leading, spacing: 8) {
                                Text(session.title)
                                    .font(.headline)
                                    .lineLimit(2)
                                Text(session.createdAt.formatted(date: .abbreviated, time: .shortened))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(16)
                            .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .padding(20)
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
