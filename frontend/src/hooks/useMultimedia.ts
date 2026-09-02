import { useCallback, useState } from "react";
import {
  AssetPackRequest,
  AssetPackResponse,
  downloadAssetPack,
  generateAssetPack,
  getTaskStatus,
  TaskStatusResponse,
} from "../api/multimedia";

export interface UseMultimediaResult {
  loading: boolean;
  error: string | null;
  assetId: number | null;
  taskId: string | null;
  lastResult: AssetPackResponse | null;
  generate: (req: AssetPackRequest) => Promise<AssetPackResponse | null>;
  download: (assetId: number) => Promise<Blob | null>;
  poll: (taskId: string) => Promise<TaskStatusResponse | null>;
  reset: () => void;
}

export function useMultimedia(): UseMultimediaResult {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assetId, setAssetId] = useState<number | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<AssetPackResponse | null>(null);

  const generate = useCallback(
    async (req: AssetPackRequest): Promise<AssetPackResponse | null> => {
      setLoading(true);
      setError(null);
      try {
        const res = await generateAssetPack(req);
        setAssetId(res.asset_id);
        setTaskId(res.task_id);
        setLastResult(res);
        return res;
      } catch (e) {
        setError(e instanceof Error ? e.message : "unknown error");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const download = useCallback(
    async (id: number): Promise<Blob | null> => {
      try {
        return await downloadAssetPack(id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "download failed");
        return null;
      }
    },
    [],
  );

  const poll = useCallback(
    async (tid: string): Promise<TaskStatusResponse | null> => {
      try {
        return await getTaskStatus(tid);
      } catch (e) {
        setError(e instanceof Error ? e.message : "poll failed");
        return null;
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setError(null);
    setAssetId(null);
    setTaskId(null);
    setLastResult(null);
  }, []);

  return { loading, error, assetId, taskId, lastResult, generate, download, poll, reset };
}
