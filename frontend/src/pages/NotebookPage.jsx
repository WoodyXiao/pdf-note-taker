import React, { useEffect, useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import TextEditor from "../components/TextEditor";
import NotebookChat from "../components/NotebookChat";
import { Trash2 } from "lucide-react";
import UploadPdfDialog from "../shared/UploadPdfDialog";

function NotebookPage() {
  const { notebookId } = useParams();
  const [notebook, setNotebook] = useState(null);
  const [files, setFiles] = useState([]);
  const [selectedFileIds, setSelectedFileIds] = useState([]);
  const [previewFileId, setPreviewFileId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("authToken");
    if (!token) return;

    const headers = { Authorization: `Token ${token}` };

    async function load() {
      try {
        const [nbRes, filesRes, nbFilesRes] = await Promise.all([
          axios.get(`/api/files/notebooks/${notebookId}/`, { headers }),
          axios.get("/api/files/", { headers }),
          axios.get(`/api/files/notebooks/${notebookId}/files/`, { headers }),
        ]);

        setNotebook(nbRes.data);
        setFiles(filesRes.data);
        setSelectedFileIds(nbFilesRes.data.fileIds || []);

        // 默认预览：优先选中列表中的第一个 PDF
        const initialPreview =
          nbFilesRes.data.fileIds?.[0] || filesRes.data[0]?.file_id || null;
        setPreviewFileId(initialPreview);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [notebookId]);

  const token = useMemo(() => localStorage.getItem("authToken"), []);

  const headers = useMemo(
    () => ({
      Authorization: `Token ${token}`,
    }),
    [token]
  );

  const refreshFiles = async () => {
    if (!token) return;
    try {
      const [filesRes, nbFilesRes] = await Promise.all([
        axios.get("/api/files/", { headers }),
        axios.get(`/api/files/notebooks/${notebookId}/files/`, { headers }),
      ]);
      setFiles(filesRes.data);
      setSelectedFileIds(nbFilesRes.data.fileIds || []);

      // If no preview chosen yet, default to first selected/first file
      if (!previewFileId) {
        const initialPreview =
          nbFilesRes.data.fileIds?.[0] || filesRes.data[0]?.file_id || null;
        setPreviewFileId(initialPreview);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const updateNotebookSelection = async (newSelected) => {
    setSelectedFileIds(newSelected);
    try {
      await axios.put(
        `/api/files/notebooks/${notebookId}/files/`,
        { fileIds: newSelected },
        { headers }
      );
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleFile = async (fileId) => {
    const newSelected = selectedFileIds.includes(fileId)
      ? selectedFileIds.filter((id) => id !== fileId)
      : [...selectedFileIds, fileId];

    updateNotebookSelection(newSelected);
  };

  const handleSelectAll = () => {
    const allIds = files.map((f) => f.file_id);
    updateNotebookSelection(allIds);
  };

  const handleClearAll = () => {
    updateNotebookSelection([]);
  };

  const currentPreviewFile = files.find((f) => f.file_id === previewFileId) || null;
  const handleDeleteFile = async (fileId) => {
    const confirmed = window.confirm(
      "Delete this PDF and its embeddings from this workspace?"
    );
    if (!confirmed) return;

    const token = localStorage.getItem("authToken");
    if (!token) return;

    try {
      await axios.delete(`/api/files/${fileId}/`, {
        headers: {
          Authorization: `Token ${token}`,
        },
      });

      // Remove from local state
      setFiles((prev) => prev.filter((f) => f.file_id !== fileId));
      setSelectedFileIds((prev) => prev.filter((id) => id !== fileId));

      if (previewFileId === fileId) {
        const remaining = files.filter((f) => f.file_id !== fileId);
        setPreviewFileId(remaining[0]?.file_id || null);
      }
    } catch (e) {
      console.error(e);
      alert("Failed to delete PDF.");
    }
  };

  if (loading) {
    return <div style={{ padding: 24 }}>Loading notebook...</div>;
  }

  if (!notebook) {
    return <div style={{ padding: 24 }}>Notebook not found.</div>;
  }

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: 16,
          display: "flex",
          justifyContent: "space-between",
          borderBottom: "1px solid #eee",
        }}
      >
        <div>PDF Note Taker</div>
        <h2 style={{ fontWeight: "bold" }}>{notebook.name}</h2>
      </div>

      {/* Main layout: left list, center editor, right PDF preview */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "260px 1fr 420px",
          gap: 16,
          padding: 16,
          flex: 1,
          minHeight: 0,
        }}
      >
        {/* Left: PDF list with checkboxes */}
        <div
          style={{
            border: "1px solid #eee",
            borderRadius: 4,
            padding: 12,
            overflowY: "auto",
            height: "100%",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <h3 style={{ fontSize: 14, margin: 0 }}>PDFs in this notebook</h3>
            <div style={{ display: "flex", gap: 4 }}>
              {files.length > 0 && (
                <button
                  type="button"
                  onClick={
                    selectedFileIds.length === files.length
                      ? handleClearAll
                      : handleSelectAll
                  }
                  style={{ fontSize: 11, padding: "2px 6px" }}
                >
                  {selectedFileIds.length === files.length
                    ? "Uncheck all"
                    : "Check all"}
                </button>
              )}
            </div>
          </div>
          <div style={{ marginBottom: 8 }}>
            <UploadPdfDialog onUploaded={refreshFiles} />
          </div>
          {files.length === 0 ? (
            <p style={{ fontSize: 12 }}>No PDFs uploaded yet.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {files.map((f) => {
                const checked = selectedFileIds.includes(f.file_id);
                return (
                  <li
                    key={f.file_id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "6px 4px",
                      borderBottom: "1px solid #f5f5f5",
                      cursor: "pointer",
                    }}
                    onClick={() => setPreviewFileId(f.file_id)}
                  >
                    <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onClick={(e) => e.stopPropagation()}
                        onChange={() => handleToggleFile(f.file_id)}
                      />
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontSize: 13 }}>{f.file_name}</span>
                        <span
                          style={{
                            fontSize: 11,
                            color: "#888",
                          }}
                        >
                          {new Date(f.created_at).toLocaleString()}
                        </span>
                      </div>
                    </label>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteFile(f.file_id);
                      }}
                      style={{
                        border: "none",
                        background: "transparent",
                        cursor: "pointer",
                        padding: 4,
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Center: Notebook editor (TipTap) */}
        <div style={{ height: "100%", minHeight: 0 }}>
          <TextEditor notebookId={notebookId} />
        </div>

        {/* Right: PDF preview + chat (each takes ~50% of height) */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
            gap: 8,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              flex: 1,
              minHeight: 0,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            {/* Current PDF name */}
            <div style={{ fontSize: 13, color: "#555", flex: "0 0 auto" }}>
              {currentPreviewFile ? (
                <>Viewing: {currentPreviewFile.file_name}</>
              ) : (
                "No PDF selected"
              )}
            </div>

            {/* PDF preview */}
            <div style={{ flex: 1, minHeight: 0 }}>
              {currentPreviewFile ? (
                <iframe
                  src={currentPreviewFile.file_url + "#toolbar=0"}
                  style={{ border: "none", width: "100%", height: "100%" }}
                />
              ) : (
                <div
                  style={{
                    border: "1px solid #eee",
                    borderRadius: 4,
                    padding: 12,
                    height: "100%",
                  }}
                >
                  <p>Select a PDF on the left to preview it here.</p>
                </div>
              )}
            </div>
          </div>

          {/* Chatbox */}
          <div
            style={{
              flex: 1,
              minHeight: 0,
              overflow: "hidden",
            }}
          >
            <NotebookChat notebookId={notebookId} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default NotebookPage;


