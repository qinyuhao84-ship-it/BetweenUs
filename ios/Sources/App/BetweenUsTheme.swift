import SwiftUI

enum BetweenUsTheme {
    static let pageTop = Color(hex: 0xF6FFFC)
    static let pageMid = Color(hex: 0xEEF8FF)
    static let pageBottom = Color(hex: 0xF3F8FF)

    static let brandBlue = Color(hex: 0x3B82F6)
    static let brandBlueSoft = Color(hex: 0x93C5FD)
    static let brandPink = Color(hex: 0x2DD4BF)
    static let brandPinkSoft = Color(hex: 0xCCFBF1)
    static let brandCta = Color(hex: 0x34D399)
    static let brandTeal = Color(hex: 0x0EA5E9)

    static let textPrimary = Color(hex: 0x0F172A)
    static let textSecondary = Color(hex: 0x334155)
    static let textTertiary = Color(hex: 0x64748B)
    static let card = Color.white.opacity(0.92)
    static let cardStrong = Color.white.opacity(0.98)
    static let outline = Color.white.opacity(0.72)
    static let shadow = Color(hex: 0x0F172A, opacity: 0.1)

    static let pageGradient = LinearGradient(
        colors: [pageTop, pageMid, pageBottom],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    static let ctaGradient = LinearGradient(
        colors: [brandCta, brandBlue],
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
                .frame(width: 340, height: 340)
                .offset(x: 170, y: -280)
                .blur(radius: 18)

            Circle()
                .fill(BetweenUsTheme.brandBlueSoft.opacity(0.36))
                .frame(width: 320, height: 320)
                .offset(x: -170, y: -250)
                .blur(radius: 18)

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
            .shadow(color: BetweenUsTheme.shadow, radius: 20, x: 0, y: 10)
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
                color: (isDanger ? Color.red.opacity(0.18) : BetweenUsTheme.brandBlue.opacity(0.22)),
                radius: configuration.isPressed ? 8 : 16,
                x: 0,
                y: configuration.isPressed ? 4 : 10
            )
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.easeOut(duration: 0.2), value: configuration.isPressed)
    }
}

struct BetweenUsSmoothProgressBar: View {
    let progress: Double
    @State private var glowPosition: CGFloat = -0.4

    var body: some View {
        GeometryReader { geo in
            let clamped = min(max(progress, 0), 1)
            let width = max(geo.size.width * clamped, 0)

            ZStack(alignment: .leading) {
                Capsule()
                    .fill(Color.black.opacity(0.06))

                Capsule()
                    .fill(
                        LinearGradient(
                            colors: [BetweenUsTheme.brandCta, BetweenUsTheme.brandBlue],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
                    .frame(width: width)
                    .overlay(alignment: .leading) {
                        Capsule()
                            .fill(
                                LinearGradient(
                                    colors: [Color.white.opacity(0), Color.white.opacity(0.32), Color.white.opacity(0)],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: max(width * 0.35, 28))
                            .offset(x: max(width - max(width * 0.35, 28), 0) * glowPosition)
                            .opacity(width > 18 ? 1 : 0)
                    }
                    .shadow(color: BetweenUsTheme.brandBlue.opacity(0.2), radius: 6, x: 0, y: 2)
                    .animation(.interactiveSpring(response: 0.45, dampingFraction: 0.88), value: width)
            }
            .clipShape(Capsule())
            .onAppear {
                withAnimation(.linear(duration: 1.6).repeatForever(autoreverses: false)) {
                    glowPosition = 1.2
                }
            }
        }
        .frame(height: 10)
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
