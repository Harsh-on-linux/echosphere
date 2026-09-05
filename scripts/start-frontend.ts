import { spawn } from 'node:child_process'
import path from 'node:path'

const webDir = path.resolve(__dirname, '..', 'web')
const env = {
  ...process.env,
  AGENT_BACKEND_URL: process.env.AGENT_BACKEND_URL || 'http://localhost:8000',
}

console.log(`[WeatherGPT Frontend] Starting Next.js (backend target: ${env.AGENT_BACKEND_URL})`)

const proc = spawn('bun', ['run', 'dev'], {
  cwd: webDir,
  stdio: 'inherit',
  env,
  shell: process.platform === 'win32',
})

proc.on('exit', (code, signal) => {
  if (code !== null) {
    process.exit(code)
  }
  if (signal) {
    process.kill(process.pid, signal)
  }
})
