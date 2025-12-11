import React, { useState } from "react";
import axios from "axios";
import { toast } from "sonner";

function NotebookChat({ notebookId }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || !notebookId) return;

    const token = localStorage.getItem("authToken");
    if (!token) {
      toast.error("Please login again.");
      return;
    }

    // Optimistic add user message
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    toast("AI is generating an answer...");

    try {
      const res = await axios.post(
        "/api/ai/answer/",
        { question, notebookId },
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );
      const answer = res.data.html || res.data.text || "";
      setMessages((prev) => [...prev, { role: "ai", content: answer }]);
    } catch (err) {
      console.error(err);
      toast.error("AI request failed");
      // Rollback last user message if needed? We'll keep it for context.
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        borderTop: "1px solid #eee",
        paddingTop: 8,
        marginTop: 8,
        display: "flex",
        flexDirection: "column",
        height: "260px",
      }}
    >
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "4px 2px",
          marginBottom: 8,
          fontSize: 13,
        }}
      >
        {messages.length === 0 ? (
          <p style={{ color: "#888" }}>
            Ask a question about the selected PDFs. Answers will appear here.
          </p>
        ) : (
          messages.map((m, idx) => (
            <div
              key={idx}
              style={{
                marginBottom: 6,
                textAlign: m.role === "user" ? "right" : "left",
              }}
            >
              <div
                style={{
                  display: "inline-block",
                  padding: "6px 10px",
                  borderRadius: 8,
                  background:
                    m.role === "user" ? "#e0f2ff" : "rgba(0,0,0,0.03)",
                }}
                // AI 回复支持简单 HTML
                dangerouslySetInnerHTML={{ __html: m.content }}
              />
            </div>
          ))
        )}
      </div>

      <form
        onSubmit={handleSend}
        style={{ display: "flex", gap: 8, alignItems: "center" }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask AI about the selected PDFs..."
          style={{ flex: 1 }}
          disabled={loading || !notebookId}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? "Asking..." : "Send"}
        </button>
      </form>
    </div>
  );
}

export default NotebookChat;


