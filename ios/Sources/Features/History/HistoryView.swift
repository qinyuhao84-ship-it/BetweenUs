import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(spacing: 12) {
                    headerCard

                    if !appState.isLoggedIn {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("请先登录")
                                .font(.headline)
                                .foregroundStyle(BetweenUsTheme.textPrimary)
                            Text("登录后才能读取你的历史复盘记录。")
                                .font(.footnote)
                                .foregroundStyle(BetweenUsTheme.textSecondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .betweenUsCardStyle()
                    }

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
                            Text("完成一次复盘后，这里会自动出现可追踪的关系修复轨迹。")
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
                                    HStack {
                                        Image(systemName: "calendar.badge.clock")
                                            .foregroundStyle(BetweenUsTheme.brandBlue)
                                        Text(session.createdAt.formatted(date: .abbreviated, time: .shortened))
                                            .font(.caption)
                                            .foregroundStyle(BetweenUsTheme.textSecondary)
                                    }

                                    Text(session.title)
                                        .font(.headline)
                                        .foregroundStyle(BetweenUsTheme.textPrimary)
                                        .lineLimit(2)
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
            if appState.sessions.isEmpty && appState.isLoggedIn {
                await appState.refreshHistory()
            }
        }
    }

    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("关系修复轨迹")
                .betweenUsHeadline()
            Text("每次复盘都会沉淀成可回看的证据：触发点、隐藏诉求、下一步行动。")
                .betweenUsBodyMuted()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .betweenUsCardStyle()
    }
}
