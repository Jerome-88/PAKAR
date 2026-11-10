// Compatibility for saved browser work; new writes use PAKAR keys.
const legacyBrand = "rekakebijakan";

function previousKey(key: string) {
  return key.replace(/^pakar(?=[-_:])/, legacyBrand);
}

export function readBrandedStorage(storage: Storage, key: string): string | null {
  const current = storage.getItem(key);
  if (current !== null) return current;
  const legacy = previousKey(key);
  if (legacy === key) return null;
  const stored = storage.getItem(legacy);
  if (stored === null) return null;
  try {
    storage.setItem(key, stored);
    storage.removeItem(legacy);
  } catch {
    // A full/read-only store must not discard or hide the existing work.
    return stored;
  }
  return stored;
}

export function removeBrandedStorage(storage: Storage, key: string) {
  storage.removeItem(key);
  const legacy = previousKey(key);
  if (legacy !== key) storage.removeItem(legacy);
}
