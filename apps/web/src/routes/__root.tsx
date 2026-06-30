import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { Outlet, Link, createRootRouteWithContext, useRouter } from "@tanstack/react-router";
import { useEffect } from "react";

import { AuthProvider } from "../lib/auth";
import { Toaster } from "../components/ui/sonner";
import { reportAppError } from "../lib/error-reporting";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Sayfa bulunamadi</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Aradiginiz sayfa mevcut degil veya tasinmis.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Ana sayfaya don
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportAppError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          Sayfa yuklenemedi
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Beklenmeyen bir hata olustu. Sayfayi yenileyebilir veya ana sayfaya donebilirsiniz.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Tekrar dene
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Ana sayfa
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { name: "robots", content: "noindex, nofollow" },
      { name: "googlebot", content: "noindex, nofollow" },
      { title: "Bomaksan Maliyet Analizleri" },
      {
        name: "description",
        content:
          "Bomaksan endustriyel filtrasyon sistemleri icin maliyet analizi ve uretim yonetim platformu.",
      },
      { name: "author", content: "Bomaksan" },
      { property: "og:title", content: "Bomaksan Maliyet Analizleri" },
      {
        property: "og:description",
        content: "Endustriyel maliyet analizi ve uretim yonetim platformu.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "twitter:title", content: "Bomaksan Maliyet Analizleri" },
      {
        name: "twitter:description",
        content: "Bomaksan maliyet analizi ve uretim yonetim platformu.",
      },
    ],
  }),
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

const CACHE_BUSTER = "bomaksan-cache-v1";

const persister =
  typeof window !== "undefined"
    ? createSyncStoragePersister({
        storage: window.localStorage,
        key: "bomaksan-query-cache",
      })
    : undefined;

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister: persister!,
        buster: CACHE_BUSTER,
        maxAge: 24 * 60 * 60 * 1000,
        dehydrateOptions: {
          shouldDehydrateQuery: (query) => {
            const key = query.queryKey?.[0];
            return key === "products" || key === "materials";
          },
        },
      }}
    >
      <AuthProvider>
        <Outlet />
        <Toaster position="top-right" richColors theme="dark" />
      </AuthProvider>
    </PersistQueryClientProvider>
  );
}
