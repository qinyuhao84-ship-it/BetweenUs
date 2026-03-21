import SwiftUI

struct ReportDetailView: View {
    let report: ConflictReport

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollViewReader { proxy in
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
                .onAppear {
#if DEBUG
                    if ProcessInfo.processInfo.environment["BETWEENUS_AUTOSCROLL_REPORT"] == "1" {
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                            withAnimation(.easeInOut(duration: 0.45)) {
                                proxy.scrollTo("actions", anchor: .bottom)
                            }
                        }
                    }
#endif
                }
            }
        }
        .navigationTitle("复盘报告")
        .navigationBarTitleDisplayMode(.inline)
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
