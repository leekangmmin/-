import AppKit
import Foundation
import SwiftUI

private enum AppConfig {
	static let host = "127.0.0.1"
	static let port = 8000
	static let baseURL = "http://\(host):\(port)"
	static let healthURL = "\(baseURL)/api/health"
	static let evaluateURL = "\(baseURL)/api/evaluate"
	static let historyURL = "\(baseURL)/api/history?limit=30"
	static let dashboardURL = "\(baseURL)/api/dashboard?limit=200"

	static func reportURL(for submissionID: Int) -> String {
		"\(baseURL)/api/report/\(submissionID).pdf"
	}
}

private enum PromptKind: String, CaseIterable, Identifiable {
	case auto
	case email
	case academicDiscussion

	var id: String { rawValue }

	var requestValue: String? {
		switch self {
		case .auto:
			return nil
		case .email:
			return "email"
		case .academicDiscussion:
			return "academic_discussion"
		}
	}

	var title: String {
		switch self {
		case .auto:
			return "AUTO"
		case .email:
			return "EMAIL"
		case .academicDiscussion:
			return "DISCUSSION"
		}
	}
}

private enum ResultTab: String, CaseIterable, Identifiable {
	case overview
	case progress
	case history

	var id: String { rawValue }

	var title: String {
		switch self {
		case .overview:
			return "RESULT"
		case .progress:
			return "DASHBOARD"
		case .history:
			return "HISTORY"
		}
	}
}

private struct EvaluatePayload: Encodable {
	let prompt_type: String?
	let prompt_text: String
	let essay_text: String
	let target_score_0_5: Double
	let exam_mode: Bool
}

private struct EvaluateResponse: Decodable {
	let submission_id: Int
	let created_at: String
	let result: EvaluateResult
}

private struct EvaluateResult: Decodable {
	let estimated_score_0_5: Double
	let estimated_score_30: Int
	let score_band_1_6: Double
	let strengths: [String]
	let weaknesses: [String]
	let action_plan: [String]
	let weekly_plan: [String]
	let personal_weakness_ranking: [String]
	let bilingual_feedback: BilingualFeedback
	let grammar_stats: GrammarStats
}

private struct BilingualFeedback: Decodable {
	let summary_ko: String
	let summary_en: String
}

private struct GrammarStats: Decodable {
	let tense: Int
	let article: Int
	let preposition: Int
	let run_on: Int
	let subject_verb: Int
	let punctuation: Int
	let total: Int
}

private struct HistoryResponse: Decodable {
	let items: [HistoryItem]
}

private struct HistoryItem: Decodable, Identifiable {
	let id: Int
	let created_at: String
	let prompt_type: String
	let estimated_score_0_5: Double
	let score_band_1_6: Double
	let estimated_score_30: Int
}

private struct DashboardResponse: Decodable {
	let attempt_count: Int
	let avg_score_0_5: Double
	let avg_prompt_fit: Double
	let score_trend: [ScoreTrendPoint]
	let top_grammar_issues: [GrammarIssueItem]
	let recommended_focus: [String]
}

private struct ScoreTrendPoint: Decodable {
	let submission_id: Int
	let score_0_5: Double
}

private struct GrammarIssueItem: Decodable, Identifiable {
	let type: String
	let count: Int

	var id: String { type }
}

private enum ServerError: Error {
	case missingPython(String)
	case failedToBoot
}

private enum InputTarget {
	case prompt
	case essay
}

private enum UITheme {
	static let bgTop = Color(red: 0.96, green: 0.97, blue: 0.99)
	static let bgBottom = Color(red: 0.90, green: 0.93, blue: 0.96)
	static let panel = Color(red: 0.99, green: 0.99, blue: 1.00)
	static let panelSoft = Color(red: 0.93, green: 0.95, blue: 0.98)
	static let accent = Color(red: 0.00, green: 0.36, blue: 0.73)
	static let accentSoft = Color(red: 0.65, green: 0.74, blue: 0.86)
	static let textMain = Color(red: 0.08, green: 0.10, blue: 0.13)
	static let textSub = Color(red: 0.30, green: 0.36, blue: 0.42)
}

@MainActor
private final class ServerController {
	static let shared = ServerController()

	private var process: Process?
	private var startedHere = false

	private init() {}

