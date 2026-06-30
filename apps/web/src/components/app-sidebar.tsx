import { Link, useRouterState } from "@tanstack/react-router";
import {
  Boxes,
  CalendarDays,
  Calculator,
  Coins,
  FileText,
  LayoutDashboard,
  Layers,
  UsersRound,
  WandSparkles,
} from "lucide-react";
import { isOwner } from "../lib/roles";
import type { LucideIcon } from "lucide-react";

import { useAuth } from "../lib/auth";
import { cn } from "../lib/utils";
import logo from "../assets/logo.png";

type NavItem = { title: string; to: string; icon: LucideIcon };

const mainItems: NavItem[] = [
  { title: "Gösterge Paneli", to: "/dashboard", icon: LayoutDashboard },
  { title: "Ürünler", to: "/products", icon: Boxes },
  { title: "Malzemeler", to: "/materials", icon: Layers },
  { title: "Seçim Sihirbazı", to: "/selection-wizard", icon: WandSparkles },
];

const engineeringItems: NavItem[] = [
  { title: "Teknik Hesaplamalar", to: "/technical-calculations", icon: Calculator },
  { title: "İzin Yönetimi", to: "/leave-management", icon: CalendarDays },
];

/**
 * Shared nav body used both by the fixed desktop sidebar and the mobile
 * drawer. `onNavigate` lets the mobile drawer close itself on selection.
 */
export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { user } = useAuth();
  const owner = isOwner(user);

  const managementItems: NavItem[] = [
    { title: "Doküman Yönetimi", to: "/documents", icon: FileText },
    ...(owner
      ? [
          { title: "Sabit Maliyet Yönetimi", to: "/fixed-costs", icon: Coins },
          { title: "Kullanıcı Yönetimi", to: "/users", icon: UsersRound },
        ]
      : []),
  ];

  const renderItem = (item: NavItem) => {
    const active = pathname === item.to || pathname.startsWith(item.to + "/");
    return (
      <Link
        key={item.to}
        to={item.to}
        onClick={onNavigate}
        className={cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
          active
            ? "border border-border bg-sidebar-accent text-foreground"
            : "border border-transparent text-muted-foreground hover:bg-accent hover:text-foreground",
        )}
      >
        <item.icon
          className={cn("size-4 shrink-0", active ? "text-primary" : "")}
        />
        <span className="truncate">{item.title}</span>
      </Link>
    );
  };

  return (
    <nav className="flex-1 space-y-1 overflow-y-auto p-4">
      <div className="mb-3 px-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        Menü
      </div>
      {mainItems.map(renderItem)}
      <div className="mb-3 mt-6 px-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        Mühendislik
      </div>
      {engineeringItems.map(renderItem)}
      <div className="mb-3 mt-6 px-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        Yönetim
      </div>
      {managementItems.map(renderItem)}
    </nav>
  );
}

export function AppSidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-sidebar md:flex">
      <div className="flex h-16 items-center gap-3 border-b border-border px-6">
        <img src={logo} alt="Bomaksan" className="h-7 w-auto" />
      </div>
      <SidebarNav />
    </aside>
  );
}
