"""Mail: Postfix, Dovecot, Exim4, Rspamd, Roundcube."""
from .base import Service, ServiceCategory


class MailServices(ServiceCategory):
    name = "Mail"

    services = (
        Service("postfix", "Postfix", "Mail", ("postfix", "mailutils"),
                ("postfix",), 25, ("/etc/postfix",), ("postfix", "check"),
                description="MTA klasik"),
        Service("dovecot", "Dovecot", "Mail",
                ("dovecot-core", "dovecot-imapd", "dovecot-pop3d"),
                ("dovecot",), 143, ("/etc/dovecot",), ("doveconf", "-n"),
                description="IMAP/POP3 server"),
        Service("exim4", "Exim4", "Mail", ("exim4",), ("exim4",), 25,
                ("/etc/exim4",), ("exim4", "--test"), ("postfix",),
                description="MTA alternatif"),
        Service("rspamd", "Rspamd", "Mail", ("rspamd",), ("rspamd",), 11334,
                ("/etc/rspamd",), ("rspamadm", "configtest"), external_repo=True,
                description="Spam filtering"),
        Service("roundcube", "Roundcube", "Mail", ("roundcube",), ("roundcube",), 80,
                ("/etc/roundcube",), external_repo=True,
                description="Webmail client"),
    )