// One of a run's own files (outline.json, script.json, reviews, critiques, plans, topics.md…), read through /media.
import { mediaUrl } from "../services/runs";
import { useApi } from "./useApi";

export function useRunFile<T>(run: string, path: string, kind: "json" | "text" = "json") {
  const file = useApi<T>(mediaUrl(run, path), kind);
  return { ...file, missing: !file.loading && file.data === null };
}
