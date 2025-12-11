import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

function NotebooksPage() {
  const [notebooks, setNotebooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem("authToken");
    axios
      .get("/api/files/notebooks/", {
        headers: {
          Authorization: `Token ${token}`,
        },
      })
      .then((res) => setNotebooks(res.data))
      .catch(() => setNotebooks([]))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    const token = localStorage.getItem("authToken");
    if (!token || !name.trim()) return;
    setCreating(true);
    try {
      const res = await axios.post(
        "/api/files/notebooks/",
        { name },
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );
      setNotebooks((prev) => [res.data, ...prev]);
      setName("");
      navigate(`/notebooks/${res.data.id}`);
    } catch (e) {
      console.error(e);
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return <div style={{ padding: 24 }}>Loading notebooks...</div>;
  }

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 16 }}>Your Notebooks</h2>

      <div style={{ marginBottom: 16, display: "flex", gap: 8 }}>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New notebook name"
          style={{ flex: 1 }}
        />
        <button onClick={handleCreate} disabled={creating || !name.trim()}>
          {creating ? "Creating..." : "Create & Open"}
        </button>
      </div>

      {notebooks.length === 0 ? (
        <p>No notebooks yet. Create one to start taking notes.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {notebooks.map((nb) => (
            <li
              key={nb.id}
              style={{
                padding: 12,
                borderBottom: "1px solid #eee",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div style={{ fontWeight: "bold" }}>{nb.name}</div>
                <div style={{ fontSize: 12, color: "#666" }}>
                  {new Date(nb.created_at).toLocaleString()}
                </div>
              </div>
              <button onClick={() => navigate(`/notebooks/${nb.id}`)}>
                Open
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default NotebooksPage;


