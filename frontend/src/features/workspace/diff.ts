export type DiffType = "same" | "add" | "del";

export interface DiffLine {
  type: DiffType;
  line: string;
  oldNo?: number;
  newNo?: number;
}

export interface DiffResult {
  lines: DiffLine[];
  additions: number;
  deletions: number;
}

const MAX_DP_CELLS = 260_000;

export function computeLineDiff(before: string, after: string): DiffResult {
  if (!before && !after) return { lines: [], additions: 0, deletions: 0 };
  const a = String(before || "").split("\n");
  const b = String(after || "").split("\n");
  if (!before) {
    const lines = b.map((line, index) => ({
      type: "add" as const,
      line,
      newNo: index + 1,
    }));
    return { lines, additions: lines.length, deletions: 0 };
  }
  if (!after) {
    const lines = a.map((line, index) => ({
      type: "del" as const,
      line,
      oldNo: index + 1,
    }));
    return { lines, additions: 0, deletions: lines.length };
  }
  if (a.length * b.length > MAX_DP_CELLS) {
    const lines: DiffLine[] = [
      ...a.map((line, index) => ({
        type: "del" as const,
        line,
        oldNo: index + 1,
      })),
      ...b.map((line, index) => ({
        type: "add" as const,
        line,
        newNo: index + 1,
      })),
    ];
    return { lines, additions: b.length, deletions: a.length };
  }

  const dp = Array.from(
    { length: a.length + 1 },
    () => new Uint16Array(b.length + 1),
  );
  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      dp[i][j] =
        a[i] === b[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const lines: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      lines.push({ type: "same", line: a[i], oldNo: i + 1, newNo: j + 1 });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      lines.push({ type: "del", line: a[i], oldNo: i + 1 });
      i += 1;
    } else {
      lines.push({ type: "add", line: b[j], newNo: j + 1 });
      j += 1;
    }
  }
  while (i < a.length) {
    lines.push({ type: "del", line: a[i], oldNo: i + 1 });
    i += 1;
  }
  while (j < b.length) {
    lines.push({ type: "add", line: b[j], newNo: j + 1 });
    j += 1;
  }

  return {
    lines,
    additions: lines.filter((line) => line.type === "add").length,
    deletions: lines.filter((line) => line.type === "del").length,
  };
}
