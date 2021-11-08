from typing import Optional
import cbpro
import datetime
from datetime import timezone
from dateutil import tz
from dateutil.relativedelta import relativedelta
from pprint import pprint as pp
import sys

a = cbpro.PublicClient()

def get_candles(gran: str, start, end):
    acceptedGrans = {'minute': 60, '5minutes': 300, '15minutes': 900, 'hour': 3600, '6hour': 21600, 'day': 86400}
    if gran not in acceptedGrans:
        raise ValueError(f'selected {gran!r} is not in {acceptedGrans=}')
    grans = acceptedGrans.get(gran)
    max_candles = grans // 60 * 300
    until_time = end
    from_time = start
    diff = end - start
    t_seconds = diff.total_seconds()
    req_candles = t_seconds // grans
    # print(f'{diff=}\n{diff.total_seconds()=}\n{req_candles=}')
    last_stamp = end
    if req_candles > max_candles:
        print(f'size is too big... adjusting from time...')
        from_time = end - relativedelta(minutes=max_candles)
        last_stamp = from_time
        # from_time = from_time.replace(tzinfo=tz.tzlocal())
        print(f'{from_time=}\n{start=}')

    ll = []
    print(f'{last_stamp=!r}\n{start=!r}')
    while last_stamp > start:
        # print(f'target date {end!r}\nstarting {from_time=} {until_time=}')
        prices = a.get_product_historic_rates('ADA-EUR',from_time,until_time,grans)
        # print(prices)
        ll.append(prices)
        # print(prices[1:10])
        print(len(prices))
        print(f'{prices[0]=}\t\t{datetime.datetime.fromtimestamp(prices[0][0])}\
            \n{prices[-1]=}\t\t{datetime.datetime.fromtimestamp(prices[-1][0])}')
        last_stamp = datetime.datetime.fromtimestamp(prices[-1][0])
        last_stamp = from_time.replace(tzinfo=tz.tzlocal())
        print(f'{last_stamp=}')
        # update times
        until_time = last_stamp
        # until_time = until_time.replace(tzinfo=tz.tzlocal())
        remain_diff = (until_time - start)
        remain_diff = remain_diff.total_seconds()
        if remain_diff > max_candles:
            from_time = until_time - relativedelta(minutes=max_candles)
            # from_time = from_time.replace(tzinfo=tz.tzlocal())
        else:
            from_time = end
    ll = [_x for _y in ll for _x in _y]
    print(len(ll))
    print(ll)

end = datetime.datetime.now(tz = tz.tzlocal())
start = datetime.datetime.fromisoformat('2021-11-08 13:15:00')
start = start.replace(tzinfo=tz.tzlocal())
get_candles('minute',start,end)
