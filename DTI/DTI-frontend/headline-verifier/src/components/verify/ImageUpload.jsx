import { useState, useRef } from 'react';
import { Upload, X, Image as ImageIcon } from 'lucide-react';
import { Button } from '../ui/Button';

export const ImageUpload = ({ onImageSelected, isLoading }) => {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const validExtensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tif', '.tiff'];

  const handleFileChange = (file) => {
    if (!file) return;

    // Validate file type
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validExtensions.includes(ext)) {
      alert(`Invalid file type. Please use: ${validExtensions.join(', ')}`);
      return;
    }

    // Validate file size (limit to 10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('File size must be less than 10MB');
      return;
    }

    setSelectedFile(file);
    setFileName(file.name);

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviewUrl(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleInputChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFileChange(file);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const file = e.dataTransfer.files?.[0];
    if (file) handleFileChange(file);
  };

  const handleSubmit = () => {
    if (selectedFile && !isLoading) {
      onImageSelected(selectedFile);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setFileName('');
    setPreviewUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full flex flex-col gap-3">
      <div className="flex gap-3">
        {/* Image Upload Area */}
        <div
          className={`flex-1 relative flex flex-col items-center justify-center border-2 border-dashed rounded-xl transition-colors duration-200 p-6 cursor-pointer ${
            dragActive
              ? 'border-accent-blue bg-accent-blue/10'
              : 'border-border-default bg-background-secondary/50 hover:border-accent-blue/50'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !selectedFile && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleInputChange}
            className="hidden"
            disabled={isLoading}
          />

          {!previewUrl ? (
            <div className="flex flex-col items-center gap-2 text-center">
              <Upload className="h-8 w-8 text-text-muted" />
              <div>
                <p className="text-text-primary font-medium">Upload an image</p>
                <p className="text-text-secondary text-sm">
                  or drag and drop
                </p>
              </div>
              <p className="text-text-muted text-xs">
                JPG, PNG, GIF, WebP, BMP up to 10MB
              </p>
            </div>
          ) : (
            <div className="text-center">
              <ImageIcon className="h-8 w-8 text-accent-blue mx-auto mb-2" />
              <p className="text-text-primary font-medium">{fileName}</p>
              <p className="text-text-secondary text-sm">Click to change</p>
            </div>
          )}
        </div>

        {/* Preview */}
        {previewUrl && (
          <div className="relative w-24 h-24 rounded-lg overflow-hidden border border-border-default">
            <img
              src={previewUrl}
              alt="Preview"
              className="w-full h-full object-cover"
            />
            <button
              onClick={handleClear}
              disabled={isLoading}
              className="absolute top-1 right-1 p-1 bg-red-500/80 hover:bg-red-600 rounded transition-colors disabled:opacity-50"
              title="Remove image"
            >
              <X className="h-3 w-3 text-white" />
            </button>
          </div>
        )}
      </div>

      {selectedFile && (
        <Button
          onClick={handleSubmit}
          disabled={!selectedFile || isLoading}
          isLoading={isLoading}
          className="w-full"
        >
          {isLoading ? 'Analyzing Image...' : 'Verify Image'}
        </Button>
      )}
    </div>
  );
};
