import { FileUpload } from './FileUpload';
import { DocumentList } from './DocumentList';
import type { Document } from '../types';

interface SidebarProps {
  documents: Document[];
  isLoading: boolean;
  onUploadFile: (file: File) => Promise<void>;
  onIngestText: (text: string, title?: string) => Promise<void>;
  onDeleteDocument: (id: string) => Promise<void>;
  onRefresh: () => Promise<void>;
}

export function Sidebar({
  documents,
  isLoading,
  onUploadFile,
  onIngestText,
  onDeleteDocument,
  onRefresh,
}: SidebarProps) {
  return (
    <div className="w-80 h-full bg-gray-50 border-r flex flex-col overflow-hidden">
      <div className="p-4 border-b bg-white">
        <h1 className="text-xl font-bold text-gray-900">
          SecondBrain
        </h1>
        <p className="text-sm text-gray-500 mt-1">Your AI Knowledge Companion</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <FileUpload
          onUploadFile={onUploadFile}
          onIngestText={onIngestText}
          isLoading={isLoading}
        />

        <DocumentList
          documents={documents}
          isLoading={isLoading}
          onDelete={onDeleteDocument}
          onRefresh={onRefresh}
        />
      </div>
    </div>
  );
}
