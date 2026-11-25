// Where things live on the server, per run.
export const runPath = (run: string, rest = "") => `/api/runs/${encodeURIComponent(run)}${rest}`;
export const mediaUrl = (run: string, path: string) => `/media/${encodeURIComponent(run)}/${path}`;
export const runHash = (run: string, stage?: string, tab?: string) =>
  `#/runs/${encodeURIComponent(run)}${stage ? `/${stage}` : ""}${tab ? `/${tab}` : ""}`;
/** A starter template in dark or light mode, as one frame at 2560×1440. */
export const starterPreview = (name: string, mode: string) => `/previews/starters/${name}/${mode}.webp`;
