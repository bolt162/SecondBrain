import ReactMarkdown from 'react-markdown';
import { User, Bot } from 'lucide-react';
import type { Message } from '../types';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

function MessageBubble({
  message,
  isStreaming,
}: {
  message: Message;
  isStreaming: boolean;
}) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-primary-600' : 'bg-gray-200'
        }`}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-gray-600" />
        )}
      </div>

      {/* Content */}
      <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-2 ${
            isUser
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-800'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className={`prose prose-sm max-w-none ${isStreaming ? 'cursor-blink' : ''}`}>
              <ReactMarkdown>{message.content || 'Thinking...'}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="text-xs text-gray-400 mt-1">
          {new Date(message.created_at).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      </div>
    </div>
  );
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  return (
    <div className="space-y-6">
      {messages.map((message, index) => (
        <MessageBubble
          key={message.id}
          message={message}
          isStreaming={
            isLoading &&
            message.role === 'assistant' &&
            index === messages.length - 1
          }
        />
      ))}
    </div>
  );
}
