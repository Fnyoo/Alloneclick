"""File Sharing: Samba, NFS, vsftpd, ProFTPD."""
from .services.base import Service, ServiceCategory


class FileSharingServices(ServiceCategory):
    name = "File Sharing"

    services = (
        Service("samba", "Samba", "File Sharing", ("samba",), ("smbd", "nmbd"), 445,
                ("/etc/samba",), ("testparm", "-s"),
                description="SMB/CIFS file sharing"),
        Service("nfs", "NFS Server", "File Sharing", ("nfs-kernel-server",),
                ("nfs-server",), 2049, ("/etc/exports",),
                description="Network File System"),
        Service("vsftpd", "vsftpd", "File Sharing", ("vsftpd",), ("vsftpd",), 21,
                ("/etc/vsftpd.conf",), ("vsftpd", "-t"),
                description="FTP server ringan"),
        Service("proftpd", "ProFTPD", "File Sharing", ("proftpd-basic",),
                ("proftpd",), 21, ("/etc/proftpd",), ("proftpd", "-t"),
                ("vsftpd",), description="FTP server modular"),
    )