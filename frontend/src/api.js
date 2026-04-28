// SSE + fetch helpers. No localStorage / sessionStorage anywhere.
import { fetchEventSource } from "@microsoft/fetch-event-source";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(
  /\/+$/,
  "",
);

/** GET /health */
export async function fetchHealth() {
  const res = await fetch(`${API_URL}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

/** GET /sources */
export async function fetchSources() {
  const res = await fetch(`${API_URL}/sources`);
  if (!res.ok) {
    throw new Error(`Failed to load sources: ${res.status}`);
  }
  return res.json();
}

/**
 * Stream a chat response from POST /chat.
 *
 * @param {string} question — user question
 * @param {object} handlers
 * @param {(token: string) => void} handlers.onToken   — called for each token
 * @param {(sources: string[]) => void} handlers.onDone — called once with the final source list
 * @param {(error: string) => void} handlers.onError   — called on any error
 * @param {AbortSignal} [handlers.signal]              — optional abort signal
 */
export async function streamChat(question, { onToken, onDone, onError, signal }) {
  try {
    await fetchEventSource(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
      openWhenHidden: true,

      onopen: async (response) => {
        if (!response.ok) {
          const text = await response.text().catch(() => "");
          throw new Error(`Backend error ${response.status}: ${text || response.statusText}`);
        }
      },

      onmessage: (msg) => {
        if (!msg.data) return;
        let payload;
        try {
          payload = JSON.parse(msg.data);
        } catch {
          return;
        }
        if (payload.error) {
          onError?.(payload.error);
          return;
        }
        if (payload.token) {
          onToken?.(payload.token);
          return;
        }
        if (payload.done) {
          onDone?.(payload.sources || []);
        }
      },

      onerror: (err) => {
        // Throwing here stops fetchEventSource from retrying.
        throw err;
      },
    });
  } catch (err) {
    if (err?.name === "AbortError") return;
    onError?.(err?.message || String(err));
  }
}
