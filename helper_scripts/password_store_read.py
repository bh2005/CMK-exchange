#!/usr/bin/env python3

from cmk.utils import password_store
from sys import argv

pw = password_store.lookup(
    pw_id=argv[1],
    pw_file=password_store.password_store_path()
)

print(pw)