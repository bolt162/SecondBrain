export type SourceType = 'audio' | 'pdf' | 'markdown' | 'web' | 'text' | 'image';
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface Document {
  id: string;
  user_id: string;
  source_type: SourceType;
  title: string;
  source_uri: string | null;
  original_filename: string | null;
  status: JobStatus;
  created_at: string;
  ingested_at: string | null;
  metadata: Record<string, unknown> | null;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  title: string;
  source_uri: string | null;
  source_type: SourceType;
  page_range: string | null;
  time_range: string | null;
  text_snippet: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  messages: Message[];
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  content: string;
  citations: Citation[];
}

export interface StreamEvent {
  type: 'start' | 'citations' | 'token' | 'done';
  conversation_id?: string;
  citations?: Citation[];
  token?: string;
  message_id?: string;
}
