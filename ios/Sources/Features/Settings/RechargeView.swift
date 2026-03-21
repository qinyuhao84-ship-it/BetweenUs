import SwiftUI

struct RechargeView: View {
    @EnvironmentObject private var appState: AppState
    @Environment(\.openURL) private var openURL

    @State private var selectedPackageID: String = ""
    @State private var selectedChannel: String = "alipay"
    @State private var pendingOrder: CreatePaymentOrderResponse?
    @State private var confirmLoading: Bool = false
    @State private var successBanner: String?

    var body: some View {
        ZStack {
            BetweenUsGradientBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    quotaCard
                    packageCard
                    channelCard
                    actionCard

                    if let pendingOrder {
                        pendingOrderCard(order: pendingOrder)
                    }

                    if let error = appState.billingErrorMessage {
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
        }
        .onChange(of: appState.topupPackages.count) { _, _ in
            ensureSelection()
        }
        .alert("充值成功", isPresented: Binding(
            get: { successBanner != nil },
            set: { newValue in
                if !newValue {
                    successBanner = nil
                }
            }
        )) {
            Button("知道了", role: .cancel) {}
        } message: {
            Text(successBanner ?? "")
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
            Text("选择套餐")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            if appState.topupPackages.isEmpty {
                HStack(spacing: 10) {
                    if appState.billingLoading {
                        ProgressView()
                    }
                    Text(appState.billingLoading ? "正在拉取套餐..." : "当前没有可购买套餐")
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
                                Text("\(item.units) 单位")
                                    .font(.caption)
                                    .foregroundStyle(BetweenUsTheme.textSecondary)
                            }
                            Spacer()
                            Text(item.price_label)
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

    private var channelCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("支付方式")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            HStack(spacing: 10) {
                channelButton(id: "alipay", title: "支付宝")
                channelButton(id: "wechat", title: "微信支付")
            }
        }
        .betweenUsCardStyle()
    }

    private var actionCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("创建订单")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)
            Text("下单后会拉起对应支付应用，支付完成再回到这里确认到账。")
                .font(.footnote)
                .foregroundStyle(BetweenUsTheme.textSecondary)

            Button {
                Task {
                    guard !selectedPackageID.isEmpty else { return }
                    if let order = await appState.createTopupOrder(packageID: selectedPackageID, channel: selectedChannel) {
                        pendingOrder = order
                        if let url = URL(string: order.payment_payload), !order.payment_payload.hasPrefix("mock://") {
                            openURL(url)
                        }
                    }
                }
            } label: {
                if appState.billingLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text("去支付")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(BetweenUsPrimaryButtonStyle())
            .disabled(selectedPackageID.isEmpty || appState.billingLoading)
        }
        .betweenUsCardStyle()
    }

    private func pendingOrderCard(order: CreatePaymentOrderResponse) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("待确认订单")
                .font(.headline)
                .foregroundStyle(BetweenUsTheme.textPrimary)

            detailRow("订单号", order.order_no)
            detailRow("支付渠道", order.channel == "wechat" ? "微信支付" : "支付宝")
            detailRow("金额", "¥\(String(format: "%.2f", Double(order.amount_cny) / 100.0))")
            detailRow("额度", "\(order.units) 单位")
            detailRow("失效时间", order.expires_at)

            if order.payment_payload.hasPrefix("mock://") {
                Text("当前为开发模式，支付将走模拟确认。")
                    .font(.footnote)
                    .foregroundStyle(BetweenUsTheme.textSecondary)
            }

            Text(order.payment_payload)
                .font(.caption.monospaced())
                .foregroundStyle(BetweenUsTheme.textTertiary)
                .textSelection(.enabled)
                .padding(.top, 2)

            Button {
                confirmLoading = true
                Task {
                    defer { confirmLoading = false }
                    let providerID = order.payment_payload.hasPrefix("mock://")
                        ? "mock_\(Int(Date().timeIntervalSince1970))"
                        : ""
                    let ok = await appState.confirmTopupOrder(orderNo: order.order_no, providerOrderID: providerID)
                    if ok {
                        successBanner = "充值已到账，余额额度已更新。"
                        pendingOrder = nil
                        await appState.refreshEntitlements()
                    }
                }
            } label: {
                if confirmLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text(order.payment_payload.hasPrefix("mock://") ? "模拟支付成功" : "我已完成支付，确认到账")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(BetweenUsPrimaryButtonStyle())
            .disabled(confirmLoading)
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

    private func channelButton(id: String, title: String) -> some View {
        Button {
            selectedChannel = id
        } label: {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(selectedChannel == id ? .white : BetweenUsTheme.textPrimary)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 11)
                .background(
                    RoundedRectangle(cornerRadius: 12, style: .continuous)
                        .fill(
                            selectedChannel == id
                                ? AnyShapeStyle(BetweenUsTheme.ctaGradient)
                                : AnyShapeStyle(Color.white.opacity(0.78))
                        )
                )
        }
        .buttonStyle(.plain)
    }

    private func detailRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(BetweenUsTheme.textSecondary)
            Spacer()
            Text(value)
                .foregroundStyle(BetweenUsTheme.textPrimary)
                .textSelection(.enabled)
        }
        .font(.footnote)
    }

    private func ensureSelection() {
        if selectedPackageID.isEmpty {
            selectedPackageID = appState.topupPackages.first?.package_id ?? ""
        } else if !appState.topupPackages.contains(where: { $0.package_id == selectedPackageID }) {
            selectedPackageID = appState.topupPackages.first?.package_id ?? ""
        }
    }
}
