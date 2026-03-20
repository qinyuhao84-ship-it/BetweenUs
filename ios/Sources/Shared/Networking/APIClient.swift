import Foundation

enum APIClientError: Error, LocalizedError {
    case invalidResponse
    case serverError(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "服务返回异常，请稍后重试。"
        case .serverError(let message):
            return message
        }
    }
}

struct APIClient {
    let baseURL: URL

    func appleLogin(identityToken: String) async throws -> AuthTokenResponse {
        let body = AppleLoginRequest(apple_identity_token: identityToken)
        return try await request(
            path: "/v1/auth/apple-login",
            method: "POST",
            userID: "",
            accessToken: nil,
            body: body,
            response: AuthTokenResponse.self
        )
    }

    func createSession(title: String, userID: String, accessToken: String?) async throws -> SessionCreateResponse {
        let body = SessionCreateRequest(title: title)
        return try await request(
            path: "/v1/sessions",
            method: "POST",
            userID: userID,
            accessToken: accessToken,
            body: body,
            response: SessionCreateResponse.self
        )
    }

    func finishSession(
        sessionID: String,
        durationMinutes: Int,
        userID: String,
        accessToken: String?
    ) async throws -> SessionFinishResponse {
        let body = SessionFinishRequest(duration_minutes: durationMinutes, consent_acknowledged: true)
        return try await request(
            path: "/v1/sessions/\(sessionID)/finish",
            method: "POST",
            userID: userID,
            accessToken: accessToken,
            body: body,
            response: SessionFinishResponse.self
        )
    }

    func uploadSessionAudio(
        sessionID: String,
        audioURL: URL,
        userID: String,
        accessToken: String?
    ) async throws -> SessionAudioUploadResponse {
        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: baseURL.appendingPathComponent("/v1/sessions/\(sessionID)/audio"))
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        applyAuthHeaders(to: &request, userID: userID, accessToken: accessToken)

        let audioData = try Data(contentsOf: audioURL)
        let filename = audioURL.lastPathComponent.isEmpty ? "recording.m4a" : audioURL.lastPathComponent
        let mimeType = "audio/m4a"

        var body = Data()
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"\(filename)\"\r\n")
        body.append("Content-Type: \(mimeType)\r\n\r\n")
        body.append(audioData)
        body.append("\r\n--\(boundary)--\r\n")
        request.httpBody = body

        let (data, httpResponse) = try await URLSession.shared.data(for: request)
        guard let httpResponse = httpResponse as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }
        guard (200 ... 299).contains(httpResponse.statusCode) else {
            if let serverMessage = try? JSONDecoder().decode([String: String].self, from: data),
               let detail = serverMessage["detail"] {
                throw APIClientError.serverError(detail)
            }
            throw APIClientError.serverError("上传录音失败，状态码 \(httpResponse.statusCode)")
        }
        return try JSONDecoder().decode(SessionAudioUploadResponse.self, from: data)
    }

    func fetchReport(sessionID: String, userID: String, accessToken: String?) async throws -> ConflictReport {
        try await request(
            path: "/v1/reports/\(sessionID)",
            method: "GET",
            userID: userID,
            accessToken: accessToken,
            body: Optional<Data>.none,
            response: ConflictReport.self
        )
    }

    func fetchProgress(sessionID: String, userID: String, accessToken: String?) async throws -> SessionProgressResponse {
        try await request(
            path: "/v1/sessions/\(sessionID)/progress",
            method: "GET",
            userID: userID,
            accessToken: accessToken,
            body: Optional<Data>.none,
            response: SessionProgressResponse.self
        )
    }

    func listSessions(userID: String, accessToken: String?) async throws -> [SessionListItemResponse] {
        try await request(
            path: "/v1/sessions",
            method: "GET",
            userID: userID,
            accessToken: accessToken,
            body: Optional<Data>.none,
            response: [SessionListItemResponse].self
        )
    }

    private func request<T: Decodable, B: Encodable>(
        path: String,
        method: String,
        userID: String,
        accessToken: String?,
        body: B,
        response: T.Type
    ) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        applyAuthHeaders(to: &request, userID: userID, accessToken: accessToken)

        if method != "GET" {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, httpResponse) = try await URLSession.shared.data(for: request)
        guard let httpResponse = httpResponse as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }

        guard (200 ... 299).contains(httpResponse.statusCode) else {
            if let serverMessage = try? JSONDecoder().decode([String: String].self, from: data),
               let detail = serverMessage["detail"] {
                throw APIClientError.serverError(detail)
            }
            throw APIClientError.serverError("请求失败，状态码 \(httpResponse.statusCode)")
        }

        return try APIClient.decoder.decode(T.self, from: data)
    }

    private func applyAuthHeaders(to request: inout URLRequest, userID: String, accessToken: String?) {
        if let accessToken, !accessToken.isEmpty {
            request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        } else if !userID.isEmpty {
            request.setValue(userID, forHTTPHeaderField: "X-User-Id")
        }
    }

    private static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        let formatterWithFractional = ISO8601DateFormatter()
        formatterWithFractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let raw = try container.decode(String.self)
            if let d = formatterWithFractional.date(from: raw) ?? formatter.date(from: raw) {
                return d
            }
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Invalid ISO8601 date: \(raw)"
            )
        }
        return decoder
    }()
}

private extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}
