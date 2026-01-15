import { useState, useCallback, useEffect } from 'react';
import { api } from '../services/api';
import type { Document } from '../types';

interface UseDocumentsReturn {
  documents: Document[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  uploadFile: (file: File) => Promise<void>;
  ingestUrl: (url: string) => Promise<void>;
  ingestText: (text: string, title?: string) => Promise<void>;
  deleteDocument: (id: string) => Promise<void>;
}

function getSourceType(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop();
  switch (ext) {
    case 'mp3':
    case 'm4a':
    case 'wav':
    case 'webm':
    case 'ogg':
      return 'audio';
    case 'pdf':
      return 'pdf';
    case 'md':
    case 'markdown':
      return 'markdown';
    default:
      return 'text';
  }
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.listDocuments();
      setDocuments(response.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const uploadFile = useCallback(async (file: File) => {
    setIsLoading(true);
    setError(null);
    try {
      const sourceType = getSourceType(file.name);
      await api.ingestFile(file, sourceType);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refresh]);

  const ingestUrl = useCallback(async (url: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.ingestUrl(url);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ingest URL');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refresh]);

  const ingestText = useCallback(async (text: string, title?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.ingestText(text, title);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ingest text');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refresh]);

  const deleteDocument = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await api.deleteDocument(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [refresh]);

  return {
    documents,
    isLoading,
    error,
    refresh,
    uploadFile,
    ingestUrl,
    ingestText,
    deleteDocument,
  };
}
