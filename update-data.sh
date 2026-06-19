#!/bin/bash
# Usage: DATA_PASSWORD=yourpassword ./update-data.sh
# Updates encrypted data files after changing any file in data/

set -e

if [ -z "$DATA_PASSWORD" ]; then
  echo ""
  echo "Error: DATA_PASSWORD is not set."
  echo "Usage: DATA_PASSWORD=yourpassword ./update-data.sh"
  echo ""
  exit 1
fi

echo ""
echo "Encrypting data files..."
node encrypt.js

echo "Next steps:"
echo "  git add web/data/*.enc"
echo "  git commit -m 'chore(data): update encrypted data'"
echo ""
