import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 text-center px-4">
      <h1 className="text-7xl font-extrabold text-blue-600">404</h1>
      <h2 className="mt-4 text-3xl font-bold text-gray-900">Page Not Found</h2>
      <p className="mt-2 text-lg text-gray-600">
        Oops! The page you are looking for doesn't exist or has been moved.
      </p>
      <Link
        to="/"
        className="mt-8 px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 hover:shadow-lg transition duration-300"
      >
        Go to Dashboard
      </Link>
    </div>
  );
}