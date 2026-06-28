"""Mock OpenAI-compatible API server for MVP manual acceptance.

Provides:
- POST /v1/embeddings: returns deterministic fake embeddings
- POST /v1/chat/completions: returns fake streaming chat response
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler


def _fake_embedding(text: str, dim: int = 1024) -> list[float]:
    """Generate deterministic embedding from text hash."""
    h = abs(hash(text)) % 10000
    return [float((h + i) % 100) / 100.0 - 0.5 for i in range(dim)]


class MockHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}

        if "/embeddings" in self.path:
            inputs = payload.get("input", [])
            if isinstance(inputs, str):
                inputs = [inputs]
            dim = 1024
            data = [
                {"object": "embedding", "index": i, "embedding": _fake_embedding(t, dim)}
                for i, t in enumerate(inputs)
            ]
            self._respond(200, {"object": "list", "data": data, "model": "mock", "usage": {"prompt_tokens": 1}})

        elif "/chat/completions" in self.path:
            stream = payload.get("stream", False)
            if stream:
                self._respond_stream()
            else:
                self._respond(200, {
                    "id": "mock-chat",
                    "object": "chat.completion",
                    "model": "mock",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "这是Mock LLM的回答。"}, "finish_reason": "stop"}],
                })

        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, data: dict) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        body = json.dumps(data).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _respond_stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for chunk_text in ["这是", "Mock", "LLM", "的", "回答", "。"]:
            chunk = {
                "id": "mock-chat",
                "object": "chat.completion.chunk",
                "model": "mock",
                "choices": [{"index": 0, "delta": {"content": chunk_text}, "finish_reason": None}],
            }
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
            self.wfile.flush()
        done_chunk = {
            "id": "mock-chat",
            "object": "chat.completion.chunk",
            "model": "mock",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        self.wfile.write(f"data: {json.dumps(done_chunk)}\n\n".encode("utf-8"))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, format, *args) -> None:  # noqa: A002
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8089), MockHandler)
    print("Mock OpenAI server on http://127.0.0.1:8089", flush=True)
    server.serve_forever()
