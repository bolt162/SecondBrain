import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { ChatInterface } from './components/ChatInterface';
import { Sidebar } from './components/Sidebar';
import { useChat } from './hooks/useChat';
import { useDocuments } from './hooks/useDocuments';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const chat = useChat();
  const documents = useDocuments();

  return (
    <div className="h-screen flex bg-white">
      {/* Mobile sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-md lg:hidden"
      >
        {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Sidebar */}
      <div
        className={`fixed lg:static inset-y-0 left-0 z-40 transform transition-transform duration-300 lg:transform-none ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <Sidebar
          documents={documents.documents}
          isLoading={documents.isLoading}
          onUploadFile={documents.uploadFile}
          onIngestText={documents.ingestText}
          onDeleteDocument={documents.deleteDocument}
          onRefresh={documents.refresh}
        />
      </div>

      {/* Backdrop for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-14 border-b bg-white flex items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-4">
            <div className="lg:hidden w-10" /> {/* Spacer for mobile toggle */}
            <h2 className="font-semibold text-gray-900">Chat</h2>
          </div>
          {chat.conversationId && (
            <button
              onClick={chat.clearMessages}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              New Conversation
            </button>
          )}
        </header>

        {/* Chat area */}
        <main className="flex-1 overflow-hidden">
          <ChatInterface
            messages={chat.messages}
            isLoading={chat.isLoading}
            error={chat.error}
            onSendMessage={chat.sendMessage}
          />
        </main>
      </div>
    </div>
  );
}

export default App;
