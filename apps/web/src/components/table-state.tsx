import { AlertTriangle, Loader2 } from "lucide-react";

import { Button } from "./ui/button";
import { Skeleton } from "./ui/skeleton";

/**
 * Loading state for the big data tables. Shows an explicit spinner + message
 * (so the user knows data is actually being fetched, not stuck) on top of
 * skeleton rows that hint at the table shape.
 */
export function TableLoadingState({
  message = "Veriler yükleniyor…",
  hint,
  rows = 8,
}: {
  message?: string;
  hint?: string;
  rows?: number;
}) {
  return (
    <div className="p-6 sm:p-8">
      <div className="mb-5 flex items-center gap-3 rounded-md border border-border bg-surface px-4 py-3">
        <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{message}</p>
          <p className="font-mono text-[11px] text-muted-foreground">
            {hint ?? "Liste bir kez yüklenip önbelleğe alınıyor; sonraki açılışlar anında gelir."}
          </p>
        </div>
      </div>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    </div>
  );
}

/**
 * Error state for the big data tables. Clearly distinguishes a failed fetch
 * from a slow one and offers a retry, so the user is never left guessing.
 */
export function TableErrorState({
  error,
  onRetry,
  retrying = false,
}: {
  error?: unknown;
  onRetry: () => void;
  retrying?: boolean;
}) {
  const message =
    error instanceof Error
      ? error.message
      : "Veriler yüklenirken bir sorun oluştu.";
  return (
    <div className="flex flex-col items-center justify-center gap-4 p-12 text-center sm:p-16">
      <div className="flex size-12 items-center justify-center rounded-full border border-destructive/30 bg-destructive/10">
        <AlertTriangle className="size-6 text-destructive" />
      </div>
      <div className="max-w-sm space-y-1">
        <p className="text-sm font-medium text-foreground">
          Veriler yüklenemedi
        </p>
        <p className="text-xs text-muted-foreground">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry} disabled={retrying}>
        {retrying ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <AlertTriangle className="size-4" />
        )}
        Tekrar Dene
      </Button>
    </div>
  );
}
