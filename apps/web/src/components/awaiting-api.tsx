import { Clock } from "lucide-react";

import { cn } from "../lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";

const DEFAULT_HINT =
  "Bu işlem için backend ucu henüz hazır değil. Hazır olduğunda otomatik etkinleşecek.";

export function AwaitingApiBadge({
  label = "API bekliyor",
  hint = DEFAULT_HINT,
  className,
  compact = false,
}: {
  label?: string;
  hint?: string;
  className?: string;
  compact?: boolean;
}) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              "inline-flex cursor-help items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 font-mono uppercase tracking-wide text-amber-400",
              compact ? "size-5 justify-center p-0" : "px-2 py-0.5 text-[10px]",
              className,
            )}
            aria-label={compact ? "API bekliyor" : undefined}
          >
            <Clock className="size-3" />
            {!compact && label}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-xs">{hint}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
