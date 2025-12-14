import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import UploadPdfDialog from "../shared/UploadPdfDialog";
import { Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";

function PdfLibraryPage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  const token = useMemo(() => localStorage.getItem("authToken"), []);
  const headers = useMemo(
    () => ({
      Authorization: `Token ${token}`,
    }),
    [token]
  );

  const loadFiles = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await axios.get("/api/files/", { headers });
      setFiles(res.data);
    } catch (e) {
      console.error(e);
      toast.error("Failed to load PDFs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // Subscribe to ingest status updates via SSE.
  useEffect(() => {
    if (!token) return;

    const es = new EventSource("/api/files/events/");

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type !== "pdf_ingested") return;
        setFiles((prev) =>
          prev.map((f) =>
            f.file_id === data.file_id
              ? {
                  ...f,
                  is_ingested: data.is_ingested,
                  ingest_error: data.ingest_error,
                }
              : f
          )
        );
      } catch (e) {
        console.error("Failed to handle ingest_events SSE", e);
      }
    };

    es.onerror = (err) => {
      console.error("SSE connection error (PdfLibraryPage)", err);
      es.close();
    };

    return () => {
      es.close();
    };
  }, [token]);

  const handleDeleteFile = async (fileId) => {
    const confirmed = window.confirm(
      "Delete this PDF and its embeddings from your library?"
    );
    if (!confirmed) return;

    if (!token) return;

    try {
      await axios.delete(`/api/files/${fileId}/`, { headers });
      // Optimistically update local state
      setFiles((prev) => prev.filter((f) => f.file_id !== fileId));
    } catch (e) {
      console.error(e);
      toast.error("Failed to delete PDF");
    }
  };

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          padding: 16,
          borderBottom: "1px solid #eee",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h2 style={{ margin: 0, fontSize: 18 }}>My PDFs</h2>
        <div style={{ width: 220 }}>
          <UploadPdfDialog onUploaded={loadFiles} />
        </div>
      </div>

      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          padding: 16,
        }}
      >
        {loading ? (
          <div>Loading PDFs...</div>
        ) : files.length === 0 ? (
          <p style={{ fontSize: 14 }}>No PDFs uploaded yet.</p>
        ) : (
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 14,
            }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: "left",
                    padding: "8px 4px",
                    borderBottom: "1px solid #eee",
                  }}
                >
                  File name
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "8px 4px",
                    borderBottom: "1px solid #eee",
                  }}
                >
                  Uploaded at
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "8px 4px",
                    borderBottom: "1px solid #eee",
                  }}
                >
                  Status
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "8px 4px",
                    borderBottom: "1px solid #eee",
                  }}
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.file_id}>
                  <td
                    style={{
                      padding: "6px 4px",
                      borderBottom: "1px solid #f5f5f5",
                    }}
                  >
                    {f.file_name}
                  </td>
                  <td
                    style={{
                      padding: "6px 4px",
                      borderBottom: "1px solid #f5f5f5",
                      color: "#777",
                      fontSize: 13,
                    }}
                  >
                    {new Date(f.created_at).toLocaleString()}
                  </td>
                  <td
                    style={{
                      padding: "6px 4px",
                      borderBottom: "1px solid #f5f5f5",
                    }}
                  >
                    {f.is_ingested === false ? (
                      <span
                        title="Embedding in progress..."
                        style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                      >
                        <Loader2
                          size={14}
                          style={{
                            animation: "spin 1s linear infinite",
                          }}
                        />
                        Processing
                      </span>
                    ) : f.ingest_error ? (
                      <span style={{ color: "#c00", fontSize: 12 }} title={f.ingest_error}>
                        Failed
                      </span>
                    ) : (
                      <span style={{ fontSize: 12, color: "#4caf50" }}>Ready</span>
                    )}
                  </td>
                  <td
                    style={{
                      padding: "6px 4px",
                      borderBottom: "1px solid #f5f5f5",
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => handleDeleteFile(f.file_id)}
                      style={{
                        border: "none",
                        background: "transparent",
                        cursor: "pointer",
                        padding: 4,
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default PdfLibraryPage;


