import XCTest
@testable import BetweenUs

final class UsageUnitPolicyTests: XCTestCase {
    func testRoundsUpByHourUnit() {
        XCTAssertEqual(UsageUnitPolicy.units(for: 45), 1)
        XCTAssertEqual(UsageUnitPolicy.units(for: 60), 1)
        XCTAssertEqual(UsageUnitPolicy.units(for: 61), 2)
        XCTAssertEqual(UsageUnitPolicy.units(for: 121), 3)
    }

    func testReturnsZeroForInvalidMinutes() {
        XCTAssertEqual(UsageUnitPolicy.units(for: 0), 0)
        XCTAssertEqual(UsageUnitPolicy.units(for: -1), 0)
    }
}
