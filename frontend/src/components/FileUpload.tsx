import { useCallback, useState } from 'react';
import { Upload, X, FileText, Loader2 } from 'lucide-react';

interface FileUploadProps {
  onUploadFile: (file: File) => Promise<void>;
  onIngestText: (text: string, title?: string) => Promise<void>;
  isLoading: boolean;
}

type Tab = 'file' | 'text';

export function FileUpload({
  onUploadFile,
  onIngestText,
  isLoading,
}: FileUploadProps) {
  const [activeTab, setActiveTab] = useState<Tab>('file');
  const [isDragging, setIsDragging] = useState(false);
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      setError(null);
      setSuccess(null);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        try {
          await onUploadFile(files[0]);
          setSuccess(`Successfully uploaded ${files[0].name}`);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Upload failed');
        }
      }
    },
    [onUploadFile]
  );

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      setError(null);
      setSuccess(null);
      const files = e.target.files;
      if (files && files.length > 0) {
        try {
          await onUploadFile(files[0]);
          setSuccess(`Successfully uploaded ${files[0].name}`);
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Upload failed');
        }
      }
      // Reset input
      e.target.value = '';
    },
    [onUploadFile]
  );

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!text.trim()) return;

    try {
      await onIngestText(text.trim(), title.trim() || undefined);
      setSuccess('Successfully added note');
      setText('');
      setTitle('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add note');
    }
  };

  return (
    <div className="bg-white rounded-lg border shadow-sm">
      {/* Tabs */}
      <div className="flex border-b">
        {[
          { id: 'file' as Tab, label: 'Upload File', icon: Upload },
          { id: 'text' as Tab, label: 'Add Note', icon: FileText },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => {
              setActiveTab(id);
              setError(null);
              setSuccess(null);
            }}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === id
                ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      <div className="p-4">
        {/* Status messages */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center justify-between">
            {error}
            <button onClick={() => setError(null)}>
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm flex items-center justify-between">
            {success}
            <button onClick={() => setSuccess(null)}>
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* File upload */}
        {activeTab === 'file' && (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input
              type="file"
              id="file-upload"
              className="hidden"
              onChange={handleFileSelect}
              accept=".pdf,.md,.txt,.mp3,.m4a,.wav,.webm"
              disabled={isLoading}
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer flex flex-col items-center"
            >
              {isLoading ? (
                <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
              ) : (
                <Upload className="w-12 h-12 text-gray-400 mb-4" />
              )}
              <p className="text-gray-600 mb-2">
                {isLoading ? 'Processing...' : 'Drag & drop a file here, or click to browse'}
              </p>
              <p className="text-sm text-gray-400">
                Supports PDF, Markdown, Text, Audio (MP3, M4A, WAV)
              </p>
            </label>
          </div>
        )}

        {/* Text input */}
        {activeTab === 'text' && (
          <form onSubmit={handleTextSubmit} className="space-y-3">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title (optional)"
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={isLoading}
            />
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Enter your note or text content..."
              rows={4}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!text.trim() || isLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              Add Note
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
