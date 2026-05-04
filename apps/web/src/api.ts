export type ModuleInfo = {
  key: string;
  title: string;
  phase: number;
};

export type UserInfo = {
  id: number;
  kullanici_adi: string;
  rol_id?: number | null;
  rol_adi?: string | null;
  module_permissions: Record<string, boolean>;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: UserInfo;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8100";

async function parseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || "İşlem tamamlanamadı.";
  } catch {
    return "İşlem tamamlanamadı.";
  }
}

export async function login(kullaniciAdi: string, sifre: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      kullanici_adi: kullaniciAdi,
      sifre,
    }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as LoginResponse;
}

export async function fetchMe(token: string): Promise<UserInfo> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as UserInfo;
}

export async function fetchModules(token: string): Promise<ModuleInfo[]> {
  const response = await fetch(`${API_BASE_URL}/modules`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  const payload = (await response.json()) as { modules?: ModuleInfo[] };
  return payload.modules ?? [];
}
