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
	static let vocabURL = "\(baseURL)/api/vocab-analysis"
	static let weeklyReportURL = "\(baseURL)/api/weekly-report"

	static func reportURL(for submissionID: Int) -> String {
		"\(baseURL)/api/report/\(submissionID).pdf"
	}

	static func compareURL(_ id1: Int, _ id2: Int) -> String {
		"\(baseURL)/api/compare/\(id1)/\(id2)"
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
	case corrections
	case vocab
	case progress
	case weekly
	case history

	var id: String { rawValue }

	var title: String {
		switch self {
		case .overview: return "RESULT"
		case .corrections: return "교정"
		case .vocab: return "어휘"
		case .progress: return "DASHBOARD"
		case .weekly: return "주간"
		case .history: return "HISTORY"
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
	// Extended fields (optional for backward compat)
	let score_highlights: [SentenceHighlight]?
	let auto_rewrite_essay: String?
	let grammar_corrections: [GrammarCorrectionItem]?
	let target_eta: TargetEta?
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

// ── Sentence Highlights ───────────────────────────────────────────────────
private struct SentenceHighlight: Decodable {
	let sentence: String
	let impact: String // "positive", "negative", "neutral"
	let reason: String
}

// ── Grammar Correction ────────────────────────────────────────────────────
private struct GrammarCorrectionItem: Decodable {
	let sentence: String
	let error_type: String
	let corrected: String
	let explanation: String
	let severity: String
	let focus_text: String?
}

// ── Target ETA ────────────────────────────────────────────────────────────
private struct TargetEta: Decodable {
	let estimated_attempts: Int?
	let pace_label: String?
	let message: String?
}

// ── Vocabulary Analysis ───────────────────────────────────────────────────
private struct VocabAnalysis: Decodable {
	let total_words: Int
	let unique_words: Int
	let academic_word_count: Int
	let academic_ratio: Double
	let type_token_ratio: Double
	let sophistication_score: Double
	let academic_words_found: [String]
	let collocations_found: [String]
	let suggestions: [String]
}

private struct VocabAnalysisPayload: Encodable {
	let essay_text: String
}

// ── Weekly Report ─────────────────────────────────────────────────────────
private struct DailyCount: Decodable, Identifiable {
	let day: String
	let count: Int
	let avg_score: Double
	var id: String { day }
}

private struct WeeklyReport: Decodable {
	let week_attempts: Int
	let week_avg_score: Double
	let week_best_score: Double
	let week_worst_score: Double
	let most_common_error: String
	let recommendation: String
	let daily_submissions: [DailyCount]
}

// ── Compare ───────────────────────────────────────────────────────────────
private struct CompareScoreInfo: Decodable {
	let submission_id: Int
	let created_at: String
	let score_band_1_6: Double
	let estimated_score_30: Int
	let grammar_total: Int
	let strengths: [String]
	let weaknesses: [String]
}

private struct CompareResult: Decodable {
	let submission_1: CompareScoreInfo
	let submission_2: CompareScoreInfo
	let score_delta: Double
	let grammar_delta: Int
	let improvement_areas: [String]
}

// ── Saved Prompt Library ──────────────────────────────────────────────────
private struct SavedPromptItem: Codable, Identifiable {
	var id: String = UUID().uuidString
	var name: String
	var text: String
}

// ── Timer Mode ────────────────────────────────────────────────────────────
private enum TimerMode: String, CaseIterable, Identifiable {
	case integrated = "통합형 20분"
	case discussion = "토론형 10분"
	case custom = "직접 설정"

	var id: String { rawValue }

	var defaultSeconds: Int {
		switch self {
		case .integrated: return 1200
		case .discussion: return 600
		case .custom: return 900
		}
	}
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
	// Dynamic colors: automatically switch between light and dark appearances
	static let bgTop = Color(NSColor(name: nil, dynamicProvider: { app in
		app.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
			? NSColor(red: 0.09, green: 0.10, blue: 0.13, alpha: 1)
			: NSColor(red: 0.96, green: 0.97, blue: 0.99, alpha: 1)
	}))
	static let bgBottom = Color(NSColor(name: nil, dynamicProvider: { app in
		app.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
			? NSColor(red: 0.05, green: 0.07, blue: 0.09, alpha: 1)
			: NSColor(red: 0.90, green: 0.93, blue: 0.96, alpha: 1)
	}))
	static let panel = Color(NSColor(name: nil, dynamicProvider: { app in
		app.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
			? NSColor(red: 0.13, green: 0.15, blue: 0.19, alpha: 1)
			: NSColor(red: 0.99, green: 0.99, blue: 1.00, alpha: 1)
	}))
	static let panelSoft = Color(NSColor(name: nil, dynamicProvider: { app in
		app.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
			? NSColor(red: 0.10, green: 0.12, blue: 0.16, alpha: 1)
			: NSColor(red: 0.93, green: 0.95, blue: 0.98, alpha: 1)
	}))
	static let accent = Color(red: 0.00, green: 0.36, blue: 0.73)
	static let accentSoft = Color(red: 0.65, green: 0.74, blue: 0.86)
	static let textMain = Color(NSColor.labelColor)
	static let textSub = Color(NSColor.secondaryLabelColor)
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

	// Dark mode
	@AppStorage("isDarkMode") var isDarkMode: Bool = false

	// Timer
	@Published var timerMode: TimerMode = .integrated
	@Published var timerSecondsLeft: Int = TimerMode.integrated.defaultSeconds
	@Published var timerRunning: Bool = false
	@Published var timerCustomMinutes: Int = 15
	private var timerTask: Task<Void, Never>?

	// Vocab analysis
	@Published var vocabAnalysis: VocabAnalysis?
	@Published var isAnalyzingVocab: Bool = false

	// Weekly report
	@Published var weeklyReport: WeeklyReport?
	@Published var isLoadingWeekly: Bool = false

	// Compare
	@Published var compareResult: CompareResult?
	@Published var isComparing: Bool = false

	// Autosave
	@Published var lastAutosaved: Date?
	private var autosaveWorkItem: DispatchWorkItem?

	// Prompt library (stored in UserDefaults)
	@AppStorage("savedPromptsData") private var savedPromptsData: Data = Data()
	var savedPrompts: [SavedPromptItem] {
		(try? JSONDecoder().decode([SavedPromptItem].self, from: savedPromptsData)) ?? []
	}

	// Show prompt library popover
	@Published var showPromptLibrary: Bool = false

	private var keyMonitor: Any?

	func bootstrap() {
		// Restore draft if available
		if let draft = UserDefaults.standard.string(forKey: "autosaveDraft"), !draft.isEmpty, essayText.isEmpty {
			essayText = draft
		}
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

	// MARK: - Timer
	func startTimer() {
		timerRunning = true
		timerTask = Task { @MainActor [weak self] in
			while let self, self.timerRunning, self.timerSecondsLeft > 0 {
				try? await Task.sleep(nanoseconds: 1_000_000_000)
				if self.timerRunning { self.timerSecondsLeft -= 1 }
			}
			self?.timerRunning = false
		}
	}

	func pauseTimer() {
		timerRunning = false
		timerTask?.cancel()
	}

	func resetTimer() {
		timerRunning = false
		timerTask?.cancel()
		timerSecondsLeft = timerMode == .custom ? timerCustomMinutes * 60 : timerMode.defaultSeconds
	}

	// MARK: - Vocab Analysis
	func analyzeVocab() {
		guard !essayText.trimmingCharacters(in: .whitespaces).isEmpty else { return }
		isAnalyzingVocab = true
		Task {
			defer { isAnalyzingVocab = false }
			do {
				let payload = VocabAnalysisPayload(essay_text: essayText)
				let r: VocabAnalysis = try await postJSON(urlString: AppConfig.vocabURL, payload: payload, timeout: 30)
				vocabAnalysis = r
				selectedTab = .vocab
			} catch {
				errorMessage = "어휘 분석 실패: \(error.localizedDescription)"
			}
		}
	}

	// MARK: - Weekly Report
	func fetchWeeklyReport() {
		isLoadingWeekly = true
		Task {
			defer { isLoadingWeekly = false }
			do {
				weeklyReport = try await getJSON(urlString: AppConfig.weeklyReportURL, timeout: 20)
				selectedTab = .weekly
			} catch {
				errorMessage = "주간 리포트 실패: \(error.localizedDescription)"
			}
		}
	}

	// MARK: - Compare
	func compareWith(id: Int) {
		guard let currentID = lastSubmissionID, currentID != id else { return }
		isComparing = true
		Task {
			defer { isComparing = false }
			do {
				compareResult = try await getJSON(urlString: AppConfig.compareURL(currentID, id), timeout: 20)
			} catch {
				errorMessage = "비교 실패: \(error.localizedDescription)"
			}
		}
	}

	// MARK: - Autosave
	func scheduleAutosave() {
		autosaveWorkItem?.cancel()
		let work = DispatchWorkItem { [weak self] in
			guard let self else { return }
			UserDefaults.standard.set(self.essayText, forKey: "autosaveDraft")
			self.lastAutosaved = Date()
		}
		autosaveWorkItem = work
		DispatchQueue.main.asyncAfter(deadline: .now() + 120, execute: work)
	}

	// MARK: - Prompt Library
	func saveCurrentPrompt(name: String) {
		guard !name.isEmpty, !essayText.isEmpty else { return }
		var prompts = savedPrompts
		prompts.insert(SavedPromptItem(name: name, text: essayText), at: 0)
		if prompts.count > 20 { prompts = Array(prompts.prefix(20)) }
		savedPromptsData = (try? JSONEncoder().encode(prompts)) ?? Data()
	}

	func deletePrompt(id: String) {
		var prompts = savedPrompts
		prompts.removeAll { $0.id == id }
		savedPromptsData = (try? JSONEncoder().encode(prompts)) ?? Data()
	}

	// MARK: - Clipboard
	func copyToClipboard(_ text: String) {
		NSPasteboard.general.clearContents()
		NSPasteboard.general.setString(text, forType: .string)
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
			HStack {
				Text("TOEFL CONTROL PANEL")
					.font(.system(size: 22, weight: .black, design: .monospaced))
					.foregroundStyle(UITheme.textMain)
				Spacer()
				// Dark mode toggle
				Button {
					vm.isDarkMode.toggle()
				} label: {
					Image(systemName: vm.isDarkMode ? "moon.fill" : "sun.max.fill")
						.font(.system(size: 14, weight: .bold))
				}
				.buttonStyle(.bordered)
				.tint(UITheme.accent)
				.help(vm.isDarkMode ? "라이트 모드로" : "다크 모드로")
			}

			// Timer
			TimerView(vm: vm)

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
							.fill(Color.white.opacity(vm.isDarkMode ? 0.07 : 1.0))
					)
					.overlay(
						RoundedRectangle(cornerRadius: 8)
							.stroke(UITheme.accentSoft, lineWidth: 1)
					)
					.frame(minHeight: 380)
					.focused($essayEditorFocused)
					.onChange(of: vm.essayText) { _ in vm.scheduleAutosave() }

				HStack {
					Text("TOKENS: \(vm.essayText.split(whereSeparator: { $0.isWhitespace || $0.isNewline }).count)")
						.font(.system(size: 11, design: .monospaced))
						.foregroundStyle(UITheme.textSub)
					Spacer()
					if let saved = vm.lastAutosaved {
						Text("자동저장: \(saved, formatter: timeFormatter)")
							.font(.system(size: 10, design: .monospaced))
							.foregroundStyle(UITheme.textSub)
					}
				}
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

					// Prompt library
					Button {
						vm.showPromptLibrary.toggle()
					} label: {
						Image(systemName: "books.vertical")
							.font(.system(size: 13, weight: .semibold))
					}
					.buttonStyle(.bordered)
					.tint(UITheme.accent)
					.help("프롬프트 라이브러리")
					.popover(isPresented: $vm.showPromptLibrary) {
						PromptLibraryView(vm: vm, isPresented: $vm.showPromptLibrary)
					}
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

			// Extra action buttons
			HStack(spacing: 8) {
				Button {
					vm.analyzeVocab()
				} label: {
					if vm.isAnalyzingVocab {
						ProgressView().controlSize(.small)
					} else {
						Label("어휘분석", systemImage: "text.magnifyingglass")
							.font(.system(size: 11, weight: .bold, design: .monospaced))
					}
				}
				.buttonStyle(.bordered)
				.tint(UITheme.accent)
				.disabled(vm.isAnalyzingVocab || vm.essayText.isEmpty)

				Button {
					vm.fetchWeeklyReport()
				} label: {
					if vm.isLoadingWeekly {
						ProgressView().controlSize(.small)
					} else {
						Label("주간리포트", systemImage: "chart.bar.fill")
							.font(.system(size: 11, weight: .bold, design: .monospaced))
					}
				}
				.buttonStyle(.bordered)
				.tint(UITheme.accent)
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
				case .overview:
					overviewTab
				case .corrections:
					correctionsTab
				case .vocab:
					vocabTab
				case .progress:
					progressTab
				case .weekly:
					weeklyTab
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

					// Target ETA
					if let eta = result.target_eta {
						PanelCard(title: "타겟 달성 예측") {
							HStack(spacing: 16) {
								VStack(alignment: .leading, spacing: 4) {
									Text("예상 남은 횟수")
										.font(.system(size: 10, design: .monospaced))
										.foregroundStyle(UITheme.textSub)
									Text(eta.estimated_attempts.map { "\($0)회" } ?? "-")
										.font(.system(size: 18, weight: .black, design: .monospaced))
										.foregroundStyle(UITheme.accent)
								}
								if let pace = eta.pace_label {
									VStack(alignment: .leading, spacing: 4) {
										Text("페이스")
											.font(.system(size: 10, design: .monospaced))
											.foregroundStyle(UITheme.textSub)
										Text(pace)
											.font(.system(size: 13, weight: .bold, design: .monospaced))
											.foregroundStyle(UITheme.textMain)
									}
								}
							}
							if let msg = eta.message {
								Text(msg)
									.font(.system(size: 11, design: .monospaced))
									.foregroundStyle(UITheme.textSub)
							}
						}
					}

					// Auto rewrite
					if let autoRewrite = result.auto_rewrite_essay, !autoRewrite.isEmpty {
						PanelCard(title: "AUTO.REWRITE") {
							Text(autoRewrite)
								.font(.system(size: 11, design: .monospaced))
								.foregroundStyle(UITheme.textMain)
							Button {
								vm.copyToClipboard(autoRewrite)
							} label: {
								Label("교정문 복사", systemImage: "doc.on.doc")
									.font(.system(size: 10, design: .monospaced))
							}
							.buttonStyle(.plain)
							.foregroundStyle(UITheme.accent)
						}
					}

					// Sentence highlights
					if let highlights = result.score_highlights, !highlights.isEmpty {
						PanelCard(title: "SENTENCE.SCORE") {
							ForEach(Array(highlights.prefix(8).enumerated()), id: \.offset) { _, h in
								HStack(alignment: .top, spacing: 8) {
									Circle()
										.fill(h.impact == "positive" ? Color.green.opacity(0.85)
											: h.impact == "negative" ? Color.red.opacity(0.75)
											: Color.orange.opacity(0.75))
										.frame(width: 8, height: 8)
										.padding(.top, 4)
									VStack(alignment: .leading, spacing: 2) {
										Text(h.sentence)
											.font(.system(size: 11, design: .monospaced))
											.foregroundStyle(UITheme.textMain)
										Text(h.reason)
											.font(.system(size: 10, design: .monospaced))
											.foregroundStyle(UITheme.textSub)
									}
								}
							}
						}
					}

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
			// Compare result overlay
			if let cmp = vm.compareResult {
				PanelCard(title: "\u2194️ 비교: #\(cmp.submission_1.submission_id) vs #\(cmp.submission_2.submission_id)") {
					HStack(spacing: 10) {
						VStack(alignment: .leading, spacing: 4) {
							Text("#\(cmp.submission_1.submission_id) \u2014 \(cmp.submission_1.created_at)")
								.font(.system(size: 10, design: .monospaced)).foregroundStyle(UITheme.textSub)
							Text(String(format: "%.1f점", cmp.submission_1.score_band_1_6))
								.font(.system(size: 18, weight: .black, design: .monospaced)).foregroundStyle(UITheme.textMain)
							Text("문법 \(cmp.submission_1.grammar_total)개")
								.font(.system(size: 11, design: .monospaced)).foregroundStyle(UITheme.textSub)
						}
						VStack {
							Image(systemName: cmp.score_delta >= 0 ? "arrow.up.circle.fill" : "arrow.down.circle.fill")
								.font(.system(size: 20)).foregroundStyle(cmp.score_delta >= 0 ? .green : .red)
							Text(String(format: "%+.1f", cmp.score_delta))
								.font(.system(size: 12, weight: .bold, design: .monospaced))
								.foregroundStyle(cmp.score_delta >= 0 ? .green : .red)
						}
						VStack(alignment: .leading, spacing: 4) {
							Text("#\(cmp.submission_2.submission_id) \u2014 \(cmp.submission_2.created_at)")
								.font(.system(size: 10, design: .monospaced)).foregroundStyle(UITheme.textSub)
							Text(String(format: "%.1f점", cmp.submission_2.score_band_1_6))
								.font(.system(size: 18, weight: .black, design: .monospaced)).foregroundStyle(UITheme.textMain)
							Text("문법 \(cmp.submission_2.grammar_total)개")
								.font(.system(size: 11, design: .monospaced)).foregroundStyle(UITheme.textSub)
						}
					}
					ForEach(cmp.improvement_areas, id: \.self) { area in
						Text("• \(area)").font(.system(size: 11, design: .monospaced)).foregroundStyle(UITheme.textMain)
					}
					Button("닫기") { vm.compareResult = nil }
						.buttonStyle(.plain).foregroundStyle(UITheme.textSub)
						.font(.system(size: 11, design: .monospaced))
				}
				.padding(.horizontal, 12)
			}
		}
	}

	// ── Corrections Tab ─────────────────────────────────────────────────
	private var correctionsTab: some View {
		Group {
			if let corrections = vm.result?.grammar_corrections, !corrections.isEmpty {
				ScrollView {
					VStack(alignment: .leading, spacing: 12) {
						HStack {
							Text("GRAMMAR CORRECTIONS")
								.font(.system(size: 21, weight: .black, design: .monospaced))
								.foregroundStyle(UITheme.textMain)
							Spacer()
							Button {
								let all = corrections.map {
									"[\($0.severity.uppercased())] \($0.error_type)\n원문: \($0.sentence)\n교정: \($0.corrected)\n설명: \($0.explanation)"
								}.joined(separator: "\n\n")
								vm.copyToClipboard(all)
							} label: {
								Label("전체 복사", systemImage: "doc.on.doc")
									.font(.system(size: 11, weight: .bold, design: .monospaced))
							}
							.buttonStyle(.bordered)
							.tint(UITheme.accent)
						}
						ForEach(Array(corrections.enumerated()), id: \.offset) { _, c in
							PanelCard(title: "[\(c.severity.uppercased())] \(c.error_type.uppercased())") {
								Text("원문: \(c.sentence)")
									.font(.system(size: 11, design: .monospaced))
									.foregroundStyle(UITheme.textSub)
								Text("교정: \(c.corrected)")
									.font(.system(size: 12, weight: .semibold, design: .monospaced))
									.foregroundStyle(UITheme.accent)
								Text(c.explanation)
									.font(.system(size: 11, design: .monospaced))
									.foregroundStyle(UITheme.textSub)
								Button {
									vm.copyToClipboard("\(c.sentence) → \(c.corrected)")
								} label: {
									Label("복사", systemImage: "doc.on.doc")
										.font(.system(size: 10, design: .monospaced))
								}
								.buttonStyle(.plain)
								.foregroundStyle(UITheme.accent)
							}
						}
					}
					.padding(16)
				}
			} else {
				placeholder("채점 후 교정 결과가 표시됩니다.")
			}
		}
	}

	// ── Vocab Tab ────────────────────────────────────────────────────────
	private var vocabTab: some View {
		Group {
			if let vocab = vm.vocabAnalysis {
				ScrollView {
					VStack(alignment: .leading, spacing: 12) {
						Text("VOCABULARY ANALYSIS")
							.font(.system(size: 21, weight: .black, design: .monospaced))
							.foregroundStyle(UITheme.textMain)
						HStack(spacing: 10) {
							scoreCard(title: "총 단어", value: "\(vocab.total_words)")
							scoreCard(title: "고유 단어", value: "\(vocab.unique_words)")
							scoreCard(title: "학술 어휘", value: "\(vocab.academic_word_count)")
						}
						PanelCard(title: "어휘 지수") {
							VStack(alignment: .leading, spacing: 6) {
								HStack {
									Text("학술 어휘 비율")
										.font(.system(size: 11, design: .monospaced)).foregroundStyle(UITheme.textSub)
									Spacer()
									Text("\(Int(vocab.academic_ratio * 100))%")
										.font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundStyle(UITheme.textMain)
								}
								HStack {
									Text("어휘 다양성(TTR)")
										.font(.system(size: 11, design: .monospaced)).foregroundStyle(UITheme.textSub)
									Spacer()
									Text("\(Int(vocab.type_token_ratio * 100))%")
										.font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundStyle(UITheme.textMain)
								}
								HStack {
									Text("정교함 점수")
										.font(.system(size: 11, design: .monospaced)).foregroundStyle(UITheme.textSub)
									Spacer()
									Text(String(format: "%.1f / 100", vocab.sophistication_score))
										.font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundStyle(UITheme.accent)
								}
							}
						}
						if !vocab.collocations_found.isEmpty {
							PanelCard(title: "연결어 사용 ✓") {
								ForEach(vocab.collocations_found, id: \.self) { c in
									Text("• \(c)").font(.system(size: 12, design: .monospaced)).foregroundStyle(UITheme.textMain)
								}
							}
						}
						if !vocab.academic_words_found.isEmpty {
							PanelCard(title: "학술 어휘 목록") {
								Text(vocab.academic_words_found.joined(separator: "  ·  "))
									.font(.system(size: 11, design: .monospaced)).foregroundStyle(UITheme.textSub)
							}
						}
						if !vocab.suggestions.isEmpty {
							listPanel(title: "개선 제안", items: vocab.suggestions)
						}
					}
					.padding(16)
				}
			} else {
				VStack(spacing: 12) {
					placeholder("왼쪽 '어휘분석' 버튼을 눌러 실행하세요.")
					Button {
						vm.analyzeVocab()
					} label: {
						if vm.isAnalyzingVocab {
							ProgressView()
						} else {
							Label("어휘 분석 실행", systemImage: "text.magnifyingglass")
								.font(.system(size: 13, weight: .bold, design: .monospaced))
						}
					}
					.buttonStyle(.borderedProminent)
					.tint(UITheme.accent)
				}
			}
		}
	}

	// ── Weekly Tab ───────────────────────────────────────────────────────
	private var weeklyTab: some View {
		Group {
			if let report = vm.weeklyReport {
				ScrollView {
					VStack(alignment: .leading, spacing: 12) {
						Text("WEEKLY REPORT")
							.font(.system(size: 21, weight: .black, design: .monospaced))
							.foregroundStyle(UITheme.textMain)
						HStack(spacing: 10) {
							scoreCard(title: "이번 주 제출", value: "\(report.week_attempts)회")
							scoreCard(title: "평균 점수", value: String(format: "%.1f", report.week_avg_score))
							scoreCard(title: "최고 점수", value: String(format: "%.1f", report.week_best_score))
						}
						PanelCard(title: "주요 오류") {
							Text("가장 많은 오류 유형: \(report.most_common_error.uppercased())")
								.font(.system(size: 13, weight: .bold, design: .monospaced))
								.foregroundStyle(UITheme.textMain)
						}
						textPanel(title: "코치 피드백", body: report.recommendation)
						if !report.daily_submissions.isEmpty {
							PanelCard(title: "일별 현황") {
								ForEach(report.daily_submissions) { day in
									HStack {
										Text(day.day).font(.system(size: 11, design: .monospaced))
											.foregroundStyle(UITheme.textSub).frame(width: 90, alignment: .leading)
										Text("\(day.count)회").font(.system(size: 11, weight: .bold, design: .monospaced))
											.foregroundStyle(UITheme.textMain)
										Text("평균 \(String(format: "%.1f", day.avg_score))")
											.font(.system(size: 11, design: .monospaced)).foregroundStyle(UITheme.textSub)
									}
								}
							}
						}
					}
					.padding(16)
				}
			} else {
				VStack(spacing: 12) {
					placeholder("왼쪽 '주간리포트' 버튼을 눌러 로드하세요.")
					Button {
						vm.fetchWeeklyReport()
					} label: {
						if vm.isLoadingWeekly {
							ProgressView()
						} else {
							Label("주간 리포트 로드", systemImage: "chart.bar.fill")
								.font(.system(size: 13, weight: .bold, design: .monospaced))
						}
					}
					.buttonStyle(.borderedProminent)
					.tint(UITheme.accent)
				}
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

private let timeFormatter: DateFormatter = {
	let f = DateFormatter()
	f.dateFormat = "HH:mm"
	return f
}()

// ── Timer View ────────────────────────────────────────────────────────────
private struct TimerView: View {
	@ObservedObject var vm: AppViewModel

	var body: some View {
		PanelCard(title: "⏱ TIMER") {
			HStack(spacing: 8) {
				Text(timeString(vm.timerSecondsLeft))
					.font(.system(size: 22, weight: .black, design: .monospaced))
					.foregroundStyle(vm.timerSecondsLeft <= 60 && vm.timerSecondsLeft > 0
						? Color.red : UITheme.textMain)
					.animation(.default, value: vm.timerSecondsLeft)
				Spacer()
				if vm.timerRunning {
					Button("일시정지") { vm.pauseTimer() }
						.buttonStyle(.bordered).tint(UITheme.accent)
						.font(.system(size: 11, design: .monospaced))
				} else {
					Button("시작") { vm.startTimer() }
						.buttonStyle(.borderedProminent).tint(UITheme.accent)
						.font(.system(size: 11, weight: .bold, design: .monospaced))
				}
				Button("초기화") { vm.resetTimer() }
					.buttonStyle(.plain).foregroundStyle(UITheme.textSub)
					.font(.system(size: 11, design: .monospaced))
			}
			Picker("모드", selection: $vm.timerMode) {
				ForEach(TimerMode.allCases) { mode in
					Text(mode.rawValue).tag(mode)
				}
			}
			.labelsHidden()
			.pickerStyle(.segmented)
			.onChange(of: vm.timerMode) { _ in vm.resetTimer() }

			if vm.timerMode == .custom {
				Stepper("직접: \(vm.timerCustomMinutes)분", value: $vm.timerCustomMinutes, in: 1...60)
					.font(.system(size: 11, design: .monospaced))
					.foregroundStyle(UITheme.textMain)
					.onChange(of: vm.timerCustomMinutes) { _ in
						if !vm.timerRunning { vm.resetTimer() }
					}
			}
		}
	}

	private func timeString(_ s: Int) -> String {
		String(format: "%02d:%02d", s / 60, s % 60)
	}
}

// ── Prompt Library View ───────────────────────────────────────────────────
private struct PromptLibraryView: View {
	@ObservedObject var vm: AppViewModel
	@Binding var isPresented: Bool
	@State private var newName = ""
	@State private var showSaveForm = false

	var body: some View {
		VStack(alignment: .leading, spacing: 10) {
			Text("프롬프트 라이브러리")
				.font(.system(size: 14, weight: .black, design: .monospaced))
				.foregroundStyle(UITheme.textMain)

			if showSaveForm {
				HStack {
					TextField("저장 이름", text: $newName)
						.textFieldStyle(.roundedBorder)
						.font(.system(size: 12))
					Button("저장") {
						vm.saveCurrentPrompt(name: newName)
						newName = ""
						showSaveForm = false
					}
					.disabled(newName.isEmpty)
					.buttonStyle(.borderedProminent).tint(UITheme.accent)
					Button("취소") { showSaveForm = false }
						.buttonStyle(.plain).foregroundStyle(UITheme.textSub)
				}
			} else {
				Button {
					showSaveForm = true
				} label: {
					Label("현재 입력 저장", systemImage: "square.and.arrow.down")
						.font(.system(size: 11, weight: .bold, design: .monospaced))
				}
				.buttonStyle(.bordered).tint(UITheme.accent)
				.disabled(vm.essayText.isEmpty)
			}
			Divider()
			if vm.savedPrompts.isEmpty {
				Text("저장된 프롬프트 없음")
					.font(.system(size: 11, design: .monospaced))
					.foregroundStyle(UITheme.textSub)
			} else {
				ScrollView {
					VStack(spacing: 6) {
						ForEach(vm.savedPrompts) { prompt in
							HStack {
								VStack(alignment: .leading, spacing: 2) {
									Text(prompt.name)
										.font(.system(size: 12, weight: .bold, design: .monospaced))
										.foregroundStyle(UITheme.textMain)
									Text(String(prompt.text.prefix(50)) + (prompt.text.count > 50 ? "..." : ""))
										.font(.system(size: 10, design: .monospaced))
										.foregroundStyle(UITheme.textSub)
								}
								Spacer()
								Button("불러오기") {
									vm.essayText = prompt.text
									isPresented = false
								}
								.buttonStyle(.bordered).tint(UITheme.accent)
								.font(.system(size: 10))
								Button {
									vm.deletePrompt(id: prompt.id)
								} label: {
									Image(systemName: "trash")
								}
								.buttonStyle(.plain).foregroundStyle(Color.red.opacity(0.7))
							}
							.padding(.vertical, 4)
						}
					}
				}
				.frame(maxHeight: 200)
			}
		}
		.padding(16)
		.frame(width: 380)
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
				.frame(minWidth: 1240, minHeight: 820)
		}
	}
}
