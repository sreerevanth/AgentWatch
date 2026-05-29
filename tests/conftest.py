import datetime

if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc
