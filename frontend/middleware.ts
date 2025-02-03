import { authMiddleware } from "@clerk/nextjs";
 
export default authMiddleware({
  // Routes that can be accessed while signed out
  publicRoutes: ["/", "/api/search"],
  // Routes that can always be accessed, and have
  // no authentication information
  ignoredRoutes: [
    "/_next/static/(.*)",
    "/favicon.ico",
    "/api/weaviate/(.*)",
  ],
});
 
export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
};
