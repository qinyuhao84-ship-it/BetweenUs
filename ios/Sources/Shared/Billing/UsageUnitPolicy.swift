import Foundation

struct UsageUnitPolicy {
    static func units(for durationMinutes: Int) -> Int {
        guard durationMinutes > 0 else { return 0 }
        return Int(ceil(Double(durationMinutes) / 60.0))
    }
}
