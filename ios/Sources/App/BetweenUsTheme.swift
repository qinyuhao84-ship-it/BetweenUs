import SwiftUI

enum BetweenUsTheme {
    static let pageTop = Color(hex: 0xF8FAFC)
    static let pageMid = Color(hex: 0xEEF4FF)
    static let pageBottom = Color(hex: 0xFDF4FF)

    static let brandBlue = Color(hex: 0x2563EB)
    static let brandBlueSoft = Color(hex: 0x7AA2FF)
    static let brandPink = Color(hex: 0xD946EF)
    static let brandPinkSoft = Color(hex: 0xF5D0FE)
    static let brandCta = Color(hex: 0xF97316)

    static let textPrimary = Color(hex: 0x0F172A)
    static let textSecondary = Color(hex: 0x475569)
    static let textTertiary = Color(hex: 0x64748B)
    static let card = Color.white.opacity(0.88)
    static let cardStrong = Color.white.opacity(0.96)
    static let outline = Color.white.opacity(0.75)
    static let shadow = Color(hex: 0x2563EB, opacity: 0.16)

    static let pageGradient = LinearGradient(
        colors: [pageTop, pageMid, pageBottom],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static let ctaGradient = LinearGradient(
        colors: [brandPink, brandBlue],
        startPoint: .leading,
        endPoint: .trailing
    )

    static let dangerGradient = LinearGradient(
        colors: [Color(hex: 0xFF5D8C), Color(hex: 0xFF4065)],
        startPoint: .leading,
        endPoint: .trailing
    )
}

struct BetweenUsGradientBackground: View {
    var body: some View {
        ZStack {
            BetweenUsTheme.pageGradient
                .ignoresSafeArea()

            Circle()
                .fill(BetweenUsTheme.brandPinkSoft.opacity(0.44))
                .frame(width: 320, height: 320)
                .offset(x: 150, y: -290)
                .blur(radius: 10)

            Circle()
                .fill(BetweenUsTheme.brandBlueSoft.opacity(0.36))
                .frame(width: 300, height: 300)
                .offset(x: -180, y: -260)
                .blur(radius: 12)

            RoundedRectangle(cornerRadius: 42, style: .continuous)
                .fill(BetweenUsTheme.brandBlue.opacity(0.07))
                .frame(width: 420, height: 220)
                .rotationEffect(.degrees(-16))
                .offset(x: -170, y: 220)
                .blur(radius: 2)
        }
    }
}

struct BetweenUsCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: [BetweenUsTheme.cardStrong, BetweenUsTheme.card],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .stroke(BetweenUsTheme.outline, lineWidth: 1)
            )
            .shadow(color: BetweenUsTheme.shadow, radius: 18, x: 0, y: 12)
    }
}

struct BetweenUsPrimaryButtonStyle: ButtonStyle {
    var isDanger: Bool = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.weight(.semibold))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 15)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(isDanger ? BetweenUsTheme.dangerGradient : BetweenUsTheme.ctaGradient)
                    .overlay(
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .stroke(Color.white.opacity(0.2), lineWidth: 1)
                    )
            )
            .shadow(
                color: (isDanger ? Color.red.opacity(0.18) : BetweenUsTheme.brandPink.opacity(0.26)),
                radius: configuration.isPressed ? 8 : 16,
                x: 0,
                y: configuration.isPressed ? 4 : 10
            )
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.easeOut(duration: 0.2), value: configuration.isPressed)
    }
}

extension View {
    func betweenUsCardStyle() -> some View {
        modifier(BetweenUsCardModifier())
    }

    func betweenUsDisplayTitle() -> some View {
        self
            .font(.system(size: 42, weight: .bold, design: .rounded))
            .tracking(-0.4)
            .foregroundStyle(BetweenUsTheme.textPrimary)
    }

    func betweenUsHeadline() -> some View {
        self
            .font(.system(size: 24, weight: .bold, design: .rounded))
            .tracking(-0.2)
            .foregroundStyle(BetweenUsTheme.textPrimary)
    }

    func betweenUsBodyMuted() -> some View {
        self
            .font(.system(size: 15, weight: .medium, design: .rounded))
            .foregroundStyle(BetweenUsTheme.textSecondary)
            .lineSpacing(2)
    }
}

extension Color {
    init(hex: UInt, opacity: Double = 1) {
        let red = Double((hex >> 16) & 0xFF) / 255.0
        let green = Double((hex >> 8) & 0xFF) / 255.0
        let blue = Double(hex & 0xFF) / 255.0
        self.init(.sRGB, red: red, green: green, blue: blue, opacity: opacity)
    }
}
