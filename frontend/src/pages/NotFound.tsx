import { useNavigate } from "react-router-dom";

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
      }}
    >
      <h1>404 - Page Not Found</h1>
      <p>The page you are looking for does not exist.</p>

      <button onClick={() => navigate("/")}>
        Go to Dashboard
      </button>
    </div>
  );
};

export default NotFound;