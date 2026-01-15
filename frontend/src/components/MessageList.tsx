import React from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot, FileText, Globe, Mic, File } from 'lucide-react';
import type { Message, Citation, SourceType } from '../types';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

function getSourceIcon(sourceType: SourceType) {
  switch (sourceType) {
    case 'audio':
      return <Mic className="w-3 h-3" />;
    case 'web':
      return <Globe className="w-3 h-3" />;
    case 'pdf':
      return <FileText className="w-3 h-3" />;
    default:
      return <File className="w-3 h-3" />;
  }
}

function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  return (
    <div className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg text-xs">
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary-100 text-primary-700 font-medium shrink-0">
        {index}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1 text-gray-600 mb-1">
          {getSourceIcon(citation.source_type)}
          <span className="font-medium truncate">{citation.title}</span>
        </div>
        {citation.page_range && (
          <span className="text-gray-500">Page {citation.page_range}</span>
        )}
        {citation.time_range && (
          <span className="text-gray-500">{citation.time_range}</span>
        )}
        <p className="text-gray-500 line-clamp-2 mt-1">{citation.text_snippet}</p>
      </div>
    </div>
  );
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

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 space-y-2 w-full">
            <p className="text-xs text-gray-500 font-medium">Sources:</p>
            <div className="grid gap-2">
              {message.citations.map((citation, idx) => (
                <CitationCard
                  key={citation.chunk_id}
                  citation={citation}
                  index={idx + 1}
                />
              ))}
            </div>
          </div>
        )}

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
