// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ToeflNativeApp",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .executable(name: "ToeflNativeApp", targets: ["ToeflNativeApp"]),
    ],
    targets: [
        .executableTarget(
            name: "ToeflNativeApp",
            path: "Sources/ToeflNativeApp"
        )
    ]
)
