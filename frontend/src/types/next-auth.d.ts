import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
    } & DefaultSession["user"];
    /**
     * A short-lived HS256 JWT, separate from NextAuth's own session cookie,
     * verified independently by the FastAPI backend (see backend/app/auth.py).
     * Attach as `Authorization: Bearer <backendToken>` on API calls.
     */
    backendToken: string;
  }

  interface JWT {
    sub?: string;
    email?: string;
    name?: string;
    picture?: string;
  }
}
