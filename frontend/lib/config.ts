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
          searches: (id: string | number) => `/api/v1/projects/${id}/searches`,
          leads: (id: string | number) => `/api/v1/projects/${id}/leads`,
          leadsExport: (id: string | number) =>
            `/api/v1/projects/${id}/leads/export`,
        },
        leads: {
          byId: (id: string | number) => `/api/v1/leads/${id}`,
          notes: (id: string | number) => `/api/v1/leads/${id}/notes`,
          stats: "/api/v1/leads/stats",
        },
        subscription: {
          root: "/api/v1/subscription",
        },
        billing: {
          checkoutSession: "/api/v1/billing/checkout-session",
          portalSession: "/api/v1/billing/portal-session",
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
        searches: (id: string | number) => `/api/projects/${id}/searches`,
        leads: (id: string | number) => `/api/projects/${id}/leads`,
        leadsExport: (id: string | number) =>
          `/api/projects/${id}/leads/export`,
      },
      leads: {
        byId: (id: string | number) => `/api/leads/${id}`,
        notes: (id: string | number) => `/api/leads/${id}/notes`,
        stats: "/api/leads/stats",
      },
      subscription: {
        root: "/api/subscription",
      },
      billing: {
        checkoutSession: "/api/billing/checkout-session",
        portalSession: "/api/billing/portal-session",
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
    billing: "/billing",
    settings: "/settings",
    project: (id: string | number) => `/projects/${id}`,
    lead: (id: string | number, leadId: string | number) =>
      `/projects/${id}/leads/${leadId}`,
    newSearch: (id: string | number) => `/projects/${id}/search`,
    searchResults: (id: string | number, searchId: string | number) =>
      `/projects/${id}/search/results?search_id=${searchId}`,
  },
} as const
