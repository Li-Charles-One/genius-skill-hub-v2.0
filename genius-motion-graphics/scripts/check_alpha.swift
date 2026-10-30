// macOS：检查视频是否带透明通道；可选解出一帧叠到纯色底上存 PNG，模拟 Mac 播放器 / 剪辑软件看到的效果。
// 用法：swift check_alpha.swift <视频> [输出.png] [秒数，默认 3] [底色 hex，默认 2a2f38]
import AVFoundation
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 2 else {
  print("usage: swift check_alpha.swift <video> [out.png] [seconds=3] [bg=2a2f38]")
  exit(2)
}
let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let tracks = asset.tracks(withMediaType: .video)
guard let track = tracks.first, let fd = track.formatDescriptions.first else {
  print("no video track"); exit(1)
}
let desc = fd as! CMFormatDescription
let ext = CMFormatDescriptionGetExtensions(desc) as? [String: Any] ?? [:]
let sub = CMFormatDescriptionGetMediaSubType(desc)
let fourcc = String((0..<4).map { Character(UnicodeScalar(UInt8((sub >> (8 * (3 - $0))) & 0xff))) })
let hasAlpha = (ext["ContainsAlphaChannel"] as? Bool) ?? ((ext["ContainsAlphaChannel"] as? NSNumber)?.boolValue ?? false)
print("codec: \(fourcc)  ContainsAlphaChannel: \(hasAlpha ? 1 : 0)")

if args.count >= 3 {
  let seconds = args.count >= 4 ? Double(args[3]) ?? 3 : 3
  let hex = args.count >= 5 ? args[4] : "2a2f38"
  let v = UInt32(hex, radix: 16) ?? 0x2a2f38
  let gen = AVAssetImageGenerator(asset: asset)
  gen.requestedTimeToleranceBefore = .zero
  gen.requestedTimeToleranceAfter = .zero
  guard let img = try? gen.copyCGImage(at: CMTime(seconds: seconds, preferredTimescale: 600), actualTime: nil) else {
    print("decode failed: 系统解码器打不开这一帧（H.265 标签是 hev1 时 QuickTime / 预览也打不开）")
    exit(1)
  }
  let ctx = CGContext(data: nil, width: img.width, height: img.height, bitsPerComponent: 8, bytesPerRow: 0,
                      space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
  ctx.setFillColor(red: CGFloat((v >> 16) & 0xff) / 255, green: CGFloat((v >> 8) & 0xff) / 255, blue: CGFloat(v & 0xff) / 255, alpha: 1)
  ctx.fill(CGRect(x: 0, y: 0, width: img.width, height: img.height))
  ctx.draw(img, in: CGRect(x: 0, y: 0, width: img.width, height: img.height))
  let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[2]) as CFURL, UTType.png.identifier as CFString, 1, nil)!
  CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
  CGImageDestinationFinalize(dest)
  print("frame @\(seconds)s over #\(hex) -> \(args[2])")
}
exit(hasAlpha ? 0 : 1)