	func startIfNeeded() throws {
		if healthOK(timeout: 1.0) {
			return
		}

		let root = projectRoot()
		let python = root.appendingPathComponent(".venv/bin/python")
		guard FileManager.default.isExecutableFile(atPath: python.path) else {
			throw ServerError.missingPython(python.path)
		}

		let dataDir = root.appendingPathComponent("data", isDirectory: true)
		try? FileManager.default.createDirectory(at: dataDir, withIntermediateDirectories: true)

		let logURL = dataDir.appendingPathComponent("app.log")
		FileManager.default.createFile(atPath: logURL.path, contents: nil)
		let logHandle = try FileHandle(forWritingTo: logURL)
		try logHandle.seekToEnd()

		let proc = Process()
		proc.currentDirectoryURL = root
		proc.executableURL = python
		proc.arguments = [
			"-m", "uvicorn", "app.main:app", "--host", AppConfig.host, "--port", "\(AppConfig.port)",
		]
		proc.standardOutput = logHandle
		proc.standardError = logHandle

		try proc.run()
		process = proc
		startedHere = true

		let pidURL = dataDir.appendingPathComponent("app.pid")
		try? String(proc.processIdentifier).write(to: pidURL, atomically: true, encoding: .utf8)

		for _ in 0..<60 {
			if healthOK(timeout: 0.6) {
				return
			}
			usleep(200_000)
		}

		stopIfStarted()
		throw ServerError.failedToBoot
	}

	func stopIfStarted() {
		guard startedHere, let proc = process else {
			return
		}

		if proc.isRunning {
			proc.terminate()
			usleep(250_000)
			if proc.isRunning {
				proc.interrupt()
			}
		}

		let pidURL = projectRoot().appendingPathComponent("data/app.pid")
		try? FileManager.default.removeItem(at: pidURL)
		startedHere = false
		process = nil
	}

	private func projectRoot() -> URL {
		let fm = FileManager.default
		if let envRoot = ProcessInfo.processInfo.environment["TOEFL_PROJECT_ROOT"], !envRoot.isEmpty {
			return URL(fileURLWithPath: envRoot, isDirectory: true)
		}
		return URL(fileURLWithPath: fm.currentDirectoryPath, isDirectory: true)
	}

	private func healthOK(timeout: TimeInterval) -> Bool {
		let process = Process()
		process.executableURL = URL(fileURLWithPath: "/usr/bin/curl")
		process.arguments = ["-s", "-m", String(format: "%.2f", timeout), AppConfig.healthURL]

		let pipe = Pipe()
		process.standardOutput = pipe
		process.standardError = Pipe()

		do {
			try process.run()
			process.waitUntilExit()
			if process.terminationStatus != 0 {
				return false
			}
			let data = pipe.fileHandleForReading.readDataToEndOfFile()
			let text = String(data: data, encoding: .utf8) ?? ""
			return text.contains("\"status\":\"ok\"") || text.contains("\"status\": \"ok\"")
		} catch {
			return false
		}
	}
}

@MainActor
private final class AppViewModel: ObservableObject {
	@Published var essayText: String = ""
	@Published var targetScoreBand: Double = 5.0
	@Published var examMode: Bool = false

	@Published var selectedTab: ResultTab = .overview
	@Published var isLoading = false
	@Published var isRefreshing = false
	@Published var isDownloadingReport = false
	@Published var errorMessage: String?

	@Published var result: EvaluateResult?
	@Published var lastSubmissionID: Int?
	@Published var historyItems: [HistoryItem] = []
	@Published var dashboard: DashboardResponse?

	private var keyMonitor: Any?

	func bootstrap() {
		Task {
			await refreshSupportData()
		}
	}

