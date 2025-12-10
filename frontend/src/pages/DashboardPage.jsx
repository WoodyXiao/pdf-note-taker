import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

function DashboardPage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("authToken");
    axios
      .get("/api/files/", {
        headers: {
          Authorization: `Token ${token}`,
        },
      })
      .then((res) => setFiles(res.data))
      .catch(() => setFiles([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div>Loading files...</div>;
  }

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>Your PDF Files</h2>
      {files.length === 0 ? (
        <p>No files uploaded yet. Use the \"Upload PDF\" button on the left.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 8 }}>
                Name
              </th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 8 }}>
                Created At
              </th>
              <th style={{ borderBottom: "1px solid #eee", padding: 8 }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.file_id}>
                <td style={{ padding: 8, borderBottom: "1px solid #f5f5f5" }}>
                  {f.file_name}
                </td>
                <td style={{ padding: 8, borderBottom: "1px solid #f5f5f5", fontSize: 12 }}>
                  {new Date(f.created_at).toLocaleString()}
                </td>
                <td style={{ padding: 8, borderBottom: "1px solid #f5f5f5" }}>
                  <button onClick={() => navigate(`/workspace/${f.file_id}`)}>
                    Open
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default DashboardPage;



