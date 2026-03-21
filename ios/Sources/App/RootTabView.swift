import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var appState: AppState
    @State private var selectedTab: TabID = .record

    var body: some View {
        Group {
            if let sessionID = ProcessInfo.processInfo.environment["BETWEENUS_OPEN_REPORT_ID"],
               !sessionID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            {
                NavigationStack {
                    ReportDebugLoaderView(sessionID: sessionID)
                }
            } else {
                TabView(selection: $selectedTab) {
                    NavigationStack {
                        RecordView()
                            .navigationTitle("冲突复盘")
                    }
                    .tabItem {
                        Label("复盘", systemImage: "waveform.circle")
                    }
                    .tag(TabID.record)

                    NavigationStack {
                        HistoryView()
                            .navigationTitle("历史记录")
                    }
                    .tabItem {
                        Label("历史", systemImage: "clock.arrow.circlepath")
                    }
                    .tag(TabID.history)

                    NavigationStack {
                        SettingsView()
                            .navigationTitle("设置")
                    }
                    .tabItem {
                        Label("设置", systemImage: "gearshape")
                    }
                    .tag(TabID.settings)
                }
                .onAppear {
                    let raw = ProcessInfo.processInfo.environment["BETWEENUS_OPEN_TAB"]?.lowercased() ?? ""
                    switch raw {
                    case "history":
                        selectedTab = .history
                    case "settings":
                        selectedTab = .settings
                    default:
                        selectedTab = .record
                    }
                }
            }
        }
        .tint(BetweenUsTheme.brandBlue)
        .toolbarBackground(BetweenUsTheme.cardStrong, for: .tabBar)
        .toolbarBackground(.visible, for: .tabBar)
    }
}

private enum TabID: Hashable {
    case record
    case history
    case settings
}

private struct ReportDebugLoaderView: View {
    @EnvironmentObject private var appState: AppState
    let sessionID: String

    @State private var report: ConflictReport?
    @State private var errorText: String?

    var body: some View {
        Group {
            if let report {
                ReportDetailView(report: report)
            } else if let errorText {
                ZStack {
                    BetweenUsGradientBackground()
                    Text(errorText)
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .padding(20)
                }
            } else {
                ZStack {
                    BetweenUsGradientBackground()
                    ProgressView("加载报告中")
                }
            }
        }
        .navigationTitle("复盘报告")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await load()
        }
    }

    private func load() async {
        do {
            guard appState.isLoggedIn else {
                errorText = "未登录，无法加载报告"
                return
            }
            guard let baseURL = URL(string: appState.serverBaseURL) else {
                errorText = "服务地址无效"
                return
            }
            let client = APIClient(baseURL: baseURL)
            let fetched = try await client.fetchReport(
                sessionID: sessionID,
                userID: appState.currentUserId,
                accessToken: appState.accessToken
            )
            report = fetched
        } catch {
            errorText = error.localizedDescription
        }
    }
}
