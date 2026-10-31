import Foundation
import Vision
import CoreGraphics
import ImageIO

guard CommandLine.arguments.count > 1 else {
    fputs("Usage: apple_ocr <image_path>\n", stderr)
    exit(1)
}

let path = CommandLine.arguments[1]
let url = URL(fileURLWithPath: path) as CFURL
guard let source = CGImageSourceCreateWithURL(url, nil),
      let cgImage = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    fputs("Error: Could not load image at \(CommandLine.arguments[1])\n", stderr)
    exit(1)
}

let semaphore = DispatchSemaphore(value: 0)
let request = VNRecognizeTextRequest { req, err in
    defer { semaphore.signal() }
    guard let obs = req.results as? [VNRecognizedTextObservation] else { return }
    for o in obs {
        if let s = o.topCandidates(1).first?.string {
            print(s)
        }
    }
}
request.recognitionLevel = .accurate

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
    semaphore.wait()
} catch {
    fputs("OCR Error: \(error)\n", stderr)
    exit(1)
}
