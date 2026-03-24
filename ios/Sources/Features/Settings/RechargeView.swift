import StoreKit
import SwiftUI

struct RechargeView: View {
    @EnvironmentObject private var appState: AppState

    @State private var selectedPackageID: String = ""
    @State private var purchasing: Bool = false

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    quotaCard
                    packageCard
                    actionCard

                    if let message = appState.iapStore.statusMessage {
                        Text(message)
                            .font(.footnote)
                            .foregroundStyle(BetweenUsTheme.textSecondary)
                            .betweenUsCardStyle()
                    }

                    if let error = appState.iapStore.errorMessage ?? appState.billingErrorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .textSelection(.enabled)
                            .betweenUsCardStyle()
                    }
                }
                .padding(20)
                .padding(.bottom, 110)
            }
        }
        .navigationTitle("充值中心")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await appState.refreshEntitlements()
            await appState.refreshTopupPackages()
            ensureSelection()
            await appState.iapStore.loadProducts(packageIDs: appState.topupPackages.map(\.package_id))
            await appState.iapStore.syncUnfinishedTransactions(appState: appState)
        }
        .onChange(of: appState.topupPackages.map(\.package_id)) { _, newValue in
            ensureSelection()
            Task {
                await appState.iapStore.loadProducts(packageIDs: newValue)
            }
        }
    }

    private var quotaCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("当前可用额度")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            HStack {
                quotaPill(
                    title: "订阅额度",
                    value: "\(appState.entitlements?.subscription_units_left ?? 0)",
                    tint: BetweenUsTheme.brandBlue
                )
                quotaPill(
                    title: "余额额度",
                    value: "\(appState.entitlements?.payg_units_left ?? 0)",
                    tint: BetweenUsTheme.brandCta
                )
            }
        }
        .betweenUsCardStyle()
    }

    private var packageCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("选择次数包")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            if appState.topupPackages.isEmpty {
                HStack(spacing: 10) {
                    if appState.billingLoading || appState.iapStore.loading {
                        ProgressView()
                    }
                    Text(appState.billingLoading || appState.iapStore.loading ? "正在加载商品..." : "当前没有可购买的次数包")
                        .font(.footnote)
                        .foregroundStyle(BetweenUsTheme.textSecondary)
                }
            } else {
                ForEach(appState.topupPackages) { item in
                    Button {
                        selectedPackageID = item.package_id
                    } label: {
                        HStack(spacing: 10) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.title)
                                    .font(.subheadline.weight(.semibold))
                                    .foregroundStyle(BetweenUsTheme.textPrimary)
                                Text("\(item.units) 次复盘额度")
                                    .font(.caption)
                                    .foregroundStyle(BetweenUsTheme.textSecondary)
                            }
                            Spacer()
                            Text(displayPrice(for: item.package_id))
                                .font(.subheadline.weight(.bold))
                                .foregroundStyle(BetweenUsTheme.brandBlue)
                        }
                        .padding(12)
                        .background(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .fill(Color.white.opacity(selectedPackageID == item.package_id ? 0.96 : 0.78))
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 14, style: .continuous)
                                .stroke(
                                    selectedPackageID == item.package_id ? BetweenUsTheme.brandBlue.opacity(0.35) : Color.clear,
                                    lineWidth: 1
                                )
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .betweenUsCardStyle()
    }

    private var actionCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("使用 Apple App 内购买")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)
            Text("购买完成后，次数会直接同步到当前账号；如果网络抖动，应用会在下次打开时继续补同步。")
                .font(.footnote)
                .foregroundStyle(BetweenUsTheme.textSecondary)

            Button {
                purchasing = true
                Task {
                    defer { purchasing = false }
                    guard !selectedPackageID.isEmpty else { return }
                    if await appState.iapStore.purchase(packageID: selectedPackageID, appState: appState) {
                        await appState.refreshEntitlements()
                    }
                }
            } label: {
                if purchasing {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text("购买并同步")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(BetweenUsPrimaryButtonStyle())
            .disabled(selectedPackageID.isEmpty || purchasing)

            Button("检查未完成购买") {
                Task {
                    await appState.iapStore.syncUnfinishedTransactions(appState: appState)
                    await appState.refreshEntitlements()
                }
            }
            .buttonStyle(BetweenUsPrimaryButtonStyle())
        }
        .betweenUsCardStyle()
    }

    private func quotaPill(title: String, value: String, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(BetweenUsTheme.textSecondary)
            Text(value)
                .font(.title3.weight(.bold))
                .foregroundStyle(tint)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color.white.opacity(0.76))
        )
    }

    private func displayPrice(for packageID: String) -> String {
        if let product = appState.iapStore.productsByID[packageID] {
            return product.displayPrice
        }
        return "待加载"
    }

    private func ensureSelection() {
        if selectedPackageID.isEmpty {
            selectedPackageID = appState.topupPackages.first?.package_id ?? ""
        } else if !appState.topupPackages.contains(where: { $0.package_id == selectedPackageID }) {
            selectedPackageID = appState.topupPackages.first?.package_id ?? ""
        }
    }
}