	func installKeyboardFallback() {
		guard keyMonitor == nil else { return }

		keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
			guard let self else { return event }
			if !NSApp.isActive {
				return event
			}

			let mods = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
			if mods.contains(.command) || mods.contains(.control) || mods.contains(.option) {
				return event
			}

			if event.keyCode == 51 { // delete
				if !self.essayText.isEmpty {
					self.essayText.removeLast()
				}
				return nil
			}

			if event.keyCode == 36 || event.keyCode == 76 { // return
				self.essayText.append("\n")
				return nil
			}

			guard let chars = event.characters, !chars.isEmpty else {
				return event
			}
			if chars.unicodeScalars.allSatisfy({ CharacterSet.controlCharacters.contains($0) }) {
				return event
			}

			self.essayText.append(chars)
			return nil
		}
	}

	func removeKeyboardFallback() {
		if let monitor = keyMonitor {
			NSEvent.removeMonitor(monitor)
			keyMonitor = nil
		}
	}

	func evaluate() {
		let wordCount = essayText.split(whereSeparator: { $0.isWhitespace || $0.isNewline }).count
		guard wordCount >= 80 else {
			errorMessage = "에세이는 최소 80단어 이상 입력해야 합니다."
			return
		}

		isLoading = true
		errorMessage = nil

		Task {
			defer { isLoading = false }
			do {
				let targetScore0to5 = max(0.0, min(5.0, targetScoreBand - 1.0))
				let payload = EvaluatePayload(
					prompt_type: nil,
					prompt_text: "",
					essay_text: essayText,
					target_score_0_5: targetScore0to5,
					exam_mode: examMode
				)

				let response: EvaluateResponse = try await postJSON(
					urlString: AppConfig.evaluateURL,
					payload: payload,
					timeout: 60
				)

				result = response.result
				lastSubmissionID = response.submission_id
				selectedTab = .overview
				await refreshSupportData()
			} catch {
				errorMessage = "채점 요청 실패: \(error.localizedDescription)"
			}
		}
	}

	func refreshSupportData() async {
		isRefreshing = true
		defer { isRefreshing = false }

		async let historyTask: [HistoryItem] = fetchHistory()
		async let dashboardTask: DashboardResponse? = fetchDashboard()

		historyItems = (try? await historyTask) ?? historyItems
		dashboard = (try? await dashboardTask) ?? dashboard
	}

	func downloadLatestReport() {
		guard let submissionID = lastSubmissionID else {
			errorMessage = "최근 채점 결과가 없어 PDF를 생성할 수 없습니다."
			return
		}
		downloadReport(for: submissionID)
	}

	func downloadReport(for submissionID: Int) {
		isDownloadingReport = true

		Task {
			defer { isDownloadingReport = false }
			do {
				let data = try await getData(urlString: AppConfig.reportURL(for: submissionID), timeout: 60)
				let downloadsDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Downloads")
				let filename = "TOEFL_Report_\(submissionID)_\(timestampForFile()).pdf"
				let fileURL = downloadsDir.appendingPathComponent(filename)
				try data.write(to: fileURL, options: .atomic)
				NSWorkspace.shared.open(fileURL)
			} catch {
				errorMessage = "PDF 다운로드 실패: \(error.localizedDescription)"
			}
		}
	}

	func pasteFromClipboard() {
		if let pasted = NSPasteboard.general.string(forType: .string), !pasted.isEmpty {
			if essayText.isEmpty {
				essayText = pasted
			} else {
				essayText += "\n" + pasted
			}
		}
	}

	private func fetchHistory() async throws -> [HistoryItem] {
		let response: HistoryResponse = try await getJSON(urlString: AppConfig.historyURL, timeout: 20)
		return response.items
	}

	private func fetchDashboard() async throws -> DashboardResponse {
		try await getJSON(urlString: AppConfig.dashboardURL, timeout: 20)
	}

	private func timestampForFile() -> String {
		let formatter = DateFormatter()
		formatter.dateFormat = "yyyyMMdd_HHmmss"
		return formatter.string(from: Date())
	}

	private func getJSON<T: Decodable>(urlString: String, timeout: TimeInterval) async throws -> T {
		let data = try await getData(urlString: urlString, timeout: timeout)
		return try JSONDecoder().decode(T.self, from: data)
	}

	private func postJSON<P: Encodable, T: Decodable>(urlString: String, payload: P, timeout: TimeInterval) async throws -> T {
		guard let url = URL(string: urlString) else {
			throw URLError(.badURL)
		}

		var request = URLRequest(url: url)
		request.httpMethod = "POST"
		request.timeoutInterval = timeout
		request.setValue("application/json", forHTTPHeaderField: "Content-Type")
		request.httpBody = try JSONEncoder().encode(payload)

		let (data, response) = try await URLSession.shared.data(for: request)
		guard let http = response as? HTTPURLResponse else {
			throw URLError(.badServerResponse)
		}
		guard (200..<300).contains(http.statusCode) else {
			let body = String(data: data, encoding: .utf8) ?? ""
			throw NSError(domain: "HTTPError", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: body])
		}

		return try JSONDecoder().decode(T.self, from: data)
	}

	private func getData(urlString: String, timeout: TimeInterval) async throws -> Data {
		guard let url = URL(string: urlString) else {
			throw URLError(.badURL)
		}

		var request = URLRequest(url: url)
		request.timeoutInterval = timeout

		let (data, response) = try await URLSession.shared.data(for: request)
		guard let http = response as? HTTPURLResponse else {
			throw URLError(.badServerResponse)
		}
		guard (200..<300).contains(http.statusCode) else {
			let body = String(data: data, encoding: .utf8) ?? ""
			throw NSError(domain: "HTTPError", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: body])
		}
		return data
	}
}

