const KEY = "synapse_username";

export function getSavedUsername(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(KEY) ?? "";
}

export function saveUsername(username: string): void {
  if (typeof window === "undefined") return;
  if (username) localStorage.setItem(KEY, username);
  else localStorage.removeItem(KEY);
}
