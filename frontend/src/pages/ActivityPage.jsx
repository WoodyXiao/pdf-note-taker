import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { toast } from "sonner";

const ACTION_LABELS = {
  upload_pdf: "Uploaded PDF",
  delete_pdf: "Deleted PDF",
  reingest_pdf: "Retried embedding",
  create_notebook: "Created notebook",
  delete_notebook: "Deleted notebook",
  login: "Logged in",
};

function formatAction(log) {
  const label = ACTION_LABELS[log.action_type] || log.action_type;
  if (log.target_name) {
    return `${label} "${log.target_name}"`;
  }
  return label;
}

function ActivityPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const token = useMemo(() => localStorage.getItem("authToken"), []);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    axios
      .get("/api/files/activity/?limit=50", {
        headers: { Authorization: `Token ${token}` },
      })
      .then((res) => {
        setLogs(res.data?.results || []);
      })
      .catch((err) => {
        console.error("Failed to load activity", err);
        toast.error("Failed to load activity log");
      })
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div style={{ padding: 24, height: "100%", display: "flex", flexDirection: "column" }}>
      <h2 style={{ marginBottom: 16 }}>Activity</h2>

      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          border: "1px solid #eee",
          borderRadius: 4,
        }}
      >
        {loading ? (
          <div style={{ padding: 16 }}>Loading activity...</div>
        ) : logs.length === 0 ? (
          <div style={{ padding: 16, fontSize: 14 }}>No recent activity.</div>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {logs.map((log) => (
              <li
                key={log.id}
                style={{
                  padding: "10px 16px",
                  borderBottom: "1px solid #f5f5f5",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: 16,
                }}
              >
                <div style={{ fontSize: 13, color: "#555" }}>
                  {new Date(log.created_at).toLocaleString()}
                </div>
                <div style={{ fontSize: 14 }}>
                  <div>{formatAction(log)}</div>
                  {log.metadata && Object.keys(log.metadata).length > 0 && (
                    <div
                      style={{
                        marginTop: 4,
                        fontSize: 12,
                        color: "#888",
                      }}
                    >
                      {log.metadata.size_bytes != null && (
                        <span>
                          Size:{" "}
                          {Math.round(log.metadata.size_bytes / 1024)} KB
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default ActivityPage;


