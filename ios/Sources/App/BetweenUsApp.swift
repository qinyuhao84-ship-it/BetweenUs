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
                    appState.iapStore.startObserving(appState: appState)
                    if appState.isLoggedIn {
                        await appState.refreshProfile()
                        await appState.refreshEntitlements()
                        await appState.refreshTopupPackages()
                        await appState.iapStore.syncUnfinishedTransactions(appState: appState)
                    }
                }
        }
    }
}
