import { useState } from "react";

const RAGChat = () => {
  const [input, setInput] = useState("");

  const [messages, setMessages] = useState([
    {
      role: "ai",
      text: "Hello! How can I help you with your compliance documents today?",
    },
  ]);

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage = {
      role: "user",
      text: input,
    };

    const aiMessage = {
      role: "ai",
      text: "This is a mock AI response for the UI demo.",
    };

    setMessages((prev) => [...prev, userMessage, aiMessage]);

    setInput("");
  };

  return (
    <div className="flex h-[calc(100vh-64px)]">

      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col bg-gray-50">

        {/* Header */}
        <div className="border-b bg-white px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-800">
            RAG Chat Assistant
          </h1>

          <p className="text-sm text-gray-500">
            Ask questions about your compliance documents
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">

          {messages.map((message, index) => (
            <div
              key={index}
              className={`max-w-xl rounded-2xl p-4 shadow-sm ${
                message.role === "user"
                  ? "ml-auto bg-blue-600 text-white"
                  : "bg-white"
              }`}
            >
              {message.text}
            </div>
          ))}

        </div>

        {/* Input */}
        <div className="border-t bg-white p-4">
          <div className="flex items-center gap-3">

           <input
  type="text"
  placeholder="Ask something..."
  value={input}
  onChange={(e) => setInput(e.target.value)}
  onKeyDown={(e) => {
    if (e.key === "Enter") {
      handleSend();
    }
  }}
  className="flex-1 rounded-xl border px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
/>

            <button
              onClick={handleSend}
              className="rounded-xl bg-blue-600 px-5 py-3 text-white hover:bg-blue-700"
            >
              Send
            </button>

          </div>
        </div>

      </div>
    </div>
  );
};

export default RAGChat;