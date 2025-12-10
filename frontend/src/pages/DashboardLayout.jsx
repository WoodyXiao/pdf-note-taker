import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import DashboardPage from "./DashboardPage";
import UploadPdfDialog from "../shared/UploadPdfDialog";

function DashboardLayout() {
  const user = JSON.parse(localStorage.getItem("currentUser") || "{}");

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("currentUser");
    window.location.href = "/login";
  };

  return (
    <div>
      <div style={{ position: "fixed", width: 260, height: "100vh", borderRight: "1px solid #eee", padding: 16 }}>
        <h2>PDF Note Taker</h2>
        <div style={{ marginTop: 24 }}>
          <UploadPdfDialog />
          <div style={{ marginTop: 16 }}>
            <div style={{ padding: 8, cursor: "pointer" }}>
              <Link to="/dashboard">Workspace</Link>
            </div>
            <div style={{ padding: 8, cursor: "pointer", color: "#999" }}>Upgrade</div>
          </div>
        </div>
      </div>
      <div style={{ marginLeft: 260 }}>
        <div style={{ display: "flex", justifyContent: "flex-end", padding: 16, borderBottom: "1px solid #eee" }}>
          <span style={{ marginRight: 8 }}>{user?.username}</span>
          <button onClick={handleLogout}>Logout</button>
        </div>
        <div style={{ padding: 24 }}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}

export default DashboardLayout;


