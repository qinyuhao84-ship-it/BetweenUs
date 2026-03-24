import Foundation

struct EntitlementResponse: Codable {
    let subscription_units_left: Int
    let payg_units_left: Int
}

struct TopupPackageResponse: Codable, Identifiable {
    let package_id: String
    let title: String
    let units: Int

    var id: String { package_id }
}

struct VerifyIAPRequest: Codable {
    let signed_transaction_info: String
}

struct VerifyIAPResponse: Codable {
    let success: Bool
    let applied: Bool
    let entitlement: EntitlementResponse
}
