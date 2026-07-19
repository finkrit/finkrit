// Chat state — a single reactive instance shared across every component that
// imports it. The right panel opens on the first message and stays until
// closed; the dock at the bottom is what's visible while it's closed.
import { api, ApiError } from '$api/client';

export type ChatMessage = { role: 'user' | 'assistant'; text: string };

class ChatState {
	open = $state(false);
	sending = $state(false);
	messages = $state<ChatMessage[]>([]);

	close() {
		this.open = false;
	}

	async send(text: string) {
		const question = text.trim();
		if (!question || this.sending) return;

		this.open = true; // asking a question expands the right panel
		this.messages.push({ role: 'user', text: question });
		this.sending = true;
		try {
			const { answer } = await api.ask(question);
			this.messages.push({ role: 'assistant', text: answer });
		} catch (err) {
			const text = err instanceof ApiError ? err.message : 'Something went wrong.';
			this.messages.push({ role: 'assistant', text });
		} finally {
			this.sending = false;
		}
	}
}

export const chat = new ChatState();
