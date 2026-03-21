import Foundation

struct AppleLoginRequest: Codable {
    let apple_identity_token: String
}

struct AuthTokenResponse: Codable {
    let user_id: String
    let access_token: String
    let token_type: String
    let expires_in_minutes: Int
    let phone: String?
    let phone_masked: String?
}

struct SendSMSCodeRequest: Codable {
    let phone: String
}

struct SendSMSCodeResponse: Codable {
    let sent: Bool
    let expires_in_seconds: Int
    let retry_after_seconds: Int
    let dev_code: String?
}

struct PhoneLoginRequest: Codable {
    let phone: String
    let code: String
}

struct UserProfileResponse: Codable {
    let user_id: String
    let phone: String
    let phone_masked: String
    let nickname: String
    let created_at: Date
    let last_login_at: Date
}

struct UpdateProfileRequest: Codable {
    let nickname: String
}
