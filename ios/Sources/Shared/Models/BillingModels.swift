import Foundation

struct EntitlementResponse: Codable {
    let subscription_units_left: Int
    let payg_units_left: Int
}

struct TopupPackageResponse: Codable, Identifiable {
    let package_id: String
    let title: String
    let units: Int
    let amount_cny: Int
    let price_label: String

    var id: String { package_id }
}

struct CreatePaymentOrderRequest: Codable {
    let package_id: String
    let channel: String
}

struct CreatePaymentOrderResponse: Codable {
    let order_no: String
    let channel: String
    let package_id: String
    let units: Int
    let amount_cny: Int
    let status: String
    let payment_payload: String
    let expires_at: String
}

struct ConfirmPaymentRequest: Codable {
    let order_no: String
    let provider_order_id: String
}

struct ConfirmPaymentResponse: Codable {
    let success: Bool
    let applied: Bool
    let entitlement: EntitlementResponse
}
