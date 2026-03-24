import Foundation

enum AppConfig {
    #if DEBUG
    private static let debugDefaultAPIBaseURL = "http://127.0.0.1:8000"
    #else
    private static let debugDefaultAPIBaseURL = "https://api.betweenus.app"
    #endif

    static let apiBaseURL: String = {
        let raw = ProcessInfo.processInfo.environment["BETWEENUS_API_BASE_URL"]?.trimmingCharacters(in: .whitespacesAndNewlines)
        let selected = (raw?.isEmpty == false) ? raw! : debugDefaultAPIBaseURL
        let normalized: String
        if selected.hasSuffix("/") {
            normalized = String(selected.dropLast())
        } else {
            normalized = selected
        }

        #if DEBUG
        return normalized
        #else
        if !normalized.lowercased().hasPrefix("https://") {
            fatalError("Release 环境必须使用 HTTPS API 地址")
        }
        return normalized
        #endif
    }()

    static let privacyPolicyURL = configuredHTTPSURL(
        envKey: "BETWEENUS_PRIVACY_POLICY_URL",
        defaultValue: "https://betweenus.app/legal/privacy/"
    )

    static let userAgreementURL = configuredHTTPSURL(
        envKey: "BETWEENUS_USER_AGREEMENT_URL",
        defaultValue: "https://betweenus.app/legal/terms/"
    )

    static let privacyChoicesURL = configuredHTTPSURL(
        envKey: "BETWEENUS_PRIVACY_CHOICES_URL",
        defaultValue: "https://betweenus.app/legal/privacy-choices/"
    )

    static let supportURL = configuredHTTPSURL(
        envKey: "BETWEENUS_SUPPORT_URL",
        defaultValue: "https://betweenus.app/support/"
    )

    static let marketingURL = configuredHTTPSURL(
        envKey: "BETWEENUS_MARKETING_URL",
        defaultValue: "https://betweenus.app/"
    )

    static let supportEmail: String = {
        let raw = ProcessInfo.processInfo.environment["BETWEENUS_SUPPORT_EMAIL"]?.trimmingCharacters(in: .whitespacesAndNewlines)
        return (raw?.isEmpty == false) ? raw! : "qinyuhao84@gmail.com"
    }()

    static let supportEmailURL: URL = {
        guard let url = URL(string: "mailto:\(supportEmail)") else {
            fatalError("支持邮箱格式无效")
        }
        return url
    }()

    private static func configuredHTTPSURL(envKey: String, defaultValue: String) -> URL {
        let raw = ProcessInfo.processInfo.environment[envKey]?.trimmingCharacters(in: .whitespacesAndNewlines)
        let selected = (raw?.isEmpty == false) ? raw! : defaultValue
        guard let url = URL(string: selected) else {
            fatalError("\(envKey) 不是合法 URL")
        }
        #if DEBUG
        return url
        #else
        if url.scheme?.lowercased() != "https" {
            fatalError("\(envKey) 在 Release 环境必须使用 HTTPS")
        }
        return url
        #endif
    }
}
