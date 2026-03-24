import SwiftUI

struct ReportDetailView: View {
    let report: ConflictReport
    @State private var showDetailedReport = false

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView(.vertical, showsIndicators: true) {
                LazyVStack(alignment: .leading, spacing: 16) {
                    summaryCard
                        .id("summary")
                    section(title: "双方的深层诉求", icon: "sparkles", lines: report.potentialNeeds)
                        .id("needs")
                    section(title: "修复建议", icon: "wand.and.stars", lines: report.repairSuggestions)
                        .id("suggestions")
                    section(title: "本次行动清单", icon: "checklist", lines: report.actionTasks.map(\.content))
                        .id("actions")
                    if !report.transcriptExcerpt.isEmpty {
                        section(title: "对话摘录（用于核对）", icon: "waveform", lines: [report.transcriptExcerpt], selectable: true)
                            .id("transcript")
                    }
                }
                .padding(20)
                .padding(.bottom, 120)
            }
            .scrollIndicators(.visible)
            .scrollBounceBehavior(.basedOnSize)
        }
        .navigationTitle("复盘报告")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("详细报告") {
                    showDetailedReport = true
                }
                .font(.subheadline.weight(.semibold))
            }
        }
        .sheet(isPresented: $showDetailedReport) {
            NavigationStack {
                DetailedPsychologyReportView(report: report)
            }
        }
    }

    @ViewBuilder
    private func section(title: String, icon: String, lines: [String], selectable: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .foregroundStyle(BetweenUsTheme.brandPink)
                Text(title)
                    .font(.headline)
                    .foregroundStyle(BetweenUsTheme.textPrimary)
            }
            ForEach(Array(lines.enumerated()), id: \.offset) { idx, line in
                HStack(alignment: .top, spacing: 8) {
                    Text("\(idx + 1).")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(BetweenUsTheme.brandBlue)
                    if selectable {
                        Text(line)
                            .foregroundStyle(BetweenUsTheme.textSecondary)
                            .textSelection(.enabled)
                    } else {
                        Text(line)
                            .foregroundStyle(BetweenUsTheme.textSecondary)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .betweenUsCardStyle()
    }

    private var summaryCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "text.quote")
                    .foregroundStyle(BetweenUsTheme.brandPink)
                Text("复盘总览")
                    .font(.headline)
                    .foregroundStyle(BetweenUsTheme.textPrimary)
            }

            ForEach(Array(summaryLines.enumerated()), id: \.offset) { _, line in
                Text(line)
                    .font(.subheadline)
                    .foregroundStyle(BetweenUsTheme.textSecondary)
                    .lineSpacing(3)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .betweenUsCardStyle()
    }

    private var summaryLines: [String] {
        let byNewline = report.summary
            .split(whereSeparator: \.isNewline)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        if byNewline.count >= 2 {
            return byNewline
        }

        let byLabel = report.summary
            .replacingOccurrences(of: "【", with: "\n【")
            .split(whereSeparator: \.isNewline)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
        if byLabel.count >= 2 {
            return byLabel
        }
        return [report.summary]
    }
}

private struct DetailedPsychologyReportView: View {
    let report: ConflictReport

    private var contentLines: [String] {
        let raw = report.detailedReport.trimmingCharacters(in: .whitespacesAndNewlines)
        if raw.isEmpty {
            return [
                "当前详细报告暂未生成。",
                "请稍后重试，或重新进行一次复盘以获取完整心理学分析。",
            ]
        }
        return raw
            .split(whereSeparator: \.isNewline)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("情感学与心理学详细报告")
                        .font(.title3.weight(.bold))
                        .foregroundStyle(BetweenUsTheme.textPrimary)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    ForEach(Array(contentLines.enumerated()), id: \.offset) { _, line in
                        Text(line)
                            .font(.subheadline)
                            .lineSpacing(4)
                            .foregroundStyle(BetweenUsTheme.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(20)
                .padding(.bottom, 120)
                .betweenUsCardStyle()
                .padding(20)
            }
        }
        .navigationTitle("详细报告")
        .navigationBarTitleDisplayMode(.inline)
    }
}
