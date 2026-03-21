import Foundation

struct SessionSummary: Identifiable, Codable, Hashable {
    let id: String
    let title: String
    let createdAt: Date
    let status: String
}

struct SessionCreateRequest: Codable {
    let title: String
}

struct SessionCreateResponse: Codable {
    let session_id: String
    let title: String
    let status: String
}

struct SessionFinishRequest: Codable {
    let duration_minutes: Int
    let consent_acknowledged: Bool
}

struct SessionProgress: Codable {
    let stage: String
    let percent: Int
}

struct SessionFinishResponse: Codable {
    let session_id: String
    let status: String
    let progress: SessionProgress
}

struct SessionProgressResponse: Codable {
    let stage: String
    let percent: Int
}

struct SessionAudioUploadResponse: Codable {
    let session_id: String
    let uploaded: Bool
    let bytes_received: Int
}

struct SessionListItemResponse: Codable {
    let session_id: String
    let title: String
    let status: String
    let created_at: Date
}

struct SessionDetailResponse: Codable {
    let session_id: String
    let title: String
    let status: String
    let created_at: Date
    let duration_minutes: Int
    let failure_reason: String
    let transcript_excerpt: String
}

struct SessionTitleUpdateRequest: Codable {
    let title: String
}
