"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { callApi } from "@/lib/api";
import { getSavedUsername, saveUsername } from "@/lib/profile";

const GOALS = ["Build muscle", "Lose weight", "Improve endurance", "General health"];
const LEVELS = ["Beginner", "Intermediate", "Advanced"];

interface Profile {
  goal: string;
  dietary: string;
  fitness_level: string;
  notes: string;
}

interface Props {
  apiUrl: string;
  username: string;
  onUsernameChange: (u: string) => void;
}

export function UserProfile({ apiUrl, username, onUsernameChange }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [profile, setProfile] = useState<Profile>({ goal: "", dietary: "", fitness_level: "", notes: "" });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);
  const [profileStatus, setProfileStatus] = useState<"existing" | "new" | null>(null);

  // On mount: restore username from localStorage, load profile from backend
  useEffect(() => {
    const saved = getSavedUsername();
    if (saved) {
      onUsernameChange(saved);
      loadProfile(saved);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadProfile(u: string) {
    const { status, data } = await callApi("GET", `${apiUrl}/profile/${encodeURIComponent(u)}`);
    if (status === 200) {
      setProfile({
        goal: (data.goal as string) ?? "",
        dietary: (data.dietary as string) ?? "",
        fitness_level: (data.fitness_level as string) ?? "",
        notes: (data.notes as string) ?? "",
      });
    }
  }

  async function handleUsernameBlur() {
    const u = draft.trim().toLowerCase();
    if (!u) return;
    setLookingUp(true);
    setProfileStatus(null);
    const { status, data } = await callApi("GET", `${apiUrl}/profile/${encodeURIComponent(u)}`);
    if (status === 200) {
      setProfile({
        goal: (data.goal as string) ?? "",
        dietary: (data.dietary as string) ?? "",
        fitness_level: (data.fitness_level as string) ?? "",
        notes: (data.notes as string) ?? "",
      });
      setProfileStatus("existing");
    } else {
      setProfile({ goal: "", dietary: "", fitness_level: "", notes: "" });
      setProfileStatus("new");
    }
    setLookingUp(false);
  }

  async function handleSave() {
    if (!draft.trim()) return;
    setSaving(true);
    const normalised = draft.trim().toLowerCase();
    await callApi("POST", `${apiUrl}/profile/${encodeURIComponent(normalised)}`, profile);
    saveUsername(normalised);
    onUsernameChange(normalised);
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    setOpen(false);
  }

  function handleOpen() {
    setDraft(username);
    setProfileStatus(null);
    setOpen(true);
  }

  return (
    <div className="relative">
      {/* Badge / trigger */}
      {username ? (
        <button
          onClick={handleOpen}
          className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs hover:bg-muted/40 transition-colors"
        >
          <span className="h-5 w-5 rounded-full bg-primary text-primary-foreground text-[10px] font-bold flex items-center justify-center uppercase">
            {username[0]}
          </span>
          <span className="text-foreground font-medium">{username}</span>
          <span className="text-muted-foreground">· edit profile</span>
        </button>
      ) : (
        <button
          onClick={handleOpen}
          className="flex items-center gap-1.5 rounded-lg border border-dashed border-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:border-border/80 transition-colors"
        >
          + Set profile
        </button>
      )}

      {/* Inline panel */}
      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 rounded-xl border border-border bg-card shadow-lg p-4 space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Your profile</p>
          <p className="text-xs text-muted-foreground">Answers will be personalised to your goals. No password needed.</p>

          <div className="space-y-1">
            <Label className="text-xs">Username</Label>
            <Input
              placeholder="e.g. smitha"
              value={draft}
              onChange={(e) => { setDraft(e.target.value); setProfileStatus(null); }}
              onBlur={handleUsernameBlur}
              className="h-8 text-sm"
            />
            {lookingUp && <p className="text-[10px] text-muted-foreground">Looking up…</p>}
            {!lookingUp && profileStatus === "existing" && (
              <p className="text-[10px] text-primary font-medium">✓ Existing profile loaded</p>
            )}
            {!lookingUp && profileStatus === "new" && (
              <p className="text-[10px] text-muted-foreground">New profile — fill in your details below</p>
            )}
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Goal</Label>
            <Select value={profile.goal} onValueChange={(v) => setProfile((p) => ({ ...p, goal: v ?? "" }))}>
              <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Select…" /></SelectTrigger>
              <SelectContent>{GOALS.map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}</SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Dietary restrictions</Label>
            <Input
              placeholder="e.g. vegan, no dairy, none"
              value={profile.dietary}
              onChange={(e) => setProfile((p) => ({ ...p, dietary: e.target.value }))}
              className="h-8 text-sm"
            />
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Fitness level</Label>
            <Select value={profile.fitness_level} onValueChange={(v) => setProfile((p) => ({ ...p, fitness_level: v ?? "" }))}>
              <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Select…" /></SelectTrigger>
              <SelectContent>{LEVELS.map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}</SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Anything else the agent should know</Label>
            <Textarea
              placeholder="e.g. knee injury, only have dumbbells at home"
              value={profile.notes}
              onChange={(e) => setProfile((p) => ({ ...p, notes: e.target.value }))}
              className="text-sm resize-none h-16"
            />
          </div>

          <div className="flex gap-2 pt-1">
            <Button size="sm" onClick={handleSave} disabled={!draft.trim() || saving} className="flex-1">
              {saving ? "Saving…" : saved ? "Saved ✓" : "Save profile"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          </div>
        </div>
      )}
    </div>
  );
}
