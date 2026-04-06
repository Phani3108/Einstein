/**
 * ShareViewController — iOS Share Extension for Einstein.
 *
 * Accepts shared text and URLs from other apps, stores them in shared
 * App Group UserDefaults so the main Einstein app can pick them up
 * on next launch/foreground.
 *
 * ---- Setup Instructions ----
 *
 * 1. In Xcode, add a new "Share Extension" target to the project:
 *    File > New > Target > Share Extension
 *
 * 2. Create an App Group in Apple Developer portal:
 *    Identifier: group.com.einstein.shared
 *
 * 3. Enable the App Group capability on BOTH targets:
 *    - Main app target > Signing & Capabilities > + App Groups > group.com.einstein.shared
 *    - ShareExtension target > Signing & Capabilities > + App Groups > group.com.einstein.shared
 *
 * 4. Replace this file's content in the generated ShareExtension target,
 *    and update the Info.plist with the provided configuration.
 *
 * 5. The main app reads pending shares from UserDefaults on launch via
 *    ShareReceiver.processPendingIOSShares() in the React Native layer.
 */

import UIKit
import Social
import MobileCoreServices
import UniformTypeIdentifiers

class ShareViewController: SLComposeServiceViewController {

    // MARK: - Constants

    /// App Group identifier — must match the main app's App Group.
    private let appGroupID = "group.com.einstein.shared"

    /// UserDefaults key for buffered shares.
    private let pendingSharesKey = "pendingShares"

    // MARK: - Lifecycle

    override func isContentValid() -> Bool {
        // Accept any non-empty content
        return true
    }

    override func didSelectPost() {
        // Collect all shared items
        guard let extensionItems = extensionContext?.inputItems as? [NSExtensionItem] else {
            completeRequest()
            return
        }

        let group = DispatchGroup()
        var sharedTexts: [String] = []
        var sharedURLs: [String] = []

        for item in extensionItems {
            guard let attachments = item.attachments else { continue }

            for attachment in attachments {
                // Handle plain text
                if attachment.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
                    group.enter()
                    attachment.loadItem(forTypeIdentifier: UTType.plainText.identifier, options: nil) { data, error in
                        defer { group.leave() }
                        if let text = data as? String, !text.isEmpty {
                            sharedTexts.append(text)
                        }
                    }
                }

                // Handle URLs
                if attachment.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
                    group.enter()
                    attachment.loadItem(forTypeIdentifier: UTType.url.identifier, options: nil) { data, error in
                        defer { group.leave() }
                        if let url = data as? URL {
                            sharedURLs.append(url.absoluteString)
                        } else if let urlString = data as? String, !urlString.isEmpty {
                            sharedURLs.append(urlString)
                        }
                    }
                }
            }
        }

        // Also capture the compose text field content
        if let composedText = contentText, !composedText.isEmpty {
            sharedTexts.append(composedText)
        }

        group.notify(queue: .main) { [weak self] in
            self?.savePendingShare(texts: sharedTexts, urls: sharedURLs)
            self?.completeRequest()
        }
    }

    override func configurationItems() -> [Any]! {
        // No additional configuration needed
        return []
    }

    // MARK: - Storage

    private func savePendingShare(texts: [String], urls: [String]) {
        guard let userDefaults = UserDefaults(suiteName: appGroupID) else {
            NSLog("[Einstein ShareExtension] Failed to access App Group UserDefaults")
            return
        }

        // Build the share entry
        let entry: [String: Any] = [
            "texts": texts,
            "urls": urls,
            "timestamp": ISO8601DateFormatter().string(from: Date()),
            "id": UUID().uuidString,
        ]

        // Append to existing pending shares
        var pending = userDefaults.array(forKey: pendingSharesKey) as? [[String: Any]] ?? []
        pending.append(entry)

        // Cap at 50 entries to prevent unbounded growth
        if pending.count > 50 {
            pending = Array(pending.suffix(50))
        }

        userDefaults.set(pending, forKey: pendingSharesKey)
        userDefaults.synchronize()

        NSLog("[Einstein ShareExtension] Saved share: %d texts, %d urls", texts.count, urls.count)
    }

    // MARK: - Helpers

    private func completeRequest() {
        extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
    }
}
