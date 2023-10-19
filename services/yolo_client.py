from zero import ZeroClient

zero_client = ZeroClient("pbyolo.lan", 5559)

def get_person_count():
    return zero_client.call("get_person_count", None)

if __name__ == "__main__":
    import time
    last_ma = 0
    while True:
        next_ma = get_person_count()
        if last_ma != next_ma:
            print(next_ma)
            last_ma = next_ma
        time.sleep(1)

