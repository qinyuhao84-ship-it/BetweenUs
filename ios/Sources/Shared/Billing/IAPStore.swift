import Foundation
import StoreKit

@MainActor
final class IAPStore: ObservableObject {
    @Published private(set) var productsByID: [String: Product] = [:]
    @Published var loading: Bool = false
    @Published var errorMessage: String?
    @Published var statusMessage: String?

    private var updatesTask: Task<Void, Never>?

    deinit {
        updatesTask?.cancel()
    }

    func startObserving(appState: AppState) {
        if updatesTask != nil { return }
        updatesTask = Task {
            for await update in Transaction.updates {
                do {
                    let transaction = try Self.requireVerified(update)
                    _ = await sync(
                        transaction: transaction,
                        signedTransactionInfo: update.jwsRepresentation,
                        appState: appState
                    )
                } catch {
                    errorMessage = error.localizedDescription
                }
            }
        }
    }

    func loadProducts(packageIDs: [String]) async {
        let ids = Array(Set(packageIDs)).sorted()
        guard !ids.isEmpty else {
            productsByID = [:]
            return
        }

        loading = true
        errorMessage = nil
        defer { loading = false }

        do {
            let products = try await Product.products(for: ids)
            productsByID = Dictionary(uniqueKeysWithValues: products.map { ($0.id, $0) })
        } catch {
            errorMessage = "加载购买项目失败：\(error.localizedDescription)"
        }
    }

    func purchase(packageID: String, appState: AppState) async -> Bool {
        guard let product = productsByID[packageID] else {
            errorMessage = "商品尚未加载完成"
            return false
        }

        do {
            let result = try await product.purchase()
            switch result {
            case .success(let verification):
                let transaction = try Self.requireVerified(verification)
                return await sync(
                    transaction: transaction,
                    signedTransactionInfo: verification.jwsRepresentation,
                    appState: appState
                )
            case .pending:
                statusMessage = "购买已提交，等待 Apple 确认。"
                return false
            case .userCancelled:
                statusMessage = "已取消购买。"
                return false
            @unknown default:
                errorMessage = "购买状态未知，请稍后在额度页确认。"
                return false
            }
        } catch {
            errorMessage = "购买失败：\(error.localizedDescription)"
            return false
        }
    }

    func syncUnfinishedTransactions(appState: AppState) async {
        guard appState.isLoggedIn else { return }

        for await verification in Transaction.unfinished {
            do {
                let transaction = try Self.requireVerified(verification)
                _ = await sync(
                    transaction: transaction,
                    signedTransactionInfo: verification.jwsRepresentation,
                    appState: appState
                )
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }

    private func sync(transaction: Transaction, signedTransactionInfo: String, appState: AppState) async -> Bool {
        guard appState.isLoggedIn else {
            statusMessage = "购买已完成，请先登录账号同步额度。"
            return false
        }

        guard let baseURL = URL(string: appState.serverBaseURL) else {
            errorMessage = "服务地址无效"
            return false
        }

        do {
            let client = APIClient(baseURL: baseURL)
            let response = try await client.verifyIAP(
                accessToken: try appState.requireAccessToken(),
                signedTransactionInfo: signedTransactionInfo
            )
            appState.entitlements = response.entitlement
            statusMessage = response.applied ? "次数已到账。" : "该购买记录已同步。"
            await transaction.finish()
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    private static func requireVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .verified(let value):
            return value
        case .unverified(_, let error):
            throw error
        }
    }
}
