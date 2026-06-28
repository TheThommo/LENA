/**
 * Profile preferences — localStorage with optional cloud sync when authenticated.
 */

export interface UserProfileData {
  specialty: string;
  role: string;
  institution: string;
  focusAreas: string[];
  preferredSources: string[];
  yearsExperience: string;
  researchInterests: string;
  communicationStyle: 'clinical' | 'academic' | 'simplified' | 'default';
  notes: string;
}

const LEGACY_KEY = 'lena_user_profile';
const LEGACY_BRAIN_KEY = 'lena_user_brain';

export const PROFILE_CHANGED_EVENT = 'lena:profile-changed';

let currentUserId: string | null = null;
let currentToken: string | null = null;

function profileKey(userId?: string | null): string {
  const uid = userId ?? currentUserId;
  return uid ? `lena_user_profile_${uid}` : LEGACY_KEY;
}

export function configureProfileSync(userId: string | null, token: string | null) {
  currentUserId = userId;
  currentToken = token;
}

export function loadLocalProfile(userId?: string | null): UserProfileData | null {
  if (typeof window === 'undefined') return null;
  try {
    const key = profileKey(userId);
    const stored = localStorage.getItem(key) || localStorage.getItem(LEGACY_KEY) || localStorage.getItem(LEGACY_BRAIN_KEY);
    if (!stored) return null;
    const parsed = JSON.parse(stored) as UserProfileData;
    if (key !== LEGACY_KEY && !localStorage.getItem(key)) {
      localStorage.setItem(key, stored);
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveLocalProfile(profile: UserProfileData, userId?: string | null) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(profileKey(userId), JSON.stringify(profile));
    window.dispatchEvent(new CustomEvent(PROFILE_CHANGED_EVENT));
  } catch {}
}

export async function hydrateProfileFromCloud(
  token: string,
  fetchPrefs: (t: string) => Promise<{ preferences: UserProfileData; updated_at: string | null }>,
): Promise<UserProfileData | null> {
  try {
    const remote = await fetchPrefs(token);
    const cloud = remote.preferences;
    if (!cloud || typeof cloud !== 'object') return loadLocalProfile();

    const local = loadLocalProfile();
    if (!local) {
      saveLocalProfile(cloud as UserProfileData);
      return cloud as UserProfileData;
    }

    const cloudTime = remote.updated_at ? Date.parse(remote.updated_at) : 0;
    const localTime = Date.parse(localStorage.getItem(`${profileKey()}_updated`) || '0') || 0;
    const merged = cloudTime >= localTime ? (cloud as UserProfileData) : local;
    saveLocalProfile(merged);
    return merged;
  } catch {
    return loadLocalProfile();
  }
}

export async function syncProfileToCloud(
  token: string,
  profile: UserProfileData,
  savePrefs: (t: string, prefs: UserProfileData) => Promise<void>,
) {
  saveLocalProfile(profile);
  if (!token) return;
  try {
    await savePrefs(token, profile);
    localStorage.setItem(`${profileKey()}_updated`, new Date().toISOString());
  } catch {
    /* local copy is source of truth offline */
  }
}

/** Compact profile context for search personalisation (max ~2k chars). */
export function buildProfileContextForSearch(userId?: string | null): string | undefined {
  const p = loadLocalProfile(userId);
  if (!p) return undefined;

  const lines: string[] = [];
  if (p.specialty) lines.push(`Specialty: ${p.specialty}`);
  if (p.role) lines.push(`Role: ${p.role}`);
  if (p.institution) lines.push(`Institution: ${p.institution}`);
  if (p.focusAreas?.length) lines.push(`Focus areas: ${p.focusAreas.join(', ')}`);
  if (p.researchInterests) lines.push(`Research interests: ${p.researchInterests}`);
  if (p.notes?.trim()) lines.push(`Personal health / context notes: ${p.notes.trim()}`);
  if (p.communicationStyle && p.communicationStyle !== 'default') {
    lines.push(`Preferred response style: ${p.communicationStyle}`);
  }

  if (lines.length === 0) return undefined;
  return lines.join(' ').slice(0, 2000);
}
