import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import DashboardLayout from "./pages/DashboardLayout";
import WorkspacePage from "./pages/WorkspacePage";

function App() {
  const token = localStorage.getItem("authToken");

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard/*"
        element={token ? <DashboardLayout /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/workspace/:fileId"
        element={token ? <WorkspacePage /> : <Navigate to="/login" replace />}
      />
      <Route path="*" element={<Navigate to={token ? "/dashboard" : "/login"} replace />} />
    </Routes>
  );
}

export default App;


