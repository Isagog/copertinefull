// app/lib/auth/mail.ts
import nodemailer from "nodemailer";
import type { AuthConfig } from "./config.ts";
import { MAGIC_TTL_SECONDS } from "./session.ts";

export async function sendMagicLink(to: string, token: string, config: AuthConfig): Promise<void> {
  const link = `${config.appUrl}/auth/verify?token=${encodeURIComponent(token)}`;
  const minutes = MAGIC_TTL_SECONDS / 60;
  const transport = nodemailer.createTransport({
    host: config.smtp.host,
    port: config.smtp.port,
    secure: config.smtp.port === 465, // 465 is implicit TLS; anything else upgrades with STARTTLS
    requireTLS: config.smtp.port !== 465,
    auth: { user: config.smtp.user, pass: config.smtp.pass },
  });

  await transport.sendMail({
    from: config.smtp.from,
    to,
    subject: "Accesso all'archivio copertine de il manifesto",
    text: `Per accedere all'archivio apri questo link:\n\n${link}\n\nIl link scade tra ${minutes} minuti.`,
    html:
      `<p>Per accedere all'archivio delle copertine:</p>` +
      `<p><a href="${link}" style="display:inline-block;padding:10px 20px;background:#dc2626;` +
      `color:#fff;text-decoration:none;border-radius:6px;font-weight:600">Accedi</a></p>` +
      `<p style="color:#666;font-size:0.85em">Il link scade tra ${minutes} minuti.</p>`,
  });
}
