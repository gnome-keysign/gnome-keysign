#!/bin/bash -ex
# A simple helper for creating an environment for the receiver of the newly produced certification

ATTESTEE_DIR=/tmp/gks-attestee

rm -rf "${ATTESTEE_DIR}.bak"
mkdir -p $ATTESTEE_DIR
mv -f "$ATTESTEE_DIR" "${ATTESTEE_DIR}.bak"
mkdir -p $ATTESTEE_DIR
echo -n | env GNUPGHOME=${ATTESTEE_DIR}  gpg --pinentry-mode loopback --batch --no-tty --yes --passphrase-fd 0 --quick-generate-key attestee@example.com
env GNUPGHOME=${ATTESTEE_DIR}  gpg --armor --export attestee@example.com > ${ATTESTEE_DIR}/attestee.pgp.asc
echo \"GNUPGHOME=${ATTESTEE_DIR}\"   python3 -m keysign.sign_and_encrypt  ${ATTESTEE_DIR}/attestee.pgp.asc