private struct AppTextArea: NSViewRepresentable {
	@Binding var text: String
	@Binding var shouldFocus: Bool

	let placeholder: String

	final class Coordinator: NSObject, NSTextViewDelegate {
		var parent: AppTextArea

		init(parent: AppTextArea) {
			self.parent = parent
		}

		func textDidChange(_ notification: Notification) {
			guard let textView = notification.object as? NSTextView else { return }
			parent.text = textView.string
		}
	}

	func makeCoordinator() -> Coordinator {
		Coordinator(parent: self)
	}

	func makeNSView(context: Context) -> NSScrollView {
		let scrollView = NSScrollView()
		scrollView.hasVerticalScroller = true
		scrollView.hasHorizontalScroller = false
		scrollView.drawsBackground = true
		scrollView.backgroundColor = NSColor(calibratedRed: 0.98, green: 0.99, blue: 1.0, alpha: 1.0)
		scrollView.borderType = .lineBorder

		let textView = NSTextView()
		textView.isEditable = true
		textView.isSelectable = true
		textView.isFieldEditor = false
		textView.isRichText = false
		textView.importsGraphics = false
		textView.usesFindBar = true
		textView.allowsUndo = true
		textView.isAutomaticQuoteSubstitutionEnabled = false
		textView.isAutomaticTextReplacementEnabled = false
		textView.isAutomaticDashSubstitutionEnabled = false
		textView.font = NSFont.monospacedSystemFont(ofSize: 13, weight: .regular)
		textView.textColor = NSColor(calibratedRed: 0.08, green: 0.10, blue: 0.13, alpha: 1.0)
		textView.insertionPointColor = NSColor(calibratedRed: 0.00, green: 0.36, blue: 0.73, alpha: 1.0)
		textView.drawsBackground = true
		textView.backgroundColor = NSColor(calibratedRed: 1.0, green: 1.0, blue: 1.0, alpha: 1.0)
		textView.typingAttributes = [
			.foregroundColor: NSColor(calibratedRed: 0.08, green: 0.10, blue: 0.13, alpha: 1.0),
			.font: NSFont.monospacedSystemFont(ofSize: 13, weight: .regular),
		]
		textView.isVerticallyResizable = true
		textView.isHorizontallyResizable = false
		textView.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
		textView.minSize = NSSize(width: 0, height: 0)
		textView.string = text.isEmpty ? "" : text
		textView.delegate = context.coordinator
		textView.textContainerInset = NSSize(width: 8, height: 8)
		textView.textContainer?.widthTracksTextView = true
		textView.textContainer?.containerSize = NSSize(width: 0, height: CGFloat.greatestFiniteMagnitude)

		if text.isEmpty {
			textView.string = ""
		}

		scrollView.documentView = textView
		return scrollView
	}

	func updateNSView(_ nsView: NSScrollView, context: Context) {
		guard let textView = nsView.documentView as? NSTextView else { return }

		if textView.string != text {
			textView.string = text
		}
		if shouldFocus, let window = nsView.window {
			if window.firstResponder !== textView {
				window.makeFirstResponder(textView)
			}
			DispatchQueue.main.async {
				shouldFocus = false
			}
		}
	}
}

private struct PanelCard<Content: View>: View {
	let title: String
	@ViewBuilder var content: Content

