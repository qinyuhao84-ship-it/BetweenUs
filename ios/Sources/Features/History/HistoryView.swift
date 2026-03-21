import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var appState: AppState
    @State private var editingSession: SessionSummary?
    @State private var editingTitle: String = ""
    @State private var titleSaving: Bool = false

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            List {
                Section {
                    headerCard
                        .listRowInsets(EdgeInsets(top: 4, leading: 14, bottom: 4, trailing: 14))
                        .listRowBackground(Color.clear)
                }

                if !appState.isLoggedIn {
                    Section {
                        noticeCard(title: "请先登录", body: "登录后才能读取你的历史复盘记录。")
                    }
                } else if appState.historyLoading && appState.sessions.isEmpty {
                    Section {
                        HStack(spacing: 10) {
                            ProgressView()
                            Text("正在加载历史记录")
                                .foregroundStyle(BetweenUsTheme.textSecondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .betweenUsCardStyle()
                    }
                } else if let error = appState.historyErrorMessage, appState.sessions.isEmpty {
                    Section {
                        VStack(alignment: .leading, spacing: 10) {
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
                } else if appState.sessions.isEmpty {
                    Section {
                        noticeCard(title: "暂无复盘记录", body: "完成一次复盘后，这里会自动沉淀可回看的关系修复轨迹。")
                    }
                } else {
                    Section("历史复盘") {
                        ForEach(appState.sessions) { session in
                            if let report = appState.reports[session.id] {
                                NavigationLink {
                                    ReportDetailView(report: report)
                                } label: {
                                    sessionRow(session: session, report: report)
                                }
                                .buttonStyle(.plain)
                                .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                    Button("改标题") {
                                        editingSession = session
                                        editingTitle = session.title
                                    }
                                    .tint(BetweenUsTheme.brandBlue)
                                }
                            }
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .listStyle(.insetGrouped)
        }
        .refreshable {
            await appState.refreshHistory()
        }
        .task {
            if appState.sessions.isEmpty && appState.isLoggedIn {
                await appState.refreshHistory()
            }
        }
        .sheet(item: $editingSession) { session in
            NavigationStack {
                VStack(alignment: .leading, spacing: 14) {
                    Text("为这次复盘起一个更容易回忆的标题。")
                        .font(.subheadline)
                        .foregroundStyle(BetweenUsTheme.textSecondary)

                    TextField("例如：家务分工争执复盘", text: $editingTitle)
                        .textFieldStyle(.roundedBorder)

                    Button {
                        titleSaving = true
                        Task {
                            defer { titleSaving = false }
                            let ok = await appState.updateSessionTitle(sessionID: session.id, newTitle: editingTitle)
                            if ok {
                                editingSession = nil
                            }
                        }
                    } label: {
                        if titleSaving {
                            ProgressView()
                                .frame(maxWidth: .infinity)
                        } else {
                            Text("保存标题")
                                .frame(maxWidth: .infinity)
                        }
                    }
                    .buttonStyle(BetweenUsPrimaryButtonStyle())
                    .disabled(titleSaving)

                    Spacer()
                }
                .padding(20)
                .background(BetweenUsGradientBackground())
                .navigationTitle("编辑标题")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("取消") {
                            editingSession = nil
                        }
                    }
                }
            }
        }
    }

    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("关系修复轨迹")
                .betweenUsHeadline()
            Text("每次复盘都会沉淀成可回看的证据：冲突主线、深层诉求和下一步行动。")
                .betweenUsBodyMuted()

            HStack(spacing: 8) {
                statPill(icon: "doc.text", text: "共 \(appState.sessions.count) 份")
                statPill(icon: "square.and.pencil", text: "标题可编辑")
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .betweenUsCardStyle()
    }

    private func sessionRow(session: SessionSummary, report: ConflictReport) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(session.title)
                    .font(.headline)
                    .foregroundStyle(BetweenUsTheme.textPrimary)
                    .lineLimit(2)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(BetweenUsTheme.textTertiary)
            }

            Text(report.summary.replacingOccurrences(of: "\n", with: " "))
                .font(.subheadline)
                .foregroundStyle(BetweenUsTheme.textSecondary)
                .lineLimit(2)

            HStack(spacing: 10) {
                Label(
                    session.createdAt.formatted(date: .numeric, time: .shortened),
                    systemImage: "calendar.badge.clock"
                )
                .font(.caption)
                .foregroundStyle(BetweenUsTheme.textTertiary)

                Spacer()

                Label("可回看", systemImage: "bookmark.fill")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(BetweenUsTheme.brandBlue)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .betweenUsCardStyle()
    }

    private func statPill(icon: String, text: String) -> some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
            Text(text)
        }
        .font(.caption.weight(.semibold))
        .foregroundStyle(BetweenUsTheme.textPrimary)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            Capsule()
                .fill(Color.white.opacity(0.72))
        )
    }

    private func noticeCard(title: String, body: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)
            Text(body)
                .font(.footnote)
                .foregroundStyle(BetweenUsTheme.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .betweenUsCardStyle()
    }
}
