export function absolutePublicUrl(path: string, origin: string): string {
  return new URL(path, origin).toString();
}
