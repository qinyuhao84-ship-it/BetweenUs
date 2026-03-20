import Foundation

struct AppleLoginRequest: Codable {
    let apple_identity_token: String
}

struct AuthTokenResponse: Codable {
    let user_id: String
    let access_token: String
    let token_type: String
    let expires_in_minutes: Int
}
