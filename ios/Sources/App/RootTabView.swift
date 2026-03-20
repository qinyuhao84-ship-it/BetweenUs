import SwiftUI

struct RootTabView: View {
    var body: some View {
        TabView {
            NavigationStack {
                RecordView()
                    .navigationTitle("冲突复盘")
            }
            .tabItem {
                Label("复盘", systemImage: "waveform.circle")
            }

            NavigationStack {
                HistoryView()
                    .navigationTitle("历史记录")
            }
            .tabItem {
                Label("历史", systemImage: "clock.arrow.circlepath")
            }

            NavigationStack {
                SettingsView()
                    .navigationTitle("设置")
            }
            .tabItem {
                Label("设置", systemImage: "gearshape")
            }
        }
    }
}
