import React from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";

function TopNav() {
  const navigate = useNavigate();
  const token = localStorage.getItem("authToken");
  const user = JSON.parse(localStorage.getItem("currentUser") || "{}");

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("currentUser");
    toast.success("Logged out");
    navigate("/login");
  };

  return (
    <header
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "12px 24px",
        borderBottom: "1px solid #eee",
        position: "sticky",
        top: 0,
        zIndex: 10,
        background: "#fff",
      }}
    >
      <div
        style={{ fontWeight: "bold", fontSize: 18, cursor: "pointer" }}
        onClick={() => navigate(token ? "/notebooks" : "/login")}
      >
        PDF Note Taker
      </div>

      <nav style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {token && (
          <>
            <Link
              to="/notebooks"
              style={{ textDecoration: "none", color: "#333" }}
            >
              Notebooks
            </Link>
            <Link
              to="/pdfs"
              style={{ textDecoration: "none", color: "#333" }}
            >
              PDFs
            </Link>
            <Link
              to="/activity"
              style={{ textDecoration: "none", color: "#333" }}
            >
              Activity
            </Link>
          </>
        )}
      </nav>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {token ? (
          <>
            <span style={{ fontSize: 14, color: "#555" }}>
              {user?.username || user?.email || "User"}
            </span>
            <button onClick={handleLogout}>Logout</button>
          </>
        ) : (
          <button onClick={() => navigate("/login")}>Login / Register</button>
        )}
      </div>
    </header>
  );
}

export default TopNav;


