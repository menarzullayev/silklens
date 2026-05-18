import { redirect } from 'next/navigation';

import { AppSidebar } from '@/components/layout/app-sidebar';
import { Topbar } from '@/components/layout/topbar';
import { auth } from '@/lib/auth/auth';

export default async function DashboardLayout({
  children,
}: {
  readonly children: React.ReactNode;
}): Promise<JSX.Element> {
  const session = await auth();
  if (!session) redirect('/login');

  return (
    <div className="flex min-h-screen w-full">
      <AppSidebar permissions={session.user.permissions} />
      <div className="flex min-h-screen flex-1 flex-col">
        <Topbar />
        <main className="flex-1 bg-muted/20 p-6">
          <div className="mx-auto w-full max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
