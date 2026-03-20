import SwiftUI

struct ReportDetailView: View {
    let report: ConflictReport

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                section(title: "本次复盘摘要", lines: [report.summary])
                section(title: "潜在诉求", lines: report.potentialNeeds)
                section(title: "修复建议", lines: report.repairSuggestions)
                section(title: "行动任务", lines: report.actionTasks.map { "[ ] \($0.content)" })
            }
            .padding(20)
        }
        .navigationTitle("复盘报告")
    }

    @ViewBuilder
    private func section(title: String, lines: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
            ForEach(lines, id: \.self) { line in
                Text("• \(line)")
                    .textSelection(.enabled)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}
