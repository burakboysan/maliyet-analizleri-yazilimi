export type ModuleInfo = {
  key: string;
  title: string;
  phase: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8100";

export async function fetchModules(): Promise<ModuleInfo[]> {
  const response = await fetch(`${API_BASE_URL}/modules`);
  if (!response.ok) {
    throw new Error("Modül listesi alınamadı.");
  }
  const payload = (await response.json()) as { modules?: ModuleInfo[] };
  return payload.modules ?? [];
}
