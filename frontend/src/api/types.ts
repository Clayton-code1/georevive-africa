export interface User {
  username: string;
  display_name: string;
  role: string;
  role_label: string;
  organisation: string;
  permissions: string[];
}

export interface Meta {
  app: string;
  version: string;
  pilot_area: { name: string; bbox: [number, number, number, number]; working_crs: string };
  disclaimer: string;
  roles: Record<string, string>;
}

export interface SourceFile {
  path: string;
  url: string | null;
  sha256: string;
  bytes: number;
}

export interface Source {
  id: string;
  name: string;
  publisher: string;
  url: string;
  urls_tried: { url: string; result: string }[];
  licence: string;
  licence_url: string | null;
  attribution: string | null;
  accessed_at: string | null;
  bbox: number[] | null;
  record_count: number | null;
  raster_size: string | null;
  status: "downloaded" | "partial" | "failed" | "needs_manual_request" | "needs_credentials";
  note: string;
  usage: string;
  error: string | null;
  how_to_obtain: string | null;
  details: Record<string, unknown>;
  is_inbox: boolean;
  layers: { id: string; name: string; kind: string }[];
  files: SourceFile[];
}

export interface AuditEntry {
  id: number;
  at: string;
  username: string;
  role: string;
  action: string;
  object_type: string;
  object_id: string;
  details: Record<string, unknown>;
}
