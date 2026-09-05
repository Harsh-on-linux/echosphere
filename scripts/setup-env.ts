import fs from 'node:fs'
import path from 'node:path'

const repoRoot = path.resolve(__dirname, '..')
const envFile = path.join(repoRoot, 'server', '.env')
const legacyEnvFile = path.join(repoRoot, 'server', '.env.local')
const exampleEnvFile = path.join(repoRoot, 'server', '.env.example')

function getCredential(filePath: string, key: string): string | null {
  if (!fs.existsSync(filePath)) return null
  const content = fs.readFileSync(filePath, 'utf-8')
  const match = content.match(new RegExp(`^${key}=([^\\r\\n]+)`, 'm'))
  return match ? match[1].trim() : null
}

function isConfigured(filePath: string, key: string, placeholder: string): boolean {
  const val = getCredential(filePath, key)
  return !!val && val !== placeholder && val.length > 0
}

function credentialsAreConfigured(filePath: string): boolean {
  return (
    isConfigured(filePath, 'AGORA_APP_ID', 'your_agora_app_id') &&
    isConfigured(filePath, 'AGORA_APP_CERTIFICATE', 'your_agora_app_certificate')
  )
}

function usesExampleCredentials(filePath: string): boolean {
  const appId = getCredential(filePath, 'AGORA_APP_ID')
  const cert = getCredential(filePath, 'AGORA_APP_CERTIFICATE')
  return appId === 'your_agora_app_id' && cert === 'your_agora_app_certificate'
}

function prepareEnv(): void {
  if (fs.existsSync(envFile)) {
    if (usesExampleCredentials(envFile) && credentialsAreConfigured(legacyEnvFile)) {
      fs.copyFileSync(legacyEnvFile, envFile)
      console.log('Copied configured server/.env.local to server/.env.')
    }
    return
  }

  if (fs.existsSync(legacyEnvFile)) {
    fs.copyFileSync(legacyEnvFile, envFile)
    console.log('Copied existing server/.env.local to server/.env.')
    return
  }

  if (fs.existsSync(exampleEnvFile)) {
    fs.copyFileSync(exampleEnvFile, envFile)
    console.log('Created server/.env from template. Add Agora credentials before running.')
  }
}

function checkEnv(): boolean {
  if (!fs.existsSync(envFile)) {
    console.error('- missing server/.env')
    return false
  }

  console.log('- server/.env present')
  let ok = true

  const checkKey = (key: string, placeholder: string) => {
    const val = getCredential(envFile, key)
    if (!val || val === placeholder) {
      console.error(`- ${key} not properly configured in server/.env`)
      ok = false
    } else {
      console.log(`- ${key} configured`)
    }
  }

  checkKey('AGORA_APP_ID', 'your_agora_app_id')
  checkKey('AGORA_APP_CERTIFICATE', 'your_agora_app_certificate')
  return ok
}

const command = process.argv[2] || 'prepare'
if (command === 'prepare') {
  prepareEnv()
} else if (command === 'check') {
  const ok = checkEnv()
  process.exit(ok ? 0 : 1)
} else if (command === 'next-steps') {
  console.log('\nSetup complete.')
  if (checkEnv()) {
    console.log('Agora credentials are configured.')
    console.log('Next step: bun run dev')
  } else {
    console.log('Next steps:')
    console.log('  1. Configure credentials in server/.env')
    console.log('  2. Run: bun run dev')
  }
} else {
  console.log(`Usage: bun run scripts/setup-env.ts [prepare|check|next-steps]`)
}
