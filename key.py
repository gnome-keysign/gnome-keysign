#!/usr/bin/env python


class KeyError(Exception):
    pass

class Key:
    @classmethod
    def is_valid_fingerprint(cls, fingerprint):
        return True

    def __init__(self, fingerprint):
        if not self.is_valid_fingerprint(fingerprint):
            raise KeyError("Fingerprint {} does not "
                           "appear to be valid".format(fingerprint))

        self.fingerprint = fingerprint
        
