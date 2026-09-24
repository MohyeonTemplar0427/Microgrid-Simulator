// Native shell for the loopback-only study application. All study controls,
// simulation requests and results are served by the shared local web code.
import AppKit
import WebKit

guard CommandLine.arguments.count == 2,
      let appURL = URL(string: CommandLine.arguments[1]),
      appURL.scheme == "http",
      appURL.host == "127.0.0.1" else {
    fputs("Expected a local Microgrid Simulator URL.\n", stderr)
    exit(2)
}

final class DesktopWindow: NSObject, NSApplicationDelegate, NSWindowDelegate,
                           WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    private let appURL: URL
    private var window: NSWindow!
    private var webView: WKWebView!

    init(url: URL) { self.appURL = url }

    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1440, height: 920),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Microgrid Simulator"
        window.minSize = NSSize(width: 820, height: 600)
        window.center()
        window.delegate = self

        webView = WKWebView(frame: window.contentView!.bounds)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        webView.load(URLRequest(url: appURL))
    }

    func windowWillClose(_ notification: Notification) { NSApp.terminate(nil) }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        print("Desktop study page loaded: \(webView.title ?? "Microgrid Simulator")")
        fflush(stdout)
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if url.scheme == appURL.scheme && url.host == appURL.host && url.port == appURL.port {
            decisionHandler(action.shouldPerformDownload ? .download : .allow)
        } else {
            if action.navigationType == .linkActivated { NSWorkspace.shared.open(url) }
            decisionHandler(.cancel)
        }
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction,
                 didBecome download: WKDownload) {
        download.delegate = self
    }

    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse,
                 didBecome download: WKDownload) {
        download.delegate = self
    }

    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse,
                  suggestedFilename: String,
                  completionHandler: @escaping (URL?) -> Void) {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = suggestedFilename
        panel.canCreateDirectories = true
        completionHandler(panel.runModal() == .OK ? panel.url : nil)
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction,
                 windowFeatures: WKWindowFeatures) -> WKWebView? {
        if navigationAction.navigationType == .linkActivated,
           let url = navigationAction.request.url,
           url.scheme == "https" || url.scheme == "http" {
            NSWorkspace.shared.open(url)
        }
        return nil
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let desktop = DesktopWindow(url: appURL)
app.delegate = desktop
app.run()
