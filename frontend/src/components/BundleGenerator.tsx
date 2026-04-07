"use client";

import { useState, useEffect } from "react";
import {
  getListings,
  generateBundles,
  type BundleOutput,
  type SavedListing,
} from "@/lib/api";

interface Props {
  refreshKey: number;
  onToast?: (type: "success" | "error" | "info", text: string) => void;
}

export default function BundleGenerator({ refreshKey, onToast }: Props) {
  const [savedListings, setSavedListings] = useState<SavedListing[]>([]);
  const [bundles, setBundles] = useState<BundleOutput[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [selectedBundle, setSelectedBundle] = useState<BundleOutput | null>(null);

  useEffect(() => {
    getListings(50)
      .then(setSavedListings)
      .catch(() => setSavedListings([]));
  }, [refreshKey]);

  const handleGenerate = async () => {
    if (savedListings.length < 3) {
      onToast?.("error", "Need at least 3 saved listings to create bundles. Save more listings first.");
      return;
    }

    setLoading(true);
    try {
      const input = savedListings.map((l) => ({
        title: l.title,
        tags: l.tags,
        description: l.description,
        price: l.price,
        image_filenames: [],
      }));
      const result = await generateBundles(input);
      setBundles(result);
      setExpanded(true);
      onToast?.("success", `${result.length} bundle(s) generated`);
    } catch (err) {
      onToast?.("error", err instanceof Error ? err.message : "Bundle generation failed");
    } finally {
      setLoading(false);
    }
  };

  if (savedListings.length < 3) return null;

  return (
    <div className="border rounded-lg">
      <div className="px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h2 className="font-semibold text-sm">Bundle Generator</h2>
          <p className="text-xs text-[var(--muted)]">
            Create 3-pack &amp; 5-pack bundles from {savedListings.length} saved listings
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-4 py-1.5 bg-black text-white text-sm rounded hover:bg-gray-800 disabled:opacity-40 transition-colors"
        >
          {loading ? "Generating..." : bundles.length > 0 ? "Regenerate" : "Generate Bundles"}
        </button>
      </div>

      {bundles.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full px-4 py-2 text-left text-xs text-[var(--muted)] hover:bg-[var(--surface)] transition-colors"
          >
            {expanded ? "Hide" : "Show"} {bundles.length} bundle(s)
          </button>

          {expanded && (
            <div className="divide-y">
              {bundles.map((bundle) => (
                <div
                  key={`${bundle.theme}-${bundle.pack_size}`}
                  className="px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold px-2 py-0.5 bg-black text-white rounded">
                          {bundle.pack_size}-Pack
                        </span>
                        <span className="text-sm font-medium truncate">{bundle.theme}</span>
                      </div>
                      <p className="text-xs text-[var(--muted)] truncate">{bundle.title}</p>
                      <p className="text-xs text-green-600 font-medium mt-1">
                        ${bundle.price.toFixed(2)}
                        <span className="text-[var(--muted)] font-normal ml-1">
                          ({bundle.pack_size === 3 ? "25%" : "30%"} off)
                        </span>
                      </p>
                    </div>
                    <button
                      onClick={() => setSelectedBundle(selectedBundle === bundle ? null : bundle)}
                      className="text-xs px-3 py-1 border rounded hover:bg-[var(--surface)] shrink-0 transition-colors"
                    >
                      {selectedBundle === bundle ? "Hide" : "Details"}
                    </button>
                  </div>

                  {selectedBundle === bundle && (
                    <div className="mt-3 p-3 bg-[var(--surface)] rounded text-xs space-y-2">
                      <div>
                        <span className="font-medium">Title:</span>
                        <p className="text-[var(--muted)]">{bundle.title}</p>
                      </div>
                      <div>
                        <span className="font-medium">Tags ({bundle.tags.length}):</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {bundle.tags.map((tag, j) => (
                            <span key={j} className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <span className="font-medium">Includes:</span>
                        <ul className="list-disc list-inside text-[var(--muted)] mt-1">
                          {bundle.source_indices.map((idx) => (
                            <li key={idx}>{savedListings[idx]?.title.split("|")[0].trim()}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <span className="font-medium">Description preview:</span>
                        <p className="text-[var(--muted)] mt-1 whitespace-pre-line line-clamp-6">
                          {bundle.description.slice(0, 300)}...
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
