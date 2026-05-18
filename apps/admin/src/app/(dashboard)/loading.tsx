import { Loader2 } from 'lucide-react';

export default function DashboardLoading(): JSX.Element {
  return (
    <div
      role="status"
      className="flex items-center justify-center py-24 text-muted-foreground"
    >
      <Loader2 className="mr-2 h-5 w-5 animate-spin" aria-hidden />
      <span className="text-sm">Loading…</span>
    </div>
  );
}
