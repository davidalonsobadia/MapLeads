export const config = {
  app: {
    name: "MapLeads",
    description: "Find and manage local business leads from Google Maps",
  },
  api: {
    // Real backend API configuration
    baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    apiKey: process.env.NEXT_PUBLIC_API_KEY || "PI1u-i-6i2pGeIi9q6OOaYYLc7BnjCHzJ58m0NEaIrM",
    endpoints: {
      // Backend API endpoints (v1)
      backend: {
        auth: {
          register: "/api/v1/auth/register",
          login: "/api/v1/auth/login",
          logout: "/api/v1/auth/logout",
          verifyEmail: "/api/v1/auth/verify-email",
          forgotPassword: "/api/v1/auth/forgot-password",
          resetPassword: "/api/v1/auth/reset-password",
          me: "/api/v1/auth/me",
        },
        projects: {
          root: "/api/v1/projects",
          byId: (id: string | number) => `/api/v1/projects/${id}`,
        },
        searches: {
          byProject: (id: string | number) => `/api/v1/projects/${id}/searches`,
        },
        subscription: {
          root: "/api/v1/subscription",
        },
      },
      // Frontend API routes (proxy to backend)
      auth: {
        register: "/api/auth/register",
        login: "/api/auth/login",
        logout: "/api/auth/logout",
        verifyEmail: "/api/auth/verify-email",
        forgotPassword: "/api/auth/forgot-password",
        resetPassword: "/api/auth/reset-password",
        me: "/api/auth/me",
      },
      projects: {
        root: "/api/projects",
        byId: (id: string | number) => `/api/projects/${id}`,
      },
      searches: {
        byProject: (id: string | number) => `/api/projects/${id}/searches`,
      },
      subscription: {
        root: "/api/subscription",
      },
    },
  },
  routes: {
    home: "/",
    login: "/login",
    register: "/register",
    verifyEmail: "/verify-email",
    forgotPassword: "/forgot-password",
    resetPassword: "/reset-password",
    dashboard: "/dashboard",
    project: (id: string | number) => `/projects/${id}`,
    projectSearch: (id: string | number) => `/projects/${id}/search`,
  },
} as const
