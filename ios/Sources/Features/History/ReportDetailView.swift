import SwiftUI

struct ReportDetailView: View {
    let report: ConflictReport

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    section(title: "本次复盘摘要", icon: "heart.text.square", lines: [report.summary])
                    section(title: "潜在诉求", icon: "sparkles", lines: report.potentialNeeds)
                    section(title: "修复建议", icon: "wand.and.stars", lines: report.repairSuggestions)
                    section(title: "行动任务", icon: "checklist", lines: report.actionTasks.map { "[ ] \($0.content)" })
                }
                .padding(20)
            }
        }
        .navigationTitle("复盘报告")
    }

    @ViewBuilder
    private func section(title: String, icon: String, lines: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .foregroundStyle(BetweenUsTheme.brandPink)
                Text(title)
                    .font(.headline)
                    .foregroundStyle(BetweenUsTheme.textPrimary)
            }
            ForEach(lines, id: \.self) { line in
                Text("• \(line)")
                    .foregroundStyle(BetweenUsTheme.textSecondary)
                    .textSelection(.enabled)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .betweenUsCardStyle()
    }
}
