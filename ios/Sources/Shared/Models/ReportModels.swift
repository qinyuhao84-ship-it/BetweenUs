import Foundation

struct ActionTaskItem: Codable, Identifiable, Hashable {
    let task_id: String
    let content: String
    let done: Bool

    var id: String { task_id }
}

struct ConflictReport: Codable, Hashable {
    let session_id: String
    let summary: String
    let transcript_excerpt: String?
    let potential_needs: [String]
    let repair_suggestions: [String]
    let action_tasks: [ActionTaskItem]
    let detailed_report: String?

    var sessionID: String { session_id }
    var transcriptExcerpt: String { transcript_excerpt ?? "" }
    var potentialNeeds: [String] { potential_needs }
    var repairSuggestions: [String] { repair_suggestions }
    var actionTasks: [ActionTaskItem] { action_tasks }
    var detailedReport: String { detailed_report ?? "" }
}
