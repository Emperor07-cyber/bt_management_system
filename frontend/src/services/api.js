import axios from "axios";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1",
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("accessToken");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    if (
      status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/login/") &&
      !originalRequest.url?.includes("/auth/token/refresh/")
    ) {
      const refreshToken = localStorage.getItem("refreshToken");

      if (refreshToken) {
        originalRequest._retry = true;

        try {
          refreshPromise =
            refreshPromise ||
            axios.post(`${api.defaults.baseURL}/auth/token/refresh/`, {
              refresh: refreshToken,
            });

          const refreshResponse = await refreshPromise;
          const newAccessToken = refreshResponse.data.access;

          localStorage.setItem("accessToken", newAccessToken);
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem("accessToken");
          localStorage.removeItem("refreshToken");
          localStorage.removeItem("username");
          localStorage.removeItem("roles");
          window.dispatchEvent(new Event("auth:logout"));
          return Promise.reject(refreshError);
        } finally {
          refreshPromise = null;
        }
      }

      window.dispatchEvent(new Event("auth:logout"));
      error.userMessage = "Your session has expired. Please log in again.";
      return Promise.reject(error);
    }

    if (status === 403) {
      error.userMessage =
        "Access denied. You do not have permission to perform this action.";
    } else if (status >= 500) {
      error.userMessage =
        "The server encountered an error. Please try again later.";
    } else {
      error.userMessage =
        error.response?.data?.detail ||
        "Something went wrong. Please try again.";
    }

    return Promise.reject(error);
  }
);

export default api;
