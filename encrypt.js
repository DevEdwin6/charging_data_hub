#!/usr/bin/env node
/**
 * Encrypts data/*.js → web/data/*.enc
 *
 * Output format per file: [salt(16) | iv(12) | ciphertext | authTag(16)]  base64
 *
 * Usage:
 *   DATA_PASSWORD=yourpassword node encrypt.js
 */
const crypto = require('crypto');
const fs     = require('fs');
const path   = require('path');

const PASSWORD = process.env.DATA_PASSWORD;
if (!PASSWORD) {
  console.error('\nError: DATA_PASSWORD environment variable is required.');
  console.error('Usage: DATA_PASSWORD=yourpassword node encrypt.js\n');
  process.exit(1);
}

const SRC_DIR = path.join(__dirname, 'data');
const OUT_DIR = path.join(__dirname, 'web', 'data');
const FILES   = ['ptt.js', 'pea.js', 'spark.js', 'igreen.js'];
const ITER    = 100_000;

fs.mkdirSync(OUT_DIR, { recursive: true });

let ok = 0;
FILES.forEach(file => {
  const src = path.join(SRC_DIR, file);
  if (!fs.existsSync(src)) {
    console.log(`  skip  ${file} (not found in data/)`);
    return;
  }

  // Extract JS array from  window.XXX_DATA = [...];
  // Keys may be unquoted (JS object literal), so evaluate via Function then re-serialize as JSON.
  const js    = fs.readFileSync(src, 'utf8');
  const match = js.match(/=\s*(\[[\s\S]*\])\s*;?\s*$/);
  if (!match) {
    console.error(`  error ${file}: could not parse JS array`);
    return;
  }

  let parsed;
  try {
    parsed = new Function('return ' + match[1])();
  } catch (e) {
    console.error(`  error ${file}: could not evaluate JS array — ${e.message}`);
    return;
  }
  const plaintext = Buffer.from(JSON.stringify(parsed), 'utf8');
  const salt      = crypto.randomBytes(16);
  const iv        = crypto.randomBytes(12);
  const key       = crypto.pbkdf2Sync(PASSWORD, salt, ITER, 32, 'sha256');

  const cipher    = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ctBuf     = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const authTag   = cipher.getAuthTag(); // 16 bytes

  // Web Crypto expects ciphertext || authTag at the end
  const output = Buffer.concat([salt, iv, ctBuf, authTag]);

  const outPath = path.join(OUT_DIR, file.replace('.js', '.enc'));
  fs.writeFileSync(outPath, output.toString('base64'));

  const kb = (output.length / 1024).toFixed(1);
  console.log(`  ✓  ${file.padEnd(12)} → web/data/${path.basename(outPath)}  (${kb} KB)`);
  ok++;
});

console.log(`\nDone: ${ok}/${FILES.length} files encrypted.\n`);
