import SwiftUI

enum BetweenUsTheme {
    static let pageTop = Color(hex: 0xFDFBFF)
    static let pageMid = Color(hex: 0xF6F8FF)
    static let pageBottom = Color(hex: 0xFFF5FA)

    static let brandBlue = Color(hex: 0x4C7DFF)
    static let brandBlueSoft = Color(hex: 0x8EB9FF)
    static let brandPink = Color(hex: 0xFF7EC2)
    static let brandPinkSoft = Color(hex: 0xFFD4EC)

    static let textPrimary = Color(hex: 0x1D2742)
    static let textSecondary = Color(hex: 0x5C6A88)
    static let card = Color.white.opacity(0.82)
    static let cardStrong = Color.white.opacity(0.92)
    static let outline = Color.white.opacity(0.72)
    static let shadow = Color(hex: 0x92A8DF, opacity: 0.28)

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
                .frame(width: 280, height: 280)
                .offset(x: 130, y: -250)
                .blur(radius: 6)

            Circle()
                .fill(BetweenUsTheme.brandBlueSoft.opacity(0.36))
                .frame(width: 260, height: 260)
                .offset(x: -150, y: -220)
                .blur(radius: 8)
        }
    }
}

struct BetweenUsCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(16)
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(BetweenUsTheme.card)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .stroke(BetweenUsTheme.outline, lineWidth: 1)
            )
            .shadow(color: BetweenUsTheme.shadow, radius: 22, x: 0, y: 14)
    }
}

struct BetweenUsPrimaryButtonStyle: ButtonStyle {
    var isDanger: Bool = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline.weight(.semibold))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .fill(isDanger ? BetweenUsTheme.dangerGradient : BetweenUsTheme.ctaGradient)
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
}

extension Color {
    init(hex: UInt, opacity: Double = 1) {
        let red = Double((hex >> 16) & 0xFF) / 255.0
        let green = Double((hex >> 8) & 0xFF) / 255.0
        let blue = Double(hex & 0xFF) / 255.0
        self.init(.sRGB, red: red, green: green, blue: blue, opacity: opacity)
    }
}
