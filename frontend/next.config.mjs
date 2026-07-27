import createNextIntlPlugin from 'next-intl/plugin'

// Point the plugin at our request config (locale resolved from the NEXT_LOCALE
// cookie; no locale routing). See frontend/i18n/request.ts.
const withNextIntl = createNextIntlPlugin('./i18n/request.ts')

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  output: 'standalone',
}

export default withNextIntl(nextConfig)
