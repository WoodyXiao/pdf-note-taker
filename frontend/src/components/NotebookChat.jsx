import React, { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";

function NotebookChat({ notebookId }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Load recent messages on mount.
  useEffect(() => {
    if (!notebookId) return;
    const token = localStorage.getItem("authToken");
    if (!token) return;

    axios
      .get(`/api/files/notebooks/${notebookId}/messages/?channel=notebook_chat`, {
        headers: { Authorization: `Token ${token}` },
      })
      .then((res) => {
        // Map API shape to local shape
        const msgs = (res.data || []).map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content_html,
          createdAt: m.created_at,
        }));
        setMessages(msgs);
      })
      .catch((err) => {
        console.error("Failed to load notebook messages", err);
      });
  }, [notebookId]);

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
    const tempCreatedAt = new Date().toISOString();
    const userMessage = { role: "user", content: question, createdAt: tempCreatedAt };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Persist the user message
      const savedUser = await axios.post(
        `/api/files/notebooks/${notebookId}/messages/`,
        {
          role: "user",
          channel: "notebook_chat",
          contentHtml: question,
        },
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );

      // Replace the temporary user message with the saved one (to get accurate timestamp)
      if (savedUser?.data) {
        setMessages((prev) => {
          const copy = [...prev];
          // Replace the last user message (optimistic one)
          const idx = copy.findIndex(
            (m, index) => m.role === "user" && index === copy.length - 1
          );
          if (idx !== -1) {
            copy[idx] = {
              role: "user",
              content: savedUser.data.content_html || question,
              createdAt: savedUser.data.created_at,
            };
          }
          return copy;
        });
      }

      const res = await axios.post(
        "/api/ai/answer/",
        { question, notebookId, channel: "notebook_chat" },
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );
      const answer = res.data.html || res.data.text || "";
      const aiCreatedAt = new Date().toISOString();
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: answer, createdAt: aiCreatedAt },
      ]);
    } catch (err) {
      console.error(err);
      toast.error("AI request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        borderTop: "1px solid #eee",
        paddingTop: 8,
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
      {/* Header */}
      <div
        style={{
          fontSize: 13,
          fontWeight: 500,
          color: "#444",
          marginBottom: 4,
        }}
      >
        Notebook Chat
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          minHeight: 0, // allow this area to shrink so the input stays visible
          overflowY: "auto",
          padding: "4px 2px",
          marginBottom: 8,
          fontSize: 13,
          border: "1px solid #f0f0f0",
          borderRadius: 6,
          background: "#fafafa",
        }}
      >
        {messages.length === 0 ? (
          <p style={{ color: "#888", margin: 8 }}>
            Ask a question about the selected PDFs. Answers will appear here.
          </p>
        ) : (
          messages.map((m, idx) => (
            <div
              key={idx}
              style={{
                margin: "6px 8px",
                textAlign: m.role === "user" ? "right" : "left",
              }}
            >
              <div
                style={{
                  display: "inline-block",
                  maxWidth: "90%",
                  padding: "6px 10px",
                  borderRadius: 8,
                  background:
                    m.role === "user" ? "#e0f2ff" : "rgba(0,0,0,0.03)",
                  color: "#222",
                  textAlign: "left",
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    color: "#777",
                    marginBottom: 2,
                  }}
                >
                  {m.role === "user" ? "You" : "AI"}
                </div>
                {/* AI 回复支持简单 HTML */}
                <div
                  dangerouslySetInnerHTML={{ __html: m.content }}
                />
                {m.createdAt && (
                  <div
                    style={{
                      marginTop: 4,
                      fontSize: 11,
                      color: "#999",
                      textAlign: "right",
                    }}
                  >
                    {new Date(m.createdAt).toLocaleString()}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <div
        style={{
          padding: "0 2px", // 对齐上面的 messages 宽度
        }}
      >
        <form
          onSubmit={handleSend}
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask AI about the selected PDFs..."
            style={{
              flex: 1,
              padding: "6px 8px",
              borderRadius: 4,
              border: "1px solid #ddd",
              fontSize: 13,
            }}
            disabled={loading || !notebookId}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            style={{
              padding: "6px 10px",
              fontSize: 13,
            }}
          >
            {loading ? "Asking..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default NotebookChat;


