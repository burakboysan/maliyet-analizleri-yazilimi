import {
  createFileRoute,
  Outlet,
  useNavigate,
  useRouterState,
} from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { LogOut, Menu } from "lucide-react";

import { useAuth } from "../lib/auth";
import { AppSidebar, SidebarNav } from "../components/app-sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "../components/ui/sheet";
import logo from "../assets/logo.png";

export const Route = createFileRoute("/_authenticated")({
  component: AuthenticatedLayout,
});

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Gösterge Paneli",
  "/products": "Ürünler",
  "/materials": "Malzemeler",
  "/selection-wizard": "Seçim Sihirbazı",
  "/technical-calculations": "Teknik Hesaplamalar",
  "/leave-management": "İzin Yönetimi",
  "/documents": "Doküman Yönetimi",
  "/users": "Kullanıcı Yönetimi",
};

function AuthenticatedLayout() {
  const { token, user, loading, signOut } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!loading && !token) navigate({ to: "/login", replace: true });
  }, [loading, token, navigate]);

  if (loading || !token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="size-8 animate-spin rounded-full border-2 border-border border-t-primary" />
      </div>
    );
  }

  const title =
    Object.entries(PAGE_TITLES).find(([k]) => pathname.startsWith(k))?.[1] ??
    "Bomaksan";

  const initials = (user?.kullanici_adi ?? "?")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <AppSidebar />

      {/* Mobile slide-in nav */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-72 bg-sidebar p-0">
          <SheetHeader className="flex h-16 flex-row items-center gap-3 border-b border-border px-6 text-left">
            <SheetTitle className="sr-only">Menü</SheetTitle>
            <img src={logo} alt="Bomaksan" className="h-7 w-auto" />
          </SheetHeader>
          <SidebarNav onNavigate={() => setMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-border px-4 sm:px-8">
          <div className="flex min-w-0 items-center gap-2">
            <button
              onClick={() => setMobileNavOpen(true)}
              aria-label="Menüyü aç"
              className="-ml-1 rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:hidden"
            >
              <Menu className="size-5" />
            </button>
            <h1 className="truncate font-display text-base font-bold tracking-tight sm:text-lg">
              {title}
            </h1>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-3 rounded-md border border-border bg-surface px-2 py-1.5 text-left outline-none transition-colors hover:bg-accent sm:px-3">
              <div className="flex size-8 items-center justify-center rounded-full bg-secondary font-mono text-xs">
                {initials}
              </div>
              <div className="hidden min-w-0 sm:block">
                <div className="truncate text-sm font-medium">
                  {user?.kullanici_adi}
                </div>
                <div className="truncate text-[10px] text-muted-foreground">
                  {user?.rol_adi ?? "Kullanıcı"}
                </div>
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <DropdownMenuLabel>
                {user?.kullanici_adi}
                <div className="font-normal text-muted-foreground">
                  {user?.rol_adi ?? "Kullanıcı"}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => {
                  signOut();
                  navigate({ to: "/login", replace: true });
                }}
              >
                <LogOut className="size-4" /> Çıkış Yap
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
