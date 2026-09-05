import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

const serverDir = path.resolve(__dirname, '..', 'server')

function getPythonExecutable(): string {
  const winVenv = path.join(serverDir, 'venv', 'Scripts', 'python.exe')
  if (fs.existsSync(winVenv)) {
    return winVenv
  }

  const posixVenv = path.join(serverDir, 'venv', 'bin', 'python')
  if (fs.existsSync(posixVenv)) {
    return posixVenv
  }

  return process.platform === 'win32' ? 'python' : 'python3'
}

const pythonExe = getPythonExecutable()
console.log(`[WeatherGPT Backend] Using Python: ${pythonExe}`)

const proc = spawn(pythonExe, ['src/server.py'], {
  cwd: serverDir,
  stdio: 'inherit',
  env: {
    ...process.env,
    PYTHONUNBUFFERED: '1',
  },
})

proc.on('exit', (code, signal) => {
  if (code !== null) {
    process.exit(code)
  }
  if (signal) {
    process.kill(process.pid, signal)
  }
})
