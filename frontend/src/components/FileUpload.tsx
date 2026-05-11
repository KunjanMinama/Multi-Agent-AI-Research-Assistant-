import { useState } from 'react';
import { Upload, FileIcon } from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

interface FileUploadProps {
  onFileSelect: (file: File | null) => void;
  disabled?: boolean;
}

export function FileUpload({ onFileSelect, disabled }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (disabled) return;
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && validateFile(droppedFile)) {
      setFile(droppedFile);
      onFileSelect(droppedFile);
    }
  };

  const validateFile = (file: File) => {
    setError(null);
    const maxSize = 10 * 1024 * 1024; // 10MB

    // Basic MIME type check or file extension check fallback
    const isCsv = file.type === 'text/csv' || file.name.endsWith('.csv');
    const isXlsx = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || file.name.endsWith('.xlsx');

    if (!isCsv && !isXlsx) {
      setError('Invalid file type. Only CSV and XLSX allowed.');
      return false;
    }
    if (file.size > maxSize) {
      setError('File too large. Maximum 10MB.');
      return false;
    }
    return true;
  };

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
          dragActive ? "border-primary bg-accent" : "border-muted",
          disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:border-primary/50"
        )}
        onClick={() => {
          if (!disabled && !file) {
            document.getElementById('file-upload-input')?.click();
          }
        }}
      >
        {file ? (
          <div className="space-y-2">
            <FileIcon className="mx-auto h-12 w-12 text-primary" />
            <p className="font-medium text-foreground">{file.name}</p>
            <p className="text-sm text-muted-foreground">
              {(file.size / 1024).toFixed(2)} KB
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
                onFileSelect(null);
              }}
            >
              Remove
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="text-lg font-medium text-foreground">
              Drop CSV or Excel file here
            </p>
            <p className="text-sm text-muted-foreground">
              or click to browse
            </p>
            <input
              id="file-upload-input"
              type="file"
              accept=".csv,.xlsx"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file && validateFile(file)) {
                  setFile(file);
                  onFileSelect(file);
                }
              }}
              className="hidden"
              disabled={disabled}
            />
          </div>
        )}
      </div>
      {error && <p className="text-sm text-destructive font-medium">{error}</p>}
    </div>
  );
}
