import { useState } from "react";

const RagChat = () => {
  const [question, setQuestion] = useState("");

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">RAG Chat</h1>

      <div className="bg-white rounded-xl shadow-md p-6 space-y-4">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your compliance documents..."
          className="w-full border rounded-lg p-4 min-h-[120px] focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <button
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition"
        >
          Ask
        </button>
      </div>

      <div className="mt-8 bg-white rounded-xl shadow-md p-6">
        <h2 className="text-xl font-semibold mb-4">Answer</h2>

        <div className="border rounded-lg p-4 text-gray-500 min-h-[120px]">
          AI-generated answer will appear here.
        </div>

        <div className="mt-6">
          <h3 className="font-semibold mb-2">Source Citations</h3>

          <div className="border rounded-lg p-4 text-gray-500">
            Relevant document sources will appear here.
          </div>
        </div>
      </div>
    </div>
  );
};

export default RagChat;