"use client";

import { useState, useEffect } from "react";
import { getAnalytics, type AnalyticsResponse, type ListingStats } from "@/lib/api";

interface Props {
  connected: boolean;
}

export default function AnalyticsDashboard({ connected }: Props) {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const fetchData = () => {
    if (!connected) return;
    setLoading(true);
    setError(null);
    getAnalytics()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (connected) fetchData();
  }, [connected]);

  if (!connected) return null;

  return (
    <div className="border rounded-lg">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-[var(--surface)] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="font-semibold text-sm">Shop Analytics</span>
          {data && (
            <div className="flex gap-3 text-xs text-[var(--muted)]">
              <span>{data.total_views.toLocaleString()} views</span>
              <span>{data.total_favorites.toLocaleString()} favorites</span>
            </div>
          )}
        </div>
        <span className="text-xs text-[var(--muted)]">{expanded ? "Hide" : "Show"}</span>
      </button>

      {expanded && (
        <div className="border-t px-4 py-3">
          {loading && <p className="text-sm text-[var(--muted)]">Loading stats...</p>}
          {error && <p className="text-sm text-red-500">{error}</p>}

          {data && (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 bg-[var(--surface)] rounded text-center">
                  <p className="text-2xl font-bold">{data.total_views.toLocaleString()}</p>
                  <p className="text-xs text-[var(--muted)]">Total Views</p>
                </div>
                <div className="p-3 bg-[var(--surface)] rounded text-center">
                  <p className="text-2xl font-bold">{data.total_favorites.toLocaleString()}</p>
                  <p className="text-xs text-[var(--muted)]">Total Favorites</p>
                </div>
              </div>

              {/* Listing table */}
              {data.listings.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs text-[var(--muted)]">
                        <th className="pb-2 pr-4">Listing</th>
                        <th className="pb-2 pr-4 text-right">Views</th>
                        <th className="pb-2 text-right">Favs</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.listings.slice(0, 20).map((item) => (
                        <tr key={item.listing_id} className="text-xs">
                          <td className="py-2 pr-4 max-w-[200px] truncate">
                            {item.url ? (
                              <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hover:underline"
                              >
                                {item.title}
                              </a>
                            ) : (
                              item.title
                            )}
                          </td>
                          <td className="py-2 pr-4 text-right tabular-nums">
                            {item.views.toLocaleString()}
                          </td>
                          <td className="py-2 text-right tabular-nums">
                            {item.favorites.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <button
                onClick={fetchData}
                disabled={loading}
                className="mt-3 text-xs text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
              >
                Refresh
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
