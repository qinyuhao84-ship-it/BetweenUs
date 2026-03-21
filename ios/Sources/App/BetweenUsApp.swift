import SwiftUI

@main
struct BetweenUsApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            Group {
                if appState.isLoggedIn {
                    RootTabView()
                } else {
                    LoginView()
                }
            }
                .environmentObject(appState)
                .task {
                    await appState.refreshRuntimeStatus()
                    if appState.isLoggedIn {
                        await appState.refreshProfile()
                    }
                }
        }
    }
}
