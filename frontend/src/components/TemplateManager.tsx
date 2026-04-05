"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getTemplates,
  getTemplateUploadUrl,
  uploadToS3,
  saveTemplate,
  deleteTemplate,
  type TemplateItem,
} from "@/lib/api";

interface Props {
  onToast?: (type: "success" | "error", text: string) => void;
}

export default function TemplateManager({ onToast }: Props) {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newName, setNewName] = useState("");
  const [orientation, setOrientation] = useState<"vertical" | "horizontal">("vertical");

  const refresh = useCallback(() => {
    setLoading(true);
    getTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !newName.trim()) return;

    setUploading(true);
    try {
      const { upload_url, template } = await getTemplateUploadUrl();
      await uploadToS3(upload_url, file);
      await saveTemplate(newName.trim(), template.s3_key!, orientation);
      setNewName("");
      refresh();
      onToast?.("success", "Template uploaded");
    } catch {
      onToast?.("error", "Template upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTemplate(id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
      onToast?.("success", "Template deleted");
    } catch {
      onToast?.("error", "Failed to delete template");
    }
  };

  const customCount = templates.filter((t) => t.is_custom).length;

  return (
    <div className="border rounded-lg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
      >
        <span className="font-semibold text-sm">
          Frame Templates ({templates.length})
          {customCount > 0 && (
            <span className="text-gray-400 font-normal"> ({customCount} custom)</span>
          )}
        </span>
        <span className="text-gray-400 text-xs">{expanded ? "Hide" : "Show"}</span>
      </button>

      {expanded && (
        <div className="border-t px-4 py-3">
          {/* Template list */}
          {!loading && templates.length > 0 && (
            <div className="divide-y mb-4">
              {templates.map((t) => (
                <div key={t.id} className="py-2 flex items-center justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{t.name}</p>
                    <p className="text-xs text-gray-400">
                      {t.orientation} {t.is_custom ? "(custom)" : "(bundled)"}
                    </p>
                  </div>
                  {t.is_custom && (
                    <button
                      onClick={() => handleDelete(t.id)}
                      className="text-xs text-gray-400 hover:text-red-500 shrink-0"
                    >
                      Delete
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Upload new template */}
          <div className="pt-2 border-t">
            <p className="text-sm font-medium mb-2">Add Custom Template</p>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Template name"
                className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-black"
              />
              <select
                value={orientation}
                onChange={(e) => setOrientation(e.target.value as "vertical" | "horizontal")}
                className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-black"
              >
                <option value="vertical">Vertical</option>
                <option value="horizontal">Horizontal</option>
              </select>
            </div>
            <div className="mt-2">
              <label
                className={`inline-block px-4 py-2 border rounded text-sm cursor-pointer transition-colors ${
                  !newName.trim() || uploading
                    ? "opacity-40 cursor-not-allowed"
                    : "hover:bg-gray-50"
                }`}
              >
                {uploading ? "Uploading..." : "Choose Image"}
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleUpload}
                  disabled={!newName.trim() || uploading}
                  className="hidden"
                />
              </label>
              <p className="text-xs text-gray-400 mt-1">
                Upload a photo of a picture frame with a white/blank interior.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
