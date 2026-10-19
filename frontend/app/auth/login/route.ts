// app/auth/login/route.ts — POST target of the /login form.
//
// The answer is the same whether or not the address is allowlisted, so the
// form cannot be used to discover who has access; the mail goes out after the
// response so its timing does not tell either.
import { after, NextResponse } from "next/server";
import { getAuthConfig, normalizeEmail } from "../../lib/auth/config.ts";
import { sendMagicLink } from "../../lib/auth/mail.ts";
import { createRateLimiter } from "../../lib/auth/rate-limit.ts";
import { createMagicToken } from "../../lib/auth/session.ts";

const MAX_EMAIL_LENGTH = 254;
const allowSend = createRateLimiter(60_000);

export async function POST(request: Request): Promise<NextResponse> {
  const config = getAuthConfig();
  const form = await request.formData().catch(() => null);
  const raw = form?.get("email");
  const email = typeof raw === "string" ? normalizeEmail(raw) : "";

  if (email.length <= MAX_EMAIL_LENGTH && config.allowedEmails.has(email) && allowSend(email)) {
    const token = createMagicToken(email, config.secret);
    after(() =>
      sendMagicLink(email, token, config).catch((error: unknown) => {
        console.error(`Magic link to ${email} could not be sent:`, error);
      }),
    );
  }

  return NextResponse.redirect(`${config.appUrl}/login?sent=1`, 303);
}
