"""Database: MariaDB, MySQL, PostgreSQL, MongoDB, Redis, SQLite."""
from .services.base import Service, ServiceCategory


class DatabaseServices(ServiceCategory):
    name = "Database"

    services = (
        Service("mariadb", "MariaDB", "Database", ("mariadb-server",),
                ("mariadb",), 3306, ("/etc/mysql",),
                description="MySQL-compatible RDBMS"),
        Service("mysql", "MySQL", "Database", ("mysql-server",), ("mysql",), 3306,
                ("/etc/mysql",), ("mysqladmin", "ping"),
                description="MySQL (butuh repo Oracle)"),
        Service("postgresql", "PostgreSQL", "Database", ("postgresql",),
                ("postgresql",), 5432, ("/etc/postgresql",),
                description="Object-relational database"),
        Service("mongodb", "MongoDB", "Database", ("mongodb-org",), ("mongod",), 27017,
                ("/etc/mongod.conf",), external_repo=True,
                description="Document database (butuh repo MongoDB)"),
        Service("redis", "Redis", "Database", ("redis-server",), ("redis-server",), 6379,
                ("/etc/redis",), ("redis-cli", "ping"),
                description="In-memory key-value store"),
        Service("sqlite", "SQLite", "Database", ("sqlite3",), (), None,
                description="Embedded SQL database (tanpa daemon)"),
    )