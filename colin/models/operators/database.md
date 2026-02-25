---
name: Database Operator Mappings
colin:
  output:
    format: json
---

{% section PostgresOperator %}
## operator
PostgresOperator

## module
airflow.providers.postgres.operators.postgres

## source_context
Executes SQL against a PostgreSQL database using psycopg2. Supports parameterized queries.

## prefect_pattern
SqlAlchemyConnector query execution

## prefect_package
prefect-sqlalchemy

## prefect_import
from prefect_sqlalchemy import SqlAlchemyConnector

## example
### before
```python
query = PostgresOperator(
    task_id="create_table",
    postgres_conn_id="postgres_default",
    sql="CREATE TABLE IF NOT EXISTS results (id SERIAL, value TEXT)",
)
```
### after
```python
from prefect_sqlalchemy import SqlAlchemyConnector
from sqlalchemy import text

@task
def create_table():
    connector = SqlAlchemyConnector.load("postgres-default")
    with connector.get_connection() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS results (id SERIAL, value TEXT)"))
```
{% endsection %}

{% section MySqlOperator %}
## operator
MySqlOperator

## module
airflow.providers.mysql.operators.mysql

## source_context
Executes SQL against a MySQL database.

## prefect_pattern
SqlAlchemyConnector with MySQL driver

## prefect_package
prefect-sqlalchemy

## prefect_import
from prefect_sqlalchemy import SqlAlchemyConnector

## example
### before
```python
query = MySqlOperator(
    task_id="insert_data",
    mysql_conn_id="mysql_default",
    sql="INSERT INTO logs (message) VALUES ('pipeline complete')",
)
```
### after
```python
from prefect_sqlalchemy import SqlAlchemyConnector
from sqlalchemy import text

@task
def insert_data():
    connector = SqlAlchemyConnector.load("mysql-default")
    with connector.get_connection() as conn:
        conn.execute(text("INSERT INTO logs (message) VALUES ('pipeline complete')"))
```
{% endsection %}

{% section MsSqlOperator %}
## operator
MsSqlOperator

## module
airflow.providers.microsoft.mssql.operators.mssql

## source_context
Executes SQL against Microsoft SQL Server.

## prefect_pattern
SqlAlchemyConnector with MSSQL driver

## prefect_package
prefect-sqlalchemy

## prefect_import
from prefect_sqlalchemy import SqlAlchemyConnector

## example
### before
```python
query = MsSqlOperator(
    task_id="run_sproc",
    mssql_conn_id="mssql_default",
    sql="EXEC dbo.my_procedure @param1='value'",
)
```
### after
```python
from prefect_sqlalchemy import SqlAlchemyConnector
from sqlalchemy import text

@task
def run_sproc():
    connector = SqlAlchemyConnector.load("mssql-default")
    with connector.get_connection() as conn:
        conn.execute(text("EXEC dbo.my_procedure @param1='value'"))
```
{% endsection %}

{% section SQLExecuteQueryOperator %}
## operator
SQLExecuteQueryOperator

## module
airflow.providers.common.sql.operators.sql

## source_context
Generic SQL execution operator that works with any DB via hook. Replaces deprecated operator-specific SQL operators.

## prefect_pattern
SqlAlchemyConnector with appropriate driver

## prefect_package
prefect-sqlalchemy

## prefect_import
from prefect_sqlalchemy import SqlAlchemyConnector

## example
### before
```python
query = SQLExecuteQueryOperator(
    task_id="run_query",
    conn_id="my_database",
    sql="SELECT COUNT(*) FROM events WHERE date = '{{ ds }}'",
)
```
### after
```python
from prefect_sqlalchemy import SqlAlchemyConnector
from sqlalchemy import text

@task
def run_query(date: str):
    connector = SqlAlchemyConnector.load("my-database")
    with connector.get_connection() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM events WHERE date = :d"), {"d": date})
        return result.scalar()
```

## notes
- Jinja templates in SQL must be replaced with parameterized queries
- conn_id maps to the block name
{% endsection %}

{% section SnowflakeOperator %}
## operator
SnowflakeOperator

## module
airflow.providers.snowflake.operators.snowflake

## source_context
Executes SQL on Snowflake. Uses snowflake-connector-python.

## prefect_pattern
SnowflakeConnector query execution

## prefect_package
prefect-snowflake

## prefect_import
from prefect_snowflake import SnowflakeConnector

## example
### before
```python
query = SnowflakeOperator(
    task_id="snowflake_query",
    snowflake_conn_id="snowflake_default",
    sql="COPY INTO my_table FROM @my_stage",
    warehouse="compute_wh",
)
```
### after
```python
from prefect_snowflake import SnowflakeConnector

@task
def snowflake_query(sql: str):
    connector = SnowflakeConnector.load("snowflake-default")
    connector.execute(sql)
```
{% endsection %}

{% section SqliteOperator %}
## operator
SqliteOperator

## module
airflow.providers.sqlite.operators.sqlite

## source_context
Executes SQL against a SQLite database.

## prefect_pattern
sqlite3 standard library or SqlAlchemyConnector

## prefect_package
prefect (core)

## prefect_import
import sqlite3

## example
### before
```python
query = SqliteOperator(
    task_id="query_local",
    sqlite_conn_id="sqlite_default",
    sql="SELECT * FROM metadata",
)
```
### after
```python
import sqlite3

@task
def query_local(db_path: str, sql: str):
    conn = sqlite3.connect(db_path)
    result = conn.execute(sql).fetchall()
    conn.close()
    return result
```
{% endsection %}