	var body: some View {
		VStack(alignment: .leading, spacing: 8) {
			Text(title)
				.font(.system(size: 12, weight: .bold, design: .monospaced))
				.foregroundStyle(UITheme.accent)
			content
		}
		.padding(12)
		.background(
			RoundedRectangle(cornerRadius: 10)
				.fill(UITheme.panel)
				.overlay(RoundedRectangle(cornerRadius: 10).stroke(UITheme.accentSoft, lineWidth: 1))
		)
	}
}

private struct ContentView: View {
	@StateObject private var vm = AppViewModel()

	@FocusState private var essayEditorFocused: Bool

	var body: some View {
		ZStack {
			LinearGradient(
				colors: [UITheme.bgTop, UITheme.bgBottom],
				startPoint: .topLeading,
				endPoint: .bottomTrailing
			)
			.ignoresSafeArea()

			NavigationSplitView {
				leftPanel
					.navigationSplitViewColumnWidth(min: 430, ideal: 480)
			} detail: {
				rightPanel
			}
		}
		.task {
			vm.bootstrap()
			vm.installKeyboardFallback()
			DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
				NSApp.activate(ignoringOtherApps: true)
				essayEditorFocused = true
			}
		}
		.onDisappear {
			vm.removeKeyboardFallback()
		}
	}

	private var leftPanel: some View {
		VStack(alignment: .leading, spacing: 12) {
			Text("TOEFL CONTROL PANEL")
				.font(.system(size: 24, weight: .black, design: .monospaced))
				.foregroundStyle(UITheme.textMain)

			Text("INPUT BUS")
				.font(.system(size: 11, weight: .bold, design: .monospaced))
				.foregroundStyle(UITheme.textSub)

			PanelCard(title: "INPUT.BUFFER") {
				TextEditor(text: $vm.essayText)
					.font(.system(size: 14, weight: .regular, design: .monospaced))
					.foregroundStyle(UITheme.textMain)
					.scrollContentBackground(.hidden)
					.padding(8)
					.background(
						RoundedRectangle(cornerRadius: 8)
							.fill(Color.white)
					)
					.overlay(
						RoundedRectangle(cornerRadius: 8)
							.stroke(UITheme.accentSoft, lineWidth: 1)
					)
					.frame(minHeight: 430)
					.focused($essayEditorFocused)

				Text("TOKENS: \(vm.essayText.split(whereSeparator: { $0.isWhitespace || $0.isNewline }).count)")
					.font(.system(size: 11, design: .monospaced))
					.foregroundStyle(UITheme.textSub)
				Text("TASK TYPE는 입력 문장 형식에 따라 자동 감지됩니다.")
					.font(.system(size: 11, design: .monospaced))
					.foregroundStyle(UITheme.textSub)

				HStack(spacing: 8) {
					Button("붙여넣기") {
						vm.pasteFromClipboard()
						essayEditorFocused = true
					}
					.buttonStyle(.bordered)
					.tint(UITheme.accent)

					Button("입력창 비우기") {
						vm.essayText = ""
						essayEditorFocused = true
					}
					.buttonStyle(.bordered)
					.tint(UITheme.accent)
				}
			}

			PanelCard(title: "TARGET.SET") {
				HStack {
					Text("GOAL \(vm.targetScoreBand, specifier: "%.1f")/6.0")
						.font(.system(size: 12, weight: .semibold, design: .monospaced))
						.foregroundStyle(UITheme.textMain)
					Slider(value: $vm.targetScoreBand, in: 1...6, step: 0.5)
						.tint(UITheme.accent)
				}

				Toggle("EXAM MODE", isOn: $vm.examMode)
					.toggleStyle(.switch)
					.tint(UITheme.accent)
					.foregroundStyle(UITheme.textMain)
					.font(.system(size: 12, weight: .bold, design: .monospaced))
			}

			HStack(spacing: 10) {
				Button {
					vm.evaluate()
				} label: {
					if vm.isLoading {
						ProgressView()
							.frame(maxWidth: .infinity)
					} else {
						Text("RUN ANALYSIS")
							.font(.system(size: 12, weight: .black, design: .monospaced))
							.frame(maxWidth: .infinity)
					}
				}
				.buttonStyle(.borderedProminent)
				.tint(UITheme.accent)
				.disabled(vm.isLoading)

				Button {
					Task { await vm.refreshSupportData() }
				} label: {
					if vm.isRefreshing {
						ProgressView()
					} else {
						Image(systemName: "arrow.clockwise")
					}
				}
				.buttonStyle(.bordered)
				.tint(UITheme.accent)
			}

			HStack {
				Button {
					vm.downloadLatestReport()
				} label: {
					if vm.isDownloadingReport {
						ProgressView().controlSize(.small)
					} else {
						Label("EXPORT LATEST PDF", systemImage: "square.and.arrow.down")
							.font(.system(size: 11, weight: .bold, design: .monospaced))
					}
				}
				.buttonStyle(.bordered)
				.tint(UITheme.accent)
				.disabled(vm.lastSubmissionID == nil || vm.isDownloadingReport)

				Spacer()
				if let lastID = vm.lastSubmissionID {
					Text("ID #\(lastID)")
						.font(.system(size: 11, weight: .bold, design: .monospaced))
						.foregroundStyle(UITheme.textSub)
				}
			}

			if let error = vm.errorMessage {
				Text(error)
					.font(.system(size: 12, weight: .medium, design: .monospaced))
					.foregroundStyle(Color(red: 0.68, green: 0.08, blue: 0.08))
					.padding(10)
					.frame(maxWidth: .infinity, alignment: .leading)
					.background(
						RoundedRectangle(cornerRadius: 8)
							.fill(Color(red: 1.0, green: 0.92, blue: 0.92))
					)
			}

			Spacer(minLength: 0)
		}
		.padding(14)
	}

	private var rightPanel: some View {
		VStack(alignment: .leading, spacing: 10) {
			Picker("탭", selection: $vm.selectedTab) {
				ForEach(ResultTab.allCases) { tab in
					Text(tab.title).tag(tab)
				}
			}
			.pickerStyle(.segmented)
			.padding(.horizontal, 16)
			.padding(.top, 12)

			Group {
				switch vm.selectedTab {
				case .overview:
					overviewTab
				case .progress:
					progressTab
				case .history:
					historyTab
				}
			}
		}
		.background(UITheme.panelSoft.opacity(0.82))
	}

	private var overviewTab: some View {
		Group {
			if let result = vm.result {
				ScrollView {
					VStack(alignment: .leading, spacing: 12) {
						Text("RESULT BLOCK")
							.font(.system(size: 21, weight: .black, design: .monospaced))
							.foregroundStyle(UITheme.textMain)

						scoreCard(title: "TOEFL SCORE (MAX 6.0)", value: String(format: "%.1f", result.score_band_1_6))

						textPanel(title: "SUMMARY.KO", body: result.bilingual_feedback.summary_ko)
						textPanel(title: "SUMMARY.EN", body: result.bilingual_feedback.summary_en)
						listPanel(title: "STRENGTHS", items: result.strengths)
						listPanel(title: "WEAKNESSES", items: result.weaknesses)
						listPanel(title: "ACTION.PLAN", items: result.action_plan)
						listPanel(title: "WEEKLY.PLAN", items: result.weekly_plan)

						PanelCard(title: "GRAMMAR.STAT") {
							Text("TOTAL: \(result.grammar_stats.total)")
								.font(.system(size: 13, weight: .bold, design: .monospaced))
								.foregroundStyle(UITheme.textMain)
							Text("TENSE \(result.grammar_stats.tense) | ARTICLE \(result.grammar_stats.article) | PREP \(result.grammar_stats.preposition)")
								.foregroundStyle(UITheme.textSub)
							Text("RUNON \(result.grammar_stats.run_on) | S-V \(result.grammar_stats.subject_verb) | PUNCT \(result.grammar_stats.punctuation)")
								.foregroundStyle(UITheme.textSub)
						}
					}
					.padding(16)
				}
			} else {
				placeholder("RUN ANALYSIS를 눌러 결과를 생성하세요.")
			}
		}
	}

	private var progressTab: some View {
		Group {
			if let dashboard = vm.dashboard {
				ScrollView {
					VStack(alignment: .leading, spacing: 12) {
						Text("DASHBOARD BLOCK")
							.font(.system(size: 21, weight: .black, design: .monospaced))
							.foregroundStyle(UITheme.textMain)

						HStack(spacing: 10) {
							scoreCard(title: "ATTEMPTS", value: "\(dashboard.attempt_count)")
							scoreCard(title: "AVG.1_6", value: String(format: "%.2f", dashboard.avg_score_0_5 + 1.0))
							scoreCard(title: "AVG.PROMPT", value: String(format: "%.2f", dashboard.avg_prompt_fit))
						}

						PanelCard(title: "SCORE.TREND") {
							TrendLineView(points: dashboard.score_trend.map { $0.score_0_5 + 1.0 })
								.frame(height: 156)
						}

						PanelCard(title: "GRAMMAR.BAR") {
							GrammarBarView(items: dashboard.top_grammar_issues)
								.frame(height: 170)
						}

						listPanel(title: "RECOMMENDED.FOCUS", items: dashboard.recommended_focus)
					}
					.padding(16)
				}
			} else {
				placeholder("대시보드 데이터를 불러오는 중입니다.")
			}
		}
	}

	private var historyTab: some View {
		Group {
			if vm.historyItems.isEmpty {
				placeholder("히스토리 데이터가 없습니다.")
			} else {
				List(vm.historyItems) { item in
					VStack(alignment: .leading, spacing: 8) {
						HStack {
							Text("#\(item.id)")
								.font(.system(size: 13, weight: .bold, design: .monospaced))
							Text(item.prompt_type.uppercased())
								.font(.system(size: 11, weight: .semibold, design: .monospaced))
								.foregroundStyle(UITheme.textSub)
							Spacer()
							Text(formatDate(item.created_at))
								.font(.system(size: 11, design: .monospaced))
								.foregroundStyle(UITheme.textSub)
						}

						HStack(spacing: 10) {
							Text("1-6: \(String(format: "%.1f", item.score_band_1_6))")
						}
						.font(.system(size: 12, weight: .semibold, design: .monospaced))

						HStack {
							Button("PDF") {
								vm.downloadReport(for: item.id)
							}
							.buttonStyle(.bordered)
							.tint(UITheme.accent)

							Button("SET AS LATEST") {
								vm.lastSubmissionID = item.id
							}
							.buttonStyle(.plain)
							.foregroundStyle(UITheme.textSub)
						}
					}
					.padding(.vertical, 4)
					.listRowBackground(UITheme.panel)
				}
				.scrollContentBackground(.hidden)
				.background(UITheme.panelSoft)
			}
		}
	}

	private func scoreCard(title: String, value: String) -> some View {
		VStack(alignment: .leading, spacing: 5) {
			Text(title)
				.font(.system(size: 11, weight: .bold, design: .monospaced))
				.foregroundStyle(UITheme.textSub)
			Text(value)
				.font(.system(size: 20, weight: .black, design: .monospaced))
				.foregroundStyle(UITheme.textMain)
		}
		.padding(10)
		.frame(maxWidth: .infinity, alignment: .leading)
		.background(
			RoundedRectangle(cornerRadius: 10)
				.fill(UITheme.panel)
				.overlay(RoundedRectangle(cornerRadius: 10).stroke(UITheme.accentSoft, lineWidth: 1))
		)
	}

	private func textPanel(title: String, body: String) -> some View {
		PanelCard(title: title) {
			Text(body)
				.font(.system(size: 12, design: .monospaced))
				.foregroundStyle(UITheme.textMain)
		}
	}

	private func listPanel(title: String, items: [String]) -> some View {
		PanelCard(title: title) {
			if items.isEmpty {
				Text("-")
					.foregroundStyle(UITheme.textSub)
			} else {
				ForEach(Array(items.enumerated()), id: \.offset) { idx, item in
					Text("\(idx + 1). \(item)")
						.font(.system(size: 12, design: .monospaced))
						.foregroundStyle(UITheme.textMain)
				}
			}
		}
	}

	private func placeholder(_ text: String) -> some View {
		VStack(spacing: 8) {
			Image(systemName: "desktopcomputer")
				.font(.system(size: 28, weight: .black))
				.foregroundStyle(UITheme.textSub)
			Text(text)
				.font(.system(size: 13, weight: .bold, design: .monospaced))
				.foregroundStyle(UITheme.textSub)
		}
		.frame(maxWidth: .infinity, maxHeight: .infinity)
	}

	private func formatDate(_ isoString: String) -> String {
		let input = ISO8601DateFormatter()
		input.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
		let fallback = ISO8601DateFormatter()

		let date = input.date(from: isoString) ?? fallback.date(from: isoString)
		guard let date else { return isoString }

		let output = DateFormatter()
		output.dateFormat = "MM/dd HH:mm"
		return output.string(from: date)
	}
}

