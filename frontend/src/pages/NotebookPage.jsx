import React, { useEffect, useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import TextEditor from "../components/TextEditor";
import NotebookChat from "../components/NotebookChat";

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

  const handleToggleFile = async (fileId) => {
    const newSelected = selectedFileIds.includes(fileId)
      ? selectedFileIds.filter((id) => id !== fileId)
      : [...selectedFileIds, fileId];

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

  const currentPreviewFile = files.find((f) => f.file_id === previewFileId) || null;

  if (loading) {
    return <div style={{ padding: 24 }}>Loading notebook...</div>;
  }

  if (!notebook) {
    return <div style={{ padding: 24 }}>Notebook not found.</div>;
  }

  return (
    <div>
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
        }}
      >
        {/* Left: PDF list with checkboxes */}
        <div
          style={{
            border: "1px solid #eee",
            borderRadius: 4,
            padding: 12,
            overflowY: "auto",
            maxHeight: "88vh",
          }}
        >
          <h3 style={{ marginBottom: 8, fontSize: 14 }}>PDFs in this notebook</h3>
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
                        onChange={(e) => {
                          e.stopPropagation();
                          handleToggleFile(f.file_id);
                        }}
                      />
                      <span style={{ fontSize: 13 }}>{f.file_name}</span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Center: Notebook editor (TipTap) */}
        <div>
          <TextEditor notebookId={notebookId} />
        </div>

        {/* Right: PDF preview */}
        <div style={{ display: "flex", flexDirection: "column", height: "90vh" }}>
          <div style={{ flex: 1 }}>
            {currentPreviewFile ? (
              <iframe
                src={currentPreviewFile.file_url + "#toolbar=0"}
                height="100%"
                width="100%"
                style={{ border: "none" }}
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
          {/* Chatbox directly under PDF preview */}
          <NotebookChat notebookId={notebookId} />
        </div>
      </div>
    </div>
  );
}

export default NotebookPage;


