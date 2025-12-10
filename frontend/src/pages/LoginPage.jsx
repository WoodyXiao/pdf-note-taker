import React, { useState } from "react";
import axios from "axios";

function LoginPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      if (isRegister) {
        const res = await axios.post("/api/auth/register/", {
          username,
          email,
          password,
        });
        localStorage.setItem("authToken", res.data.token);
        localStorage.setItem("currentUser", JSON.stringify(res.data.user));
      } else {
        const res = await axios.post("/api/auth/login/", {
          username,
          password,
        });
        localStorage.setItem("authToken", res.data.token);
        localStorage.setItem("currentUser", JSON.stringify(res.data.user));
      }
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong");
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
      <form onSubmit={handleSubmit} style={{ border: "1px solid #ddd", padding: 24, borderRadius: 8, width: 320 }}>
        <h2 style={{ marginBottom: 16 }}>{isRegister ? "Register" : "Login"}</h2>
        <div style={{ marginBottom: 8 }}>
          <label>Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ width: "100%" }}
          />
        </div>
        {isRegister && (
          <div style={{ marginBottom: 8 }}>
            <label>Email</label>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: "100%" }}
            />
          </div>
        )}
        <div style={{ marginBottom: 8 }}>
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%" }}
          />
        </div>
        {error && <p style={{ color: "red" }}>{error}</p>}
        <button type="submit" style={{ width: "100%", marginTop: 8 }}>
          {isRegister ? "Register" : "Login"}
        </button>
        <button
          type="button"
          onClick={() => setIsRegister((prev) => !prev)}
          style={{ width: "100%", marginTop: 8 }}
        >
          {isRegister ? "Already have an account? Login" : "No account? Register"}
        </button>
      </form>
    </div>
  );
}

export default LoginPage;


