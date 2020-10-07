#!/bin/bash -ex
# A simple helper for creating an environment for the producer of a certification

ATTESTOR_DIR=/tmp/gks-attestor

rm -rf "${ATTESTOR_DIR}.bak"
mkdir -p $ATTESTOR_DIR
mv -f "$ATTESTOR_DIR" "${ATTESTOR_DIR}.bak"
mkdir -p $ATTESTOR_DIR
echo -n | env GNUPGHOME=${ATTESTOR_DIR}  gpg --pinentry-mode loopback --batch --no-tty --yes --passphrase-fd 0 --quick-generate-key attestor@example.com
env GNUPGHOME=${ATTESTOR_DIR}  gpg --armor --export attestor@example.com > ${ATTESTOR_DIR}/attestor.pgp.asc

echo env \"GNUPGHOME=${ATTESTOR_DIR}\" python3 -m keysign.sign_and_encrypt  ATTESTEE_DIR/attestee.pgp.asc
