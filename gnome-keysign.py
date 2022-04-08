#!/usr/bin/env python3

import logging, os, sys, signal
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format='%(name)s (%(levelname)s): %(message)s')

thisdir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, thisdir)
sys.path.insert(0, os.sep.join((thisdir, 'monkeysign')))

from keysign import main

sys.exit(main())

