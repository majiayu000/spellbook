/**
 * Application configuration
 *
 * All configuration is loaded from environment variables.
 * Default values are provided for development.
 */

function getEnv(key: string, defaultValue?: string): string {
  const value = process.env[key] ?? defaultValue;
  if (value === undefined) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

function getEnvNumber(key: string, defaultValue: number): number {
  const value = process.env[key];
  if (value === undefined) return defaultValue;
  const num = Number(value);
  if (Number.isNaN(num)) {
    throw new Error(`Invalid number for environment variable: ${key}`);
  }
  return num;
}

export const config = {
  env: getEnv('NODE_ENV', 'development') as 'development' | 'staging' | 'production',
  port: getEnvNumber('PORT', 3000),
  logLevel: getEnv('LOG_LEVEL', 'info') as 'debug' | 'info' | 'warn' | 'error',

  // LiteLLM proxy configuration
  llm: {
    baseUrl: getEnv('LITELLM_URL', 'http://localhost:4000'),
    apiKey: getEnv('LITELLM_API_KEY', 'sk-1234'),
    defaultModel: getEnv('LLM_MODEL', 'gpt-4o'),
  },

  // Database (uncomment when needed)
  // db: {
  //   url: getEnv('DATABASE_URL'),
  //   poolSize: getEnvNumber('DB_POOL_SIZE', 10),
  // },

  // Redis (uncomment when needed)
  // redis: {
  //   url: getEnv('REDIS_URL', 'redis://localhost:6379'),
  // },

  isDev: getEnv('NODE_ENV', 'development') === 'development',
  isProd: getEnv('NODE_ENV', 'development') === 'production',
} as const;

export type Config = typeof config;
