import datetime

UNKNOWN_DATE = datetime.datetime.strptime(
    "20/04/1969 16:20:00", "%d/%m/%Y %H:%M:%S"
).isoformat()