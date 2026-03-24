import Foundation
import Security

struct StoredAuthState: Codable {
    let currentUserId: String
    let accessToken: String
    let phoneNumber: String
    let phoneMasked: String
    let nickname: String
}

final class SecureAuthStore {
    private let service: String
    private let account: String

    init(
        service: String = "com.betweenus.auth",
        account: String = "primary"
    ) {
        self.service = service
        self.account = account
    }

    func load() -> StoredAuthState? {
        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else {
            return nil
        }
        return try? JSONDecoder().decode(StoredAuthState.self, from: data)
    }

    func save(_ state: StoredAuthState) {
        guard let data = try? JSONEncoder().encode(state) else { return }

        let update: [String: Any] = [kSecValueData as String: data]
        let status = SecItemUpdate(baseQuery as CFDictionary, update as CFDictionary)
        if status == errSecItemNotFound {
            var create = baseQuery
            create[kSecValueData as String] = data
            SecItemAdd(create as CFDictionary, nil)
        }
    }

    func clear() {
        SecItemDelete(baseQuery as CFDictionary)
    }

    private var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
    }
}
