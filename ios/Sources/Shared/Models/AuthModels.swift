import Foundation

struct AppleLoginRequest: Codable {
    let apple_identity_token: String
    let authorization_code: String
    let full_name: String
}

struct AuthTokenResponse: Codable {
    let user_id: String
    let access_token: String
    let token_type: String
    let expires_in_minutes: Int
    let phone: String?
    let phone_masked: String?
    let has_bound_phone: Bool
}

struct SendSMSCodeRequest: Codable {
    let phone: String
}

struct SendSMSCodeResponse: Codable {
    let sent: Bool
    let expires_in_seconds: Int
    let retry_after_seconds: Int
}

struct PhoneLoginRequest: Codable {
    let phone: String
    let code: String
}

struct PhoneBindRequest: Codable {
    let phone: String
    let code: String
}

struct UserProfileResponse: Codable {
    let user_id: String
    let phone: String?
    let phone_masked: String?
    let has_bound_phone: Bool
    let nickname: String
    let created_at: Date
    let last_login_at: Date
}

struct UpdateProfileRequest: Codable {
    let nickname: String
}

struct DeleteAccountResponse: Codable {
    let success: Bool
    let apple_revoked: Bool
}
