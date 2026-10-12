import { useState } from "react";
import { LockKeyhole, User, Eye, EyeOff } from "lucide-react";
import "./Login.css";
import api from "../services/api";

function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response = await api.post("/auth/login/", {
        username,
        password,
      });

      localStorage.setItem("accessToken", response.data.access);
      localStorage.setItem("refreshToken", response.data.refresh);
     localStorage.setItem("username", username);

      const meResponse = await api.get("/auth/me/");

      localStorage.setItem(
        "roles",
        JSON.stringify(meResponse.data.roles || [])
      );

onLogin(meResponse.data);
    } catch (err) {
      console.error("Login error:", err);

      if (err.response?.data) {
        setError("Invalid username or password.");
      } else {
        setError("Unable to connect to the server.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">

        <div className="login-brand">
          <div className="login-logo">BT</div>
          <h1>BT Management</h1>
          <p>Business Management System</p>
        </div>

        <div className="login-card">

          <div className="login-heading">
            <h2>Welcome back</h2>
            <p>Sign in to access your management dashboard.</p>
          </div>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>

            <div className="form-group">
              <label>Username</label>

              <div className="input-wrapper">
                <User size={18} />

                <input
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Password</label>

              <div className="input-wrapper">
                <LockKeyhole size={18} />

                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>

          </form>
        </div>

        <p className="login-footer">
          BT Management System
        </p>

      </div>
    </div>
  );
}

export default Login;