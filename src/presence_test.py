from . services.presence import PresenceClient
import time

cli = PresenceClient()
last_ma = 0
while True:
    next_ma = cli("get_person_count", None)
    if last_ma != next_ma:
        print(next_ma)
        last_ma = next_ma
    time.sleep(1)
