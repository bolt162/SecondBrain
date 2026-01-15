import { useState, useCallback } from 'react';
import { api } from '../services/api';
import type { Message, Citation, StreamEvent } from '../types';

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  conversationId: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  loadConversation: (id: string) => Promise<void>;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    setIsLoading(true);
    setError(null);

    // Add user message immediately
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Add placeholder for assistant message
    const assistantPlaceholder: Message = {
      id: `temp-assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, assistantPlaceholder]);

    try {
      let currentContent = '';
      let currentCitations: Citation[] = [];
      let finalMessageId: string | null = null;

      await api.chatStream(
        content,
        conversationId || undefined,
        (event: StreamEvent) => {
          switch (event.type) {
            case 'start':
              if (event.conversation_id) {
                setConversationId(event.conversation_id);
              }
              break;
            case 'citations':
              if (event.citations) {
                currentCitations = event.citations;
              }
              break;
            case 'token':
              if (event.token) {
                currentContent += event.token;
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage.role === 'assistant') {
                    lastMessage.content = currentContent;
                    lastMessage.citations = currentCitations;
                  }
                  return newMessages;
                });
              }
              break;
            case 'done':
              finalMessageId = event.message_id || null;
              break;
          }
        }
      );

      // Update final message with proper ID
      if (finalMessageId) {
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage.role === 'assistant') {
            lastMessage.id = finalMessageId!;
          }
          return newMessages;
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      // Remove the placeholder assistant message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  }, [conversationId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  const loadConversation = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const conversation = await api.getConversation(id);
      setConversationId(conversation.id);
      setMessages(conversation.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    clearMessages,
    loadConversation,
  };
}
