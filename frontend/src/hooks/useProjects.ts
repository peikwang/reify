import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { ProjectListResponse, Task } from "../api/types";

interface ProjectsState {
  items: Task[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function useProjects(): ProjectsState {
  const [items, setItems] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api<ProjectListResponse>("/api/projects");
      setItems(data.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "项目加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { items, loading, error, reload };
}
