import React, { useState } from "react";
import axios from "axios";
import { toast } from "sonner";

function UploadPdfDialog({ onUploaded }) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const token = localStorage.getItem("authToken");
      const formData = new FormData();
      formData.append("file", file);
      formData.append("fileName", fileName);
      await axios.post("/api/files/upload/", formData, {
        headers: {
          Authorization: `Token ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });
      toast.success("PDF uploaded and ingested");
      setOpen(false);
      setFile(null);
      setFileName("");
      if (onUploaded) {
        onUploaded();
      }
    } catch (e) {
      console.error(e);
      toast.error("Upload failed");
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button style={{ width: "100%" }} onClick={() => setOpen(true)}>
        + Upload PDF
      </button>
    );
  }

  return (
    <div
      style={{
        border: "1px solid #ddd",
        padding: 12,
        borderRadius: 8,
        marginTop: 8,
      }}
    >
      <div>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => {
            const f = e.target.files?.[0] || null;
            setFile(f);
            if (f && !fileName) {
              setFileName(f.name);
            }
          }}
        />
      </div>
      <div style={{ marginTop: 8 }}>
        <label>File Name</label>
        <input
          value={fileName}
          onChange={(e) => setFileName(e.target.value)}
          style={{ width: "100%" }}
          placeholder="File Name"
        />
      </div>
      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <button onClick={() => setOpen(false)}>Close</button>
        <button onClick={handleUpload} disabled={loading}>
          {loading ? "Uploading..." : "Upload"}
        </button>
      </div>
    </div>
  );
}

export default UploadPdfDialog;



