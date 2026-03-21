import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var appState: AppState
    @State private var editingSession: SessionSummary?
    @State private var editingTitle: String = ""
    @State private var titleSaving: Bool = false

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    if appState.isLoggedIn {
                        weeklyTrendCard
                    }

                    if !appState.isLoggedIn {
                        noticeCard(title: "请先登录", body: "登录后才能读取你的历史复盘记录。")
                    } else if appState.historyLoading && appState.sessions.isEmpty {
                        HStack(spacing: 10) {
                            ProgressView()
                            Text("正在加载历史记录")
                                .foregroundStyle(BetweenUsTheme.textSecondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .betweenUsCardStyle()
                    } else if let error = appState.historyErrorMessage, appState.sessions.isEmpty {
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
                    } else if appState.sessions.isEmpty {
                        noticeCard(title: "暂无复盘记录", body: "完成一次复盘后，这里会出现你的关系修复轨迹。")
                    } else {
                        Text("历史复盘")
                            .font(.headline)
                            .foregroundStyle(BetweenUsTheme.textSecondary)
                            .padding(.horizontal, 4)

                        ForEach(appState.sessions) { session in
                            if let report = appState.reports[session.id] {
                                sessionRow(session: session, report: report)
                            }
                        }
                    }
                }
                .padding(20)
                .padding(.bottom, 120)
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

    private var weeklyTrendCard: some View {
        let buckets = weeklyBuckets
        let latest = buckets.last?.count ?? 0
        let previous = buckets.dropLast().last?.count ?? 0
        let trend = latest - previous

        return VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("最近一周")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(BetweenUsTheme.textSecondary)
                    Text("你们吵了 \(latest) 次")
                        .font(.title3.weight(.bold))
                        .foregroundStyle(BetweenUsTheme.textPrimary)
                }
                Spacer()
                Text(trendLabel(trend))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(trend > 0 ? .orange : BetweenUsTheme.brandBlue)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 5)
                    .background(
                        Capsule()
                            .fill(Color.white.opacity(0.72))
                    )
            }

            HStack(alignment: .bottom, spacing: 8) {
                ForEach(buckets) { bucket in
                    VStack(spacing: 6) {
                        RoundedRectangle(cornerRadius: 7, style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: [BetweenUsTheme.brandCta.opacity(0.9), BetweenUsTheme.brandBlue.opacity(0.95)],
                                    startPoint: .bottom,
                                    endPoint: .top
                                )
                            )
                            .frame(height: barHeight(for: bucket.count, max: buckets.map(\.count).max() ?? 1))

                        Text(bucket.shortLabel)
                            .font(.caption2)
                            .foregroundStyle(BetweenUsTheme.textTertiary)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
            .frame(height: 124, alignment: .bottom)
        }
        .betweenUsCardStyle()
    }

    private var weeklyBuckets: [WeekBucket] {
        let calendar = Calendar.current
        let now = Date()
        let currentWeekStart = calendar.dateInterval(of: .weekOfYear, for: now)?.start ?? now

        var starts: [Date] = []
        for offset in stride(from: 7, through: 0, by: -1) {
            if let d = calendar.date(byAdding: .weekOfYear, value: -offset, to: currentWeekStart) {
                starts.append(d)
            }
        }

        return starts.map { start in
            let end = calendar.date(byAdding: .day, value: 7, to: start) ?? start
            let count = appState.sessions.filter { $0.createdAt >= start && $0.createdAt < end }.count
            return WeekBucket(startDate: start, count: count)
        }
    }

    private func sessionRow(session: SessionSummary, report: ConflictReport) -> some View {
        NavigationLink {
            ReportDetailView(report: report)
        } label: {
            VStack(alignment: .leading, spacing: 9) {
                HStack(alignment: .top, spacing: 8) {
                    Text(session.title)
                        .font(.headline)
                        .foregroundStyle(BetweenUsTheme.textPrimary)
                        .lineLimit(2)
                    Spacer()
                    Button {
                        editingSession = session
                        editingTitle = session.title
                    } label: {
                        Image(systemName: "square.and.pencil")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(BetweenUsTheme.brandBlue)
                            .padding(6)
                    }
                    .buttonStyle(.plain)
                }

                Text(report.summary.replacingOccurrences(of: "\n", with: " "))
                    .font(.subheadline)
                    .foregroundStyle(BetweenUsTheme.textSecondary)
                    .lineLimit(2)

                Label(
                    session.createdAt.formatted(date: .numeric, time: .shortened),
                    systemImage: "calendar.badge.clock"
                )
                .font(.caption)
                .foregroundStyle(BetweenUsTheme.textTertiary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .betweenUsCardStyle()
        }
        .buttonStyle(.plain)
    }

    private func barHeight(for count: Int, max maxCount: Int) -> CGFloat {
        let safeMax = Swift.max(maxCount, 1)
        let minHeight: CGFloat = 10
        let dynamic = CGFloat(count) / CGFloat(safeMax) * 78
        return Swift.max(minHeight, dynamic)
    }

    private func trendLabel(_ delta: Int) -> String {
        if delta == 0 {
            return "与上周持平"
        }
        if delta > 0 {
            return "较上周 +\(delta)"
        }
        return "较上周 \(delta)"
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

private struct WeekBucket: Identifiable {
    let id = UUID()
    let startDate: Date
    let count: Int

    var shortLabel: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "M/d"
        return formatter.string(from: startDate)
    }
}
