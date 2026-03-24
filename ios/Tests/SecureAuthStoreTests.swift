import XCTest
@testable import BetweenUs

final class SecureAuthStoreTests: XCTestCase {
    func testSaveLoadAndClear() {
        let store = SecureAuthStore(
            service: "com.betweenus.tests.auth",
            account: "save-load-clear"
        )
        store.clear()

        let initial = StoredAuthState(
            currentUserId: "u_demo",
            accessToken: "token-demo",
            phoneNumber: "13800138000",
            phoneMasked: "138****8000",
            nickname: "测试用户"
        )

        store.save(initial)
        XCTAssertEqual(store.load()?.currentUserId, "u_demo")
        XCTAssertEqual(store.load()?.phoneMasked, "138****8000")

        store.clear()
        XCTAssertNil(store.load())
    }
}
