#!/usr/bin/env python3

import logging
from pathlib import Path
import os
import sys

if  __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    import keysign
    #mod = __import__('keysign')
    #sys.modules["keysign"] = mod
    __package__ = str('keysign')


from .gpgmeh import export_uids, minimise_key

def escape_filename(fname):
    escaped = ''.join(c if c.isalnum() else "_" for c in fname)
    return escaped

def main():
    fname = sys.argv[1]
    keydata = open(fname, 'rb').read()

    minimise = True
    if minimise:
        keydata = minimise_key(keydata)

    for i, (uid, uid_bytes) in enumerate(export_uids(keydata), start=1):
        uid_file = Path('.') / ("{:02d}-".format(i) + escape_filename(uid) + ".pgp.asc")
        print (f"Writing {uid_file}...")
        uid_file.write_bytes(uid_bytes)

    print (f"Done!")

if __name__ == "__main__":
    main()
