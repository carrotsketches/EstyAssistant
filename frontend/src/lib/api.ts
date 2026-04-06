const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UploadUrlResponse {
  upload_url: string;
  s3_key: string;
}

export interface ProcessedImage {
  size: string;
  download_url: string;
}

export interface ProcessResponse {
  preview_url: string;
  outputs: ProcessedImage[];
}

export interface ListingMetadata {
  title: string;
  tags: string[];
  description: string;
}

export interface MockupImage {
  template_name: string;
  url: string;
}

export interface MockupResponse {
  mockups: MockupImage[];
}

export async function getUploadUrl(
  contentType: string = "image/jpeg"
): Promise<UploadUrlResponse> {
  const res = await fetch(
    `${API_BASE}/upload-url?content_type=${encodeURIComponent(contentType)}`
  );
  if (!res.ok) throw new Error(`Failed to get upload URL: ${res.statusText}`);
  return res.json();
}

export async function uploadToS3(
  presignedUrl: string,
  file: File
): Promise<void> {
  const res = await fetch(presignedUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type },
  });
  if (!res.ok) throw new Error(`S3 upload failed: ${res.statusText}`);
}

export async function processImage(
  s3Key: string,
  sizes: string[] = ["8x10"],
  skipSteps: string[] = []
): Promise<ProcessResponse> {
  const res = await fetch(`${API_BASE}/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      s3_key: s3Key,
      sizes,
      skip_steps: skipSteps,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Processing failed: ${detail}`);
  }
  return res.json();
}

export async function generateListing(
  s3Key: string
): Promise<ListingMetadata> {
  const res = await fetch(`${API_BASE}/listing/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ s3_key: s3Key }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Listing generation failed: ${detail}`);
  }
  return res.json();
}

export async function generateMockups(
  s3Key: string,
  templateNames?: string[]
): Promise<MockupResponse> {
  const res = await fetch(`${API_BASE}/mockups/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      s3_key: s3Key,
      template_names: templateNames,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Mockup generation failed: ${detail}`);
  }
  return res.json();
}

// ── Etsy Auth ──

export interface AuthStatus {
  connected: boolean;
  shop_id: string | null;
}

export async function getEtsyAuthStatus(): Promise<AuthStatus> {
  const res = await fetch(`${API_BASE}/auth/etsy/status`);
  if (!res.ok) throw new Error("Failed to check Etsy status");
  return res.json();
}

export async function startEtsyAuth(): Promise<string> {
  const callbackUrl = `${window.location.origin}/auth/etsy/callback`;
  const res = await fetch(
    `${API_BASE}/auth/etsy/start?redirect_uri=${encodeURIComponent(callbackUrl)}`
  );
  if (!res.ok) throw new Error("Failed to start Etsy auth");
  const data = await res.json();
  return data.auth_url;
}

export async function completeEtsyAuth(
  code: string,
  state: string
): Promise<{ success: boolean; shop_id: string | null }> {
  const res = await fetch(
    `${API_BASE}/auth/etsy/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Etsy auth failed: ${detail}`);
  }
  return res.json();
}

export async function disconnectEtsy(): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/etsy/disconnect`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to disconnect Etsy");
}

// ── Publish ──

export interface PublishRequest {
  s3_key: string;
  sizes: string[];
  title: string;
  description: string;
  tags: string[];
  price: number;
}

export interface JobStatus {
  status: string;
  result?: {
    listing_id: string;
    listing_url: string | null;
    title: string;
  };
  error?: string;
}

export async function publishListing(
  req: PublishRequest
): Promise<string> {
  const res = await fetch(`${API_BASE}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Publish failed: ${detail}`);
  }
  const data = await res.json();
  return data.job_id;
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to get job status");
  return res.json();
}

// ── Listing History ──

export interface SavedListing {
  id: string;
  title: string;
  tags: string[];
  description: string;
  price: number | null;
  s3_key: string | null;
  sizes: string[];
  etsy_listing_id: string | null;
  etsy_listing_url: string | null;
  preview_url: string | null;
  created_at: number;
}

export async function getListings(limit: number = 50): Promise<SavedListing[]> {
  const res = await fetch(`${API_BASE}/listings?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch listings");
  const data = await res.json();
  return data.listings;
}

export async function saveListing(listing: {
  title: string;
  tags: string[];
  description: string;
  price?: number;
  s3_key?: string;
  sizes?: string[];
  etsy_listing_id?: string;
  etsy_listing_url?: string;
  preview_url?: string;
}): Promise<SavedListing> {
  const res = await fetch(`${API_BASE}/listings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(listing),
  });
  if (!res.ok) throw new Error("Failed to save listing");
  return res.json();
}

export async function deleteListing(listingId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/listings/${listingId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete listing");
}

// ── Templates ──

export interface TemplateItem {
  id: string;
  name: string;
  orientation: string;
  is_custom: boolean;
  s3_key: string | null;
}

export async function getTemplates(): Promise<TemplateItem[]> {
  const res = await fetch(`${API_BASE}/templates`);
  if (!res.ok) throw new Error("Failed to fetch templates");
  const data = await res.json();
  return data.templates;
}

export async function saveTemplate(
  name: string,
  s3Key: string,
  orientation: string = "vertical"
): Promise<TemplateItem> {
  const res = await fetch(`${API_BASE}/templates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, s3_key: s3Key, orientation }),
  });
  if (!res.ok) throw new Error("Failed to save template");
  return res.json();
}

export async function getTemplateUploadUrl(): Promise<{
  upload_url: string;
  template: TemplateItem;
}> {
  const res = await fetch(`${API_BASE}/templates/upload`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to get template upload URL");
  return res.json();
}

export async function deleteTemplate(templateId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/templates/${templateId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete template");
}

// ── Bundles ──

export interface BundleListingInput {
  title: string;
  tags: string[];
  description: string;
  price: number | null;
  image_filenames: string[];
}

export interface BundleOutput {
  theme: string;
  pack_size: number;
  title: string;
  tags: string[];
  description: string;
  price: number;
  image_filenames: string[];
  source_indices: number[];
}

export async function generateBundles(
  listings: BundleListingInput[],
  groups?: { theme: string; indices: number[] }[]
): Promise<BundleOutput[]> {
  const res = await fetch(`${API_BASE}/bundles/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listings, groups }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Bundle generation failed: ${detail}`);
  }
  const data = await res.json();
  return data.bundles;
}

// ── Bulk Publish ──

export interface BulkPublishItem {
  s3_key: string;
  sizes: string[];
  title: string;
  description: string;
  tags: string[];
  price: number;
}

export interface BulkPublishResponse {
  job_ids: string[];
  total: number;
}

export async function bulkPublish(
  items: BulkPublishItem[]
): Promise<BulkPublishResponse> {
  const res = await fetch(`${API_BASE}/publish/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Bulk publish failed: ${detail}`);
  }
  return res.json();
}

// ── Analytics ──

export interface ListingStats {
  listing_id: string;
  title: string;
  views: number;
  favorites: number;
  url: string | null;
}

export interface AnalyticsResponse {
  listings: ListingStats[];
  total_views: number;
  total_favorites: number;
}

export async function getAnalytics(): Promise<AnalyticsResponse> {
  const res = await fetch(`${API_BASE}/analytics`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Analytics fetch failed: ${detail}`);
  }
  return res.json();
}
