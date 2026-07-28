# finkritserver/conversations.py
"""
Server-side conversation threads, keyed by an opaque conversation id.

The chat endpoint is stateless HTTP, but a conversation is not: a follow-up like
"and how does that compare?" only makes sense with the previous turns in hand.
The client sends back the id it was given, and the matching thread is resumed.

Bounded on purpose. This is a public endpoint with no authentication, so an
unbounded dict of conversations is a memory leak with a stranger's hand on the
tap. Least recently used threads are evicted past `max_conversations`, and each
thread self-caps its own length (see finagent Conversation).

In memory only, so threads are lost on restart. Durable history belongs with the
persistent store work, not here.
"""
from __future__ import annotations

import uuid
from collections import OrderedDict

from finagent.assistant import Assistant
from finagent.conversation import Conversation

# A few hundred concurrent threads is far more than a single-tenant dashboard
# needs, and small enough that the memory stays trivial.
DEFAULT_MAX_CONVERSATIONS = 200


class ConversationRegistry:
    """Maps a conversation id to a live Conversation over the orchestrator."""

    def __init__(
        self,
        assistant: Assistant,
        max_conversations: int = DEFAULT_MAX_CONVERSATIONS,
    ) -> None:
        self._assistant = assistant
        self._max = max_conversations
        self._threads: OrderedDict[str, Conversation] = OrderedDict()

    def get_or_create(self, conversation_id: str | None) -> tuple[str, Conversation]:
        """Resume the named thread, or start a new one. Returns the id to hand
        back to the client along with the thread itself. An unknown id starts a
        fresh thread under that same id rather than erroring, so a client whose
        thread was evicted or lost to a restart simply continues with no memory
        instead of hitting a wall."""
        if conversation_id and conversation_id in self._threads:
            self._threads.move_to_end(conversation_id)      # mark recently used
            return conversation_id, self._threads[conversation_id]

        new_id = conversation_id or uuid.uuid4().hex
        thread = self._assistant.conversation()             # orchestrator, all domains
        self._threads[new_id] = thread
        self._evict_if_needed()
        return new_id, thread

    def _evict_if_needed(self) -> None:
        while len(self._threads) > self._max:
            self._threads.popitem(last=False)               # drop least recently used

    def reset(self, conversation_id: str) -> bool:
        """Forget a thread's history. True if there was one to forget."""
        thread = self._threads.pop(conversation_id, None)
        return thread is not None

    def __len__(self) -> int:
        return len(self._threads)
