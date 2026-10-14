import Foundation
import Vision
import AppKit

// usage: ocr <image> ...   -> writes <image>.txt next to each image
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("cannot load \(path)\n".data(using: .utf8)!)
        continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["en-US"]
    req.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try handler.perform([req]) } catch { continue }
    var lines: [String] = []
    for obs in req.results ?? [] {
        if let c = obs.topCandidates(1).first { lines.append(c.string) }
    }
    try? lines.joined(separator: "\n").write(toFile: path + ".txt", atomically: true, encoding: .utf8)
}
