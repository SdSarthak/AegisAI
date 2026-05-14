import axios from "axios";

/**
 * Central API client for AegisAI frontend
 * All backend calls must go through this instance
 */

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json"
  }
});

export default api;