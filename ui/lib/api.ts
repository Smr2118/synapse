export const DEFAULT_API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://synapse-5w9z.onrender.com";

export async function callApi(
  method: "GET" | "POST" | "DELETE",
  url: string,
  body?: unknown
): Promise<{ status: number; data: Record<string, unknown> }> {
  try {
    const options: RequestInit = { method, signal: AbortSignal.timeout(120_000) };
    if (body !== undefined) {
      options.headers = { "Content-Type": "application/json" };
      options.body = JSON.stringify(body);
    }
    const res = await fetch(url, options);
    try {
      return { status: res.status, data: await res.json() };
    } catch {
      return { status: res.status, data: { error: await res.text() } };
    }
  } catch (err: unknown) {
    return { status: 0, data: { error: String(err) } };
  }
}
