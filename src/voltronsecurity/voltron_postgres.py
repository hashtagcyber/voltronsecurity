import psycopg2
import logging
import os

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("voltron")
logger.setLevel(os.environ.get("APP_LOGLEVEL", logging.DEBUG))


class VoltronPostgres:
    def __init__(self, host, user, password, port, db):
        self.pg_handler = psycopg2.connect(
            database=db, user=user, password=password, port=port, host=host
        )

    def write_to_table(self, t_name, t_rows, pg_handler=None, onConflict="DO NOTHING"):
        if pg_handler is None:
            pg_handler = self.pg_handler

        if len(t_rows) == 0:
            logger.info("Received 0 rows to write")
        else:
            logger.info("Writing {} rows to {}".format(len(t_rows), t_name))
            cursor = pg_handler.cursor()
            fillers = "%s," * len(t_rows[0])
            fillers = fillers.rstrip(",")
            statement = "INSERT INTO {} VALUES ({}) ON CONFLICT {}".format(
                t_name, fillers, onConflict
            )
            cursor.executemany(statement, t_rows)
            pg_handler.commit()
            cursor.close()

    def execute_statement(self, statement, pg_handler=None):
        if pg_handler is None:
            pg_handler = self.pg_handler

        cursor = pg_handler.cursor()
        cursor.execute(statement)
        pg_handler.commit()
        cursor.close()


class VoltronDB(VoltronPostgres):
    def create_tables(self, pg_handler=None):
        if pg_handler is None:
            pg_handler = self.pg_handler

        table_statements = [
            """
            CREATE TABLE IF NOT EXISTS SNYK_ORGS (
                org_id TEXT PRIMARY KEY,
                org_payload JSONB );
            """,
            """
            CREATE TABLE IF NOT EXISTS SNYK_PROJECTS (
	            org_id TEXT,
	            project_id TEXT PRIMARY KEY,
	            project_payload JSONB);
            """,
            """
            CREATE TABLE IF NOT EXISTS SNYK_FINDINGS (
	            org_id TEXT,
	            project_id TEXT,
	            finding_id TEXT PRIMARY KEY,
	            finding_payload JSONB);
            """,
            """
            CREATE TABLE IF NOT EXISTS VOLTRON_FINDINGS (
                toolName TEXT,
                resourceType TEXT,
                resourceId TEXT,
                toolFindingId TEXT PRIMARY KEY,
                toolFindingSummary TEXT, 
                toolFindingJson JSONB,
                toolFindingURL TEXT,
                toolFindingSeverity TEXT,
                voltronSeverity TEXT,
                extractDate TIMESTAMP WITHOUT TIME ZONE,
                findingDate TIMESTAMP WITHOUT TIME ZONE
            )
            """,
        ]

        for statement in table_statements:
            self.execute_statement(statement)
