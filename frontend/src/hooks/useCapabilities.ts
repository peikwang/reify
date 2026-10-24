import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { CapabilitiesResponse, Capability } from "../api/types";

interface CapabilitiesState {
  capabilities: Capability[];
  loading: boolean;
  error: string | null;
}

export function useCapabilities(): CapabilitiesState {
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api<CapabilitiesResponse>("/api/capabilities")
      .then((data) => {
        if (!active) return;
        setCapabilities(data.items);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : "能力加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { capabilities, loading, error };
}
