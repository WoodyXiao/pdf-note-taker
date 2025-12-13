import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import NotebooksPage from "./pages/NotebooksPage";
import NotebookPage from "./pages/NotebookPage";
import PdfLibraryPage from "./pages/PdfLibraryPage";
import TopNav from "./components/TopNav";

function App() {
  const token = localStorage.getItem("authToken");

  const requireAuth = (element) =>
    token ? element : <Navigate to="/login" replace />;

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <TopNav />
      <div style={{ flex: 1, minHeight: 0 }}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          {/* Notebook-based experience */}
          <Route path="/notebooks" element={requireAuth(<NotebooksPage />)} />
          <Route
            path="/notebooks/:notebookId"
            element={requireAuth(<NotebookPage />)}
          />

          {/* Global PDF library */}
          <Route
            path="/pdfs"
            element={requireAuth(<PdfLibraryPage />)}
          />

          {/* Default route */}
          <Route
            path="*"
            element={<Navigate to={token ? "/notebooks" : "/login"} replace />}
          />
        </Routes>
      </div>
    </div>
  );
}

export default App;


