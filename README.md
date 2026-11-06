# SERVERSERVICE CLI – All-in-One Linux Server Toolkit

Toolkit terminal interaktif (Python 3, tanpa dependensi wajib) untuk menginstal,
mengonfigurasi, dan mengelola layanan server di **Ubuntu / Debian**.

## Menjalankan

```bash
# tanpa instalasi (dari folder yang berisi direktori serverservice/)
sudo python3 -m Serverservice

# atau sebagai perintah
sudo pip install .            # opsional: pip install ".[pretty]" untuk tabel rich
sudo serverkit
```

## Fitur menu

| Menu | Fungsi |
|------|--------|
| Install | Pilih `1,4`, `1-3`, `bind9,nginx`, atau `all` -> apt install + enable + start |
| Configure | Konfigurator interaktif (BIND9, Nginx), tanpa edit file manual |
| Manage | start/stop/restart/reload/enable/disable/status/log |
| Verify | status unit, autostart, port, validasi konfigurasi (`named-checkconf`, `nginx -t`, dll.) |
| Update / Uninstall | `apt --only-upgrade` / remove atau purge (backup otomatis saat purge) |
| Server Information | OS, CPU, RAM, disk, IP, uptime |
| Network Diagnostics | interface, resolver, lookup forward/PTR, ping, cek port |
| Backup & Restore | tar.gz ke `/var/backups/serverkit` + snapshot otomatis sebelum restore |

## Konfigurator BIND9

Input: domain, IP server, prefix, nama NS, forwarders, record A tambahan.
Output otomatis:

```
/etc/bind/
├── named.conf
├── named.conf.options
├── named.conf.local
└── zones/
    ├── <domain>.db     (SOA, NS, A)
    └── reverse.db      (SOA, NS, PTR)
```

Alur: tulis file (file lama dibackup) -> `named-checkconf` + `named-checkzone` ->
bila gagal rollback otomatis -> `systemctl restart bind9` -> tes `dig`.
Serial zona naik otomatis (YYYYMMDDNN). Nilai terakhir disimpan di
`/etc/serverkit/bind9.json` sebagai default saat konfigurasi ulang.

Batasan saat ini: satu domain per server; prefix non-oktet (mis. /25) dibulatkan
ke zona reverse /24.

## Uji tanpa root / tanpa mengubah sistem

```bash
SERVERKIT_DRY_RUN=1 SERVERKIT_PREFIX=/tmp/sk python3 -m serverkit
```
Perintah sistem hanya dicetak; file konfigurasi ditulis di bawah `/tmp/sk`.

## Menambah layanan / konfigurator baru

1. Tambah `Service(...)` di `serverkit/services.py`.
2. (Opsional) buat `serverkit/configurators/<nama>.py` berisi `configure()`, lalu
   daftarkan di `serverkit/configurators/__init__.py`.
