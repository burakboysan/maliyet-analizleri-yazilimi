import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowUpRight,
  Boxes,
  Calculator,
  CalendarDays,
  Coins,
  FileText,
  Layers,
  UsersRound,
  WandSparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { useAuth } from "../lib/auth";
import { isOwner } from "../lib/roles";


type ModuleCard = {
  title: string;
  description: string;
  to: string;
  icon: LucideIcon;
  ownerOnly?: boolean;
};

const MODULES: ModuleCard[] = [
  {
    title: "Ürünler",
    description: "Ürün maliyetleri, reçete ağacı ve revizyon işlemleri.",
    to: "/products",
    icon: Boxes,
  },
  {
    title: "Malzemeler",
    description: "Malzeme kartları, birim fiyatlar ve içe aktarma.",
    to: "/materials",
    icon: Layers,
  },
  {
    title: "Seçim Sihirbazı",
    description: "Adım adım ürün konfigürasyonu ve maliyet önizlemesi.",
    to: "/selection-wizard",
    icon: WandSparkles,
  },
  {
    title: "İzin Yönetim Modülü",
    description: "İzin bakiyeleri, talepler ve onay akışları.",
    to: "/leave-management",
    icon: CalendarDays,
  },
  {
    title: "Teknik Hesaplamalar",
    description: "Fan motor, basınç kaybı, kapasite ve patlama kapağı hesapları.",
    to: "/technical-calculations",
    icon: Calculator,
  },
  {
    title: "Doküman Yönetimi",
    description: "Merkezi doküman listesi ve PDF yükleme işlemleri.",
    to: "/documents",
    icon: FileText,
  },
  {
    title: "Sabit Maliyet Yönetimi",
    description: "Sabit maliyet kalemlerini görüntüleyin ve fiyatları yönetin.",
    to: "/fixed-costs",
    icon: Coins,
    ownerOnly: true,
  },
  {
    title: "Kullanıcı Yönetimi",
    description: "Kullanıcılar, roller, modül ve mobil modül yetkileri.",
    to: "/users",
    icon: UsersRound,
    ownerOnly: true,
  },
];



export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({ meta: [{ title: "Gösterge Paneli — Bomaksan" }] }),
  component: DashboardPage,
});

function DashboardPage() {
  const { user } = useAuth();
  const owner = isOwner(user);
  const visibleModules = MODULES.filter((m) => !m.ownerOnly || owner);

  return (
    <div className="space-y-8 p-8">
      <section>
        <div className="mb-3 px-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Modüller
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {visibleModules.map((m) => (
            <Link
              key={m.to}
              to={m.to}
              className="group flex items-start gap-4 rounded-lg border border-border bg-surface p-5 transition-colors hover:border-primary/50 hover:bg-accent"
            >
              <div className="grid size-10 shrink-0 place-items-center rounded-md border border-border bg-background text-primary">
                <m.icon className="size-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 font-display font-bold tracking-tight">
                  {m.title}
                  <ArrowUpRight className="size-4 text-muted-foreground transition-colors group-hover:text-primary" />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {m.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}


