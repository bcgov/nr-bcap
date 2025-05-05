import os


def format_sql(file_path: str, params: dict = None) -> str:
    with open(os.path.join(os.path.dirname(__file__), "..", file_path)) as file:
        sql_string = file.read()
        return sql_string.format(**params) if params else sql_string