private struct TrendLineView: View {
	let points: [Double]

	var body: some View {
		GeometryReader { geo in
			let width = geo.size.width
			let height = geo.size.height
			let minValue = min(points.min() ?? 1.0, 1.0)
			let maxValue = max(points.max() ?? 6.0, 6.0)
			let span = max(0.5, maxValue - minValue)

			ZStack {
				RoundedRectangle(cornerRadius: 8)
					.fill(UITheme.panelSoft)
				if points.count >= 2 {
					Path { path in
						for (idx, point) in points.enumerated() {
							let x = width * CGFloat(idx) / CGFloat(max(points.count - 1, 1))
							let normalized = (point - minValue) / span
							let y = height - CGFloat(normalized) * (height - 10) - 5
							if idx == 0 {
								path.move(to: CGPoint(x: x, y: y))
							} else {
								path.addLine(to: CGPoint(x: x, y: y))
							}
						}
					}
					.stroke(UITheme.accent, style: StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))

					ForEach(Array(points.enumerated()), id: \.offset) { idx, point in
						let x = width * CGFloat(idx) / CGFloat(max(points.count - 1, 1))
						let normalized = (point - minValue) / span
						let y = height - CGFloat(normalized) * (height - 10) - 5
						Circle()
							.fill(UITheme.accent)
							.frame(width: 7, height: 7)
							.position(x: x, y: y)
					}
				} else {
					Text("추이 데이터 부족")
						.foregroundStyle(UITheme.textSub)
						.font(.system(size: 12, design: .monospaced))
				}
			}
		}
	}
}

