import asyncio

from src import reports, services, views

if __name__ == "__main__":
    datetime_str = "2021-11-23 12:53:01"
    json_main = asyncio.run(views.main(datetime_str))
    json_events = asyncio.run(views.events(datetime_str, "W"))
    print(json_main)
    print(json_events)

if __name__ == "__main__":
    services.services()

if __name__ == "__main__":
    reports.reports()
