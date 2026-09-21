# nvram binary patcher

simple nvram binary patcher with a text config file.
can be used with [UEFI Editor](https://github.com/BoringBoredom/UEFI-Editor)

## usage

```console
python nvram_patcher.py NVRAM.bin nvram.cfg -o patched.bin
```

an example config is in [nvram.cfg](nvram.cfg)

config structure is: `varoffset value size varstorename`, comments allowed with # symbol.
offset and value are hex, size is decimal, writes are little endian.

pass -d to dry check without writing.
