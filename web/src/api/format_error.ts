/**
 * Pull a localized message out of an unknown error.
 *
 * Pattern:
 *  - if it's an `ApiRequestError`, look up `error.<body.code>` in the
 *    current locale, falling back to `body.message` (the server's
 *    English `message` from the structured envelope).
 *  - otherwise, `String(error)` so callers don't lose information.
 *
 * The optional `vars` argument forwards to the i18n util's `{{var}}`
 * interpolation. Most callers won't pass it; it's there for the few
 * codes whose translations reference template variables.
 */

import { type TranslateFn } from "@/i18n";

import { ApiRequestError } from "@/api/client";

export function formatApiError(
  err: unknown,
  t: TranslateFn,
  vars?: Record<string, string | number>,
): string {
  if (err instanceof ApiRequestError) {
    return t(`error.${err.body.code}`, err.body.message, vars);
  }
  if (err instanceof Error) return err.message;
  return String(err);
}
