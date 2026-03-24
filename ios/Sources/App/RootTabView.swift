import SwiftUI

struct RootTabView: View {
    @State private var selectedTab: TabID = .record

    var body: some View {
        TabView(selection: $selectedTab) {
            NavigationStack {
                RecordView()
                    .navigationTitle("BetweenUs")
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
