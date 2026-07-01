#!/usr/bin/env python3
# Checkmk password store reader
# CMK 2.4: cmk.utils.password_store.lookup(pw_id, pw_file)
# CMK 2.5: API unverändert, aber Pfad kann abweichen – bei Fehlern
#          "cmk --debug -vvn <host>" zur Diagnose nutzen

from cmk.utils import password_store
from sys import argv

pw = password_store.lookup(
    pw_id=argv[1],
    pw_file=password_store.password_store_path()
)

print(pw)