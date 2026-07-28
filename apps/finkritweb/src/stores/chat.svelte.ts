// Chat state — a single reactive instance shared across every component that
// imports it. The right panel opens on the first message and stays until
// closed; the dock at the bottom is what's visible while it's closed.
import { api, ApiError } from '$api/client';

export type ChatMessage = {
	role: 'user' | 'assistant';
	text: string;
	// Which specialists answered, shown as pills under an assistant reply so the
	// fan out is visible rather than implied. Absent on user messages and on
	// answers the orchestrator gave without delegating.
	specialists?: string[];
};

// Panel width bounds. Wide enough to read a paragraph, capped so the portfolio
// it is answering about never gets squeezed off screen.
export const MIN_WIDTH = 320;
export const MAX_WIDTH = 760;
// Opens wide. An answer is prose plus figures, and a narrow column turns every
// reply into a ragged sliver. Easier to drag it smaller when the portfolio needs
// the room than to discover the handle and drag it bigger.
const DEFAULT_WIDTH = 620;
const WIDTH_KEY = 'finkrit.chat.width';

function storedWidth(): number {
	if (typeof localStorage === 'undefined') return DEFAULT_WIDTH;
	const saved = Number(localStorage.getItem(WIDTH_KEY));
	return Number.isFinite(saved) && saved >= MIN_WIDTH ? Math.min(saved, MAX_WIDTH) : DEFAULT_WIDTH;
}
// Note: no viewport math here. This runs once when the module loads, so any
// window size read at that moment can be stale by the time the panel renders.
// Keeping the panel from swallowing a small screen is a max-width in the
// panel's own CSS, which re-evaluates on every resize for free.

class ChatState {
	open = $state(false);
	sending = $state(false);
	messages = $state<ChatMessage[]>([]);
	// Panel width, dragged by the resize handle and remembered across reloads.
	width = $state(storedWidth());

	setWidth(px: number) {
		this.width = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, Math.round(px)));
	}

	persistWidth() {
		try {
			localStorage.setItem(WIDTH_KEY, String(this.width));
		} catch {
			// Private mode or a full quota. The width still works for this session.
		}
	}

	// Issued by the server on the first question and echoed back on every later
	// one, which is what threads the conversation so follow-ups keep context.
	// Not reactive state: nothing renders it, it is just carried between calls.
	private conversationId: string | undefined;

	close() {
		this.open = false;
	}

	/** Clear the transcript and start a new thread, so the next question arrives
	 *  with no prior context. Tells the server to drop its copy too. */
	reset() {
		const previous = this.conversationId;
		this.conversationId = undefined;
		this.messages = [];
		if (previous) void api.resetConversation(previous).catch(() => {});
	}

	async send(text: string) {
		const question = text.trim();
		if (!question || this.sending) return;

		this.open = true; // asking a question expands the right panel
		this.messages.push({ role: 'user', text: question });
		this.sending = true;
		try {
			const { answer, conversation_id, specialists } = await api.ask(
				question,
				this.conversationId
			);
			this.conversationId = conversation_id;
			this.messages.push({ role: 'assistant', text: answer, specialists });
		} catch (err) {
			const text = err instanceof ApiError ? err.message : 'Something went wrong.';
			this.messages.push({ role: 'assistant', text });
		} finally {
			this.sending = false;
		}
	}
}

export const chat = new ChatState();
