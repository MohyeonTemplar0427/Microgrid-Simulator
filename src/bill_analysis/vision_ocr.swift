import AppKit
import Foundation
import PDFKit
import Vision

guard CommandLine.arguments.count >= 3,
      let document = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    fputs("PDF open failed\n", stderr)
    exit(2)
}

var result: [String: String] = [:]
for argument in CommandLine.arguments.dropFirst(2) {
    guard let number = Int(argument), number >= 1, number <= document.pageCount,
          let page = document.page(at: number - 1) else { fputs("Page unavailable\n", stderr); exit(2) }
    let image = page.thumbnail(of: NSSize(width: 2200, height: 2800), for: .mediaBox)
    var rect = CGRect(origin: .zero, size: image.size)
    guard let bitmap = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else { fputs("Bitmap unavailable\n", stderr); exit(2) }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    do {
        try VNImageRequestHandler(cgImage: bitmap, options: [:]).perform([request])
    } catch { fputs("Text recognition failed: \(error.localizedDescription)\n", stderr); exit(2) }
    let observations = (request.results ?? []).sorted {
        if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.012 {
            return $0.boundingBox.midY > $1.boundingBox.midY
        }
        return $0.boundingBox.minX < $1.boundingBox.minX
    }
    result[argument] = observations.compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
}
guard let data = try? JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]),
      let json = String(data: data, encoding: .utf8) else { fputs("JSON encoding failed\n", stderr); exit(2) }
print(json)
