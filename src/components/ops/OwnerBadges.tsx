import { cn } from "@/lib/utils";
import { OWNER_COLORS, type Owner } from "@/lib/ops/tasks";

export function OwnerBadges({ owners, className }: { owners: Owner[]; className?: string }) {
  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {owners.map((o) => (
        <span
          key={o}
          className={cn(
            "inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium",
            OWNER_COLORS[o],
          )}
        >
          {o}
        </span>
      ))}
    </div>
  );
}
