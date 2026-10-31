// Default OCR backend for genius-video-qc (macOS only, Apple Vision, no model download).
//
//   swift ocr_vision.swift <image_dir> [languages]
//
// languages: comma list of Vision codes, default "zh-Hans,en-US".
// Prints one JSON line per image (sorted by file name), following the OCR backend contract in
// references/backends.md: {"file": name, "lines": [{"t", "c", "cx", "cy", "h"}]}, coordinates
// normalized 0–1 with cy measured from the TOP of the image.
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 2 else {
    FileHandle.standardError.write("usage: swift ocr_vision.swift <image_dir> [languages]\n".data(using: .utf8)!)
    exit(2)
}
let dir = URL(fileURLWithPath: args[1])
let languages = args.count >= 3 ? args[2].split(separator: ",").map(String.init) : ["zh-Hans", "en-US"]
let names = ((try? FileManager.default.contentsOfDirectory(atPath: dir.path)) ?? [])
    .filter { $0.lowercased().hasSuffix(".png") || $0.lowercased().hasSuffix(".jpg") }
    .sorted()

for name in names {
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = languages
    // Keep literal text: language correction would "fix" the typos we are trying to find.
    req.usesLanguageCorrection = false
    try? VNImageRequestHandler(url: dir.appendingPathComponent(name), options: [:]).perform([req])
    var lines: [[String: Any]] = []
    for obs in req.results ?? [] {
        guard let cand = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        lines.append(["t": cand.string, "c": Double(cand.confidence),
                      "cx": Double(b.midX), "cy": Double(1 - b.midY), "h": Double(b.height)])
    }
    let obj: [String: Any] = ["file": name, "lines": lines]
    if let data = try? JSONSerialization.data(withJSONObject: obj), let s = String(data: data, encoding: .utf8) {
        print(s)
    }
}
