# ServerKit 

**A command-line toolkit for managing common server services on Debian and Ubuntu.**

ServerKit is an early-stage Python CLI project intended to make common server administration tasks easier to inspect and perform from one interface. It includes service installation and management commands, basic system diagnostics, operation history, and BIND9 forward/reverse DNS configuration.

> **Status: Alpha / experimental.** Use on a test VM first. ServerKit can install/remove packages and change system DNS configuration when run with sufficient privileges. Review commands and back up important systems before use.

## Highlights

- Install and uninstall supported services through APT.
- Check service configuration and runtime status.
- Start, stop, restart, enable, disable, and inspect service logs.
- Preview supported operations with `--dry-run`.
- Display basic host information and run system checks.
- Record actions in a local SQLite history database.
- Generate and validate BIND9 forward and reverse DNS zones.
- Back up BIND configuration before applying DNS changes.

## Supported platforms

The current OS detector explicitly recognizes:

- Ubuntu Server 24.04 LTS
- Debian 12 (Bookworm)
- Debian 13 (Trixie)

Other APT-based distributions may work, but are not currently treated as tested platforms. Use `--force` only if you understand the risk and have a backup.

## Requirements

- Python 3.10 or newer
- Debian/Ubuntu with `apt-get` and `systemd` for system-management operations
- `sudo`/root privileges for package and system configuration changes
- Python dependencies: Typer, Rich, and Jinja2
- BIND9 utilities (`named-checkconf`, `named-checkzone`, `dig`) for DNS validation/testing

## Installation (development)

Clone the repository, then run:

```bash
git clone Alloneclick
cd serverkit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with the repository URL after creating it on GitHub.

Check the :

```bash
serverkit --help
serverkit --version
serverkit list
```

You can also run it from the repository root:

```bash
python -m serverkit --help
```

## Quick start

List available services:

```bash
serverkit list
```

Preview an installation without making system changes:

```bash
serverkit install nginx --dry-run
```

Install a service (changes the system):

```bash
sudo serverkit install nginx
```

Verify a service:

```bash
serverkit verify nginx
```

Manage a service:

```bash
sudo serverkit manage nginx status
sudo serverkit manage nginx restart
sudo serverkit manage nginx logs
```

Check host information and system health:

```bash
serverkit info
serverkit doctor
serverkit history
```

## BIND9 DNS configuration

First install BIND9:

```bash
sudo serverkit install bind9
```

Preview a DNS configuration:

```bash
sudo serverkit dns setup \
  --domain lab.lan \
  --ip 192.168.1.10 \
  --hostname ns1 \
  --network 192.168.1.0/24 \
  --record www=192.168.1.20 \
  --dry-run
```

Apply it after reviewing the generated files:

```bash
sudo serverkit dns setup \
  --domain lab.lan \
  --ip 192.168.1.10 \
  --hostname ns1 \
  --network 192.168.1.0/24 \
  --record www=192.168.1.20
```

Test DNS resolution:

```bash
serverkit dns test lab.lan
```

The DNS setup command writes BIND configuration and zone files. It attempts to create a backup under `/var/backups/serverkit` before writing. Test in a disposable VM first and verify that the configured IP belongs to the intended host/network.

## Available services

| Key | Service | Category |
|---|---|---|
| `bind9` | BIND9 DNS Server | DNS |
| `dnsmasq` | dnsmasq | DNS |
| `unbound` | Unbound | DNS |
| `nginx` | Nginx | Web |
| `apache2` | Apache HTTP Server | Web |
| `mariadb` | MariaDB Server | Database |
| `postgresql` | PostgreSQL | Database |
| `redis` | Redis | Database |
| `samba` | Samba | File sharing |

Available services and package names can vary by distribution/version. Check the package manager and service status after installation.

## Current limitations / roadmap

The interactive menu includes roadmap placeholders for some planned features. The following are **not implemented yet**:

- Network diagnostics command
- Backup and restore workflow beyond the BIND configuration backup used by DNS setup
- Configuration profiles
- General configuration management for all listed services
- Automated rollback of package upgrades/downgrades
- A complete integration test suite across all supported OS versions

The current `--dry-run` option previews mutating commands handled by the command runner; it does not guarantee that every preflight check or read-only command is skipped. Review output before applying changes.

## Development and tests

Run tests:

```bash
pytest
```

Run a linter (optional):

```bash
ruff check .
```

The included test suite is small and focuses on OS detection, package-name validation, and dry-run behavior. Passing these tests does not mean every service workflow has been tested on a real server.

## Data and logs

By default, ServerKit stores its SQLite database and log file in:

- When run as root: `/var/lib/serverkit`
- When run as a normal user: `~/.local/share/serverkit`

Override the location with `SERVERKIT_HOME`, for example:

```bash
SERVERKIT_HOME="$HOME/.local/share/serverkit-dev" serverkit history
```

## Security notes

- Do not expose administrative interfaces or database ports to untrusted networks without proper access controls.
- Review commands before running them with `sudo`.
- Use `--dry-run` and test in a virtual machine before changing a production server.
- Keep backups outside the machine when the data is important.
- The project is alpha software; unexpected behavior and incomplete workflows are possible.

## Contributing

Issues and pull requests are welcome. Please include reproduction steps, OS/version details, and relevant logs with sensitive information removed.

## License

MIT. See [LICENSE](LICENSE).
