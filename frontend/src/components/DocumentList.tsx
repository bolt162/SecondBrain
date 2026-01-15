import React from 'react';
import { FileText, FileAudio, Globe, File, Trash2, Loader2, RefreshCw } from 'lucide-react';
import type { Document, SourceType, JobStatus } from '../types';

interface DocumentListProps {
  documents: Document[];
  isLoading: boolean;
  onDelete: (id: string) => void;
  onRefresh: () => void;
}

function getSourceIcon(sourceType: SourceType) {
  switch (sourceType) {
    case 'audio':
      return <FileAudio className="w-5 h-5" />;
    case 'web':
      return <Globe className="w-5 h-5" />;
    case 'pdf':
      return <FileText className="w-5 h-5" />;
    case 'markdown':
      return <FileText className="w-5 h-5" />;
    default:
      return <File className="w-5 h-5" />;
  }
}

function getStatusBadge(status: JobStatus) {
  switch (status) {
    case 'completed':
      return (
        <span className="px-2 py-0.5 rounded-full text-xs bg-green-100 text-green-700">
          Ready
        </span>
      );
    case 'running':
      return (
        <span className="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700 flex items-center gap-1">
          <Loader2 className="w-3 h-3 animate-spin" />
          Processing
        </span>
      );
    case 'queued':
      return (
        <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-100 text-yellow-700">
          Queued
        </span>
      );
    case 'failed':
      return (
        <span className="px-2 py-0.5 rounded-full text-xs bg-red-100 text-red-700">
          Failed
        </span>
      );
    default:
      return null;
  }
}

function DocumentCard({
  document,
  onDelete,
}: {
  document: Document;
  onDelete: () => void;
}) {
  const [isDeleting, setIsDeleting] = React.useState(false);

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this document?')) {
      setIsDeleting(true);
      try {
        onDelete();
      } finally {
        setIsDeleting(false);
      }
    }
  };

  return (
    <div className="flex items-center gap-3 p-3 bg-white rounded-lg border hover:shadow-sm transition-shadow">
      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-gray-500">
        {getSourceIcon(document.source_type)}
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-gray-900 truncate">{document.title}</h4>
        <div className="flex items-center gap-2 mt-1">
          {getStatusBadge(document.status)}
          <span className="text-xs text-gray-400">
            {new Date(document.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>
      <button
        onClick={handleDelete}
        disabled={isDeleting}
        className="flex-shrink-0 p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
        title="Delete document"
      >
        {isDeleting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Trash2 className="w-4 h-4" />
        )}
      </button>
    </div>
  );
}

export function DocumentList({
  documents,
  isLoading,
  onDelete,
  onRefresh,
}: DocumentListProps) {
  return (
    <div className="bg-white rounded-lg border shadow-sm">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h3 className="font-semibold text-gray-900">Knowledge Base</h3>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="p-4">
        {isLoading && documents.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <File className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No documents yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Upload files or add URLs to build your knowledge base
            </p>
          </div>
        ) : (
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {documents.map((doc) => (
              <DocumentCard
                key={doc.id}
                document={doc}
                onDelete={() => onDelete(doc.id)}
              />
            ))}
          </div>
        )}
      </div>

      {documents.length > 0 && (
        <div className="px-4 py-2 border-t bg-gray-50 text-xs text-gray-500 text-center">
          {documents.length} document{documents.length !== 1 ? 's' : ''} in your knowledge base
        </div>
      )}
    </div>
  );
}
