/**
 * Structured logging
 *
 * Simple, structured logger for development and production.
 * For more advanced logging, see structured-logging-lite skill.
 */

import { config } from './config.js';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  service: string;
  [key: string]: unknown;
}

const LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

class Logger {
  private level: LogLevel;
  private service: string;
  private context: Record<string, unknown> = {};

  constructor(service: string, level: LogLevel = 'info') {
    this.service = service;
    this.level = level;
  }

  private shouldLog(level: LogLevel): boolean {
    return LEVELS[level] >= LEVELS[this.level];
  }

  private write(level: LogLevel, message: string, data?: Record<string, unknown>) {
    if (!this.shouldLog(level)) return;

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      service: this.service,
      ...this.context,
      ...data,
    };

    const output = config.isDev
      ? `[${entry.timestamp}] ${level.toUpperCase().padEnd(5)} ${message} ${
          data ? JSON.stringify(data) : ''
        }`
      : JSON.stringify(entry);

    if (level === 'error') {
      console.error(output);
    } else {
      console.log(output);
    }
  }

  debug(message: string, data?: Record<string, unknown>) {
    this.write('debug', message, data);
  }

  info(message: string, data?: Record<string, unknown>) {
    this.write('info', message, data);
  }

  warn(message: string, data?: Record<string, unknown>) {
    this.write('warn', message, data);
  }

  error(message: string, data?: Record<string, unknown>) {
    this.write('error', message, data);
  }

  child(context: Record<string, unknown>): Logger {
    const child = new Logger(this.service, this.level);
    child.context = { ...this.context, ...context };
    return child;
  }
}

// Global logger instance
export const logger = new Logger('app', config.logLevel);

// Create child loggers for different modules
export function createLogger(module: string): Logger {
  return logger.child({ module });
}
