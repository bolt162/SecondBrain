import type { Document, ChatResponse, Conversation, StreamEvent } from '../types';

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/v1`
  : '/v1';

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  // Document endpoints
  async listDocuments(): Promise<{ documents: Document[]; total: number }> {
    return this.request('/documents');
  }

  async getDocument(id: string): Promise<Document> {
    return this.request(`/documents/${id}`);
  }

  async deleteDocument(id: string): Promise<void> {
    await this.request(`/documents/${id}`, { method: 'DELETE' });
  }

  // Ingestion endpoints
  async ingestText(text: string, title?: string): Promise<Document> {
    return this.request('/ingest/text', {
      method: 'POST',
      body: JSON.stringify({ text, title }),
    });
  }

  async ingestUrl(url: string): Promise<Document> {
    return this.request('/ingest/url', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  async ingestFile(file: File, sourceType: string): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_type', sourceType);

    const response = await fetch(`${API_BASE}/ingest/file`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  // Chat endpoints
  async chat(
    message: string,
    conversationId?: string
  ): Promise<ChatResponse> {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      }),
    });
  }

  async chatStream(
    message: string,
    conversationId: string | undefined,
    onEvent: (event: StreamEvent) => void
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Request failed');
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event: StreamEvent = JSON.parse(data);
            onEvent(event);
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }
  }

  async listConversations(): Promise<Conversation[]> {
    return this.request('/chat/conversations');
  }

  async getConversation(id: string): Promise<Conversation> {
    return this.request(`/chat/conversations/${id}`);
  }

  async deleteConversation(id: string): Promise<void> {
    await this.request(`/chat/conversations/${id}`, { method: 'DELETE' });
  }
}

export const api = new ApiService();