private struct GrammarBarView: View {
	let items: [GrammarIssueItem]

	var body: some View {
		GeometryReader { geo in
			let maxCount = max(items.map { $0.count }.max() ?? 1, 1)
			let width = geo.size.width

			VStack(alignment: .leading, spacing: 10) {
				ForEach(items.prefix(6)) { item in
					HStack(spacing: 8) {
						Text(item.type.uppercased())
							.font(.system(size: 11, weight: .bold, design: .monospaced))
							.foregroundStyle(UITheme.textSub)
							.frame(width: 100, alignment: .leading)

						ZStack(alignment: .leading) {
							RoundedRectangle(cornerRadius: 5)
								.fill(UITheme.panelSoft)
								.frame(height: 12)

							RoundedRectangle(cornerRadius: 5)
								.fill(UITheme.accent)
								.frame(width: max(8, (width - 190) * CGFloat(item.count) / CGFloat(maxCount)), height: 12)
						}

						Text("\(item.count)")
							.font(.system(size: 11, weight: .bold, design: .monospaced))
							.foregroundStyle(UITheme.textSub)
							.frame(width: 26, alignment: .trailing)
					}
				}
				Spacer(minLength: 0)
			}
			.padding(10)
		}
	}
}

private final class AppDelegate: NSObject, NSApplicationDelegate {
	func applicationDidFinishLaunching(_ notification: Notification) {
		NSApp.activate(ignoringOtherApps: true)
	}

	func applicationWillTerminate(_ notification: Notification) {
		ServerController.shared.stopIfStarted()
	}
}

@main
private struct ToeflNativeApp: App {
	@NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

	init() {
		do {
			try ServerController.shared.startIfNeeded()
		} catch let ServerError.missingPython(path) {
			let alert = NSAlert()
			alert.messageText = "Python 가상환경을 찾을 수 없습니다"
			alert.informativeText = "다음 경로를 확인하세요:\n\(path)"
			alert.runModal()
			NSApp.terminate(nil)
		} catch {
			let alert = NSAlert()
			alert.messageText = "백엔드를 시작하지 못했습니다"
			alert.informativeText = "data/app.log를 확인해 주세요."
			alert.runModal()
			NSApp.terminate(nil)
		}
	}

	var body: some Scene {
		WindowGroup("토플첨삭기 by이강민") {
			ContentView()
				.preferredColorScheme(.light)
				.frame(minWidth: 1240, minHeight: 820)
		}
	}
}
