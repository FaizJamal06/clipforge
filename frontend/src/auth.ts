import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import { SignJWT } from "jose";

// Separate from NextAuth's own (encrypted, frontend-only) session cookie: this
// is a plain HS256 JWT signed with AUTH_SECRET, verified independently by the
// FastAPI backend (see backend/app/auth.py). Both sides must share the exact
// same AUTH_SECRET value.
const backendTokenSecret = new TextEncoder().encode(process.env.AUTH_SECRET);

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, profile }) {
      // `profile` is only present on the initial sign-in request.
      if (profile) {
        token.sub = profile.sub as string;
        token.email = profile.email as string;
        token.name = profile.name as string;
        token.picture = profile.picture as string;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user && token.sub) {
        session.user.id = token.sub;
      }

      session.backendToken = await new SignJWT({
        email: token.email,
        name: token.name,
        picture: token.picture,
      })
        .setProtectedHeader({ alg: "HS256" })
        .setSubject(token.sub as string)
        .setIssuedAt()
        .setExpirationTime("1h")
        .sign(backendTokenSecret);

      return session;
    },
  },
});
