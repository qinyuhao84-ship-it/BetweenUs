import XCTest
@testable import BetweenUs

final class APIClientURLTests: XCTestCase {
    func testEndpointURLSupportsLeadingSlashPath() throws {
        let client = APIClient(baseURL: URL(string: "http://127.0.0.1:8000")!)
        let url = try client.endpointURL(path: "/v1/auth/apple-login")
        XCTAssertEqual(url.absoluteString, "http://127.0.0.1:8000/v1/auth/apple-login")
    }

    func testEndpointURLSupportsPathWithoutLeadingSlash() throws {
        let client = APIClient(baseURL: URL(string: "http://127.0.0.1:8000/")!)
        let url = try client.endpointURL(path: "v1/sessions")
        XCTAssertEqual(url.absoluteString, "http://127.0.0.1:8000/v1/sessions")
    }
}
