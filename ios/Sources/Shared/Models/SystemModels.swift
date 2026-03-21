import Foundation

struct RuntimeStatusResponse: Codable {
    let ai_provider_mode: String
    let asr_provider: String
    let asr_mock_enabled: Bool
    let llm_mock_enabled: Bool
    let queue_eager_mode: Bool

    var isFullyRealPipeline: Bool {
        !asr_mock_enabled && !llm_mock_enabled
    }
}
