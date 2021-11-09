from typing import Optional
import cbpro
import datetime
from datetime import timezone
from dateutil import tz
from dateutil.relativedelta import relativedelta
from pprint import pprint as pp
import sys
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import matplotlib.dates as mpl_dates

MAX_DATA = 300

a = cbpro.PublicClient()

def get_candles(gran: str, start, end):
    acceptedGrans = {'minute': 60, '5minutes': 300, '15minutes': 900, 'hour': 3600, '6hour': 21600, 'day': 86400}
    if gran not in acceptedGrans:
        raise ValueError(f'selected {gran!r} is not in {acceptedGrans=}')
    grans = acceptedGrans.get(gran)
    delta_time_candles = grans // 60 * MAX_DATA
    until_time = end
    from_time = start
    diff = end - start
    t_seconds = diff.total_seconds()
    req_candles = t_seconds // grans
    print(f'{diff=}\n{diff.total_seconds()=}\n{req_candles=}\n{delta_time_candles=}')
    last_stamp = end
    if req_candles > MAX_DATA:
        print(f'size is too big... adjusting from time...')
        from_time = end - relativedelta(minutes=delta_time_candles)
        last_stamp = from_time
        # print(f'{from_time=}\n{start=}')

    ll = []
    # print(f'{last_stamp=!r}\n{start=!r}')
    while last_stamp > start:
        prices = a.get_product_historic_rates('BTC-EUR',from_time,until_time,grans)
        # print(prices)
        if prices == []:
            break
        ll.append(prices)
        print(prices[1:3])
        print(len(prices))
        print(f'{prices[0]=}\t\t{datetime.datetime.fromtimestamp(prices[0][0])}\
            \n{prices[-1]=}\t\t{datetime.datetime.fromtimestamp(prices[-1][0])}')
        last_stamp = datetime.datetime.fromtimestamp(prices[-1][0])
        last_stamp = from_time.replace(tzinfo=tz.tzlocal())
        print(f'{last_stamp=}')
        # update times
        until_time = last_stamp
        remain_diff = (until_time - start)
        remain_diff = remain_diff.total_seconds()
        print(f'Remaining time is {remain_diff}')
        if remain_diff > MAX_DATA:
            from_time = until_time - relativedelta(minutes=delta_time_candles)
        else:
            from_time = end
    ll = [_x for _y in ll for _x in _y]
    print(len(ll))
    # print(ll)
    return ll
    # [ time, low, high, open, close, volume ]
    # [1636416000, 57906.6, 59114, 58278.1, 58800.83, 403.6970887]

end = datetime.datetime.now(tz = tz.tzlocal())
start = datetime.datetime.fromisoformat('2021-09-25 00:45:00')
start = start.replace(tzinfo=tz.tzlocal())
data = get_candles('6hour',start,end)
print(data[0])

plt.style.use('ggplot')

data_frame = pd.DataFrame(data,columns=['time','low', 'high', 'open', 'close', 'volume'],)
data_frame['time'] = pd.to_datetime(data_frame['time'],unit='s', origin='unix')
data_frame.index = pd.DatetimeIndex(data_frame['time'])
data_frame = data_frame[::-1]
print(data_frame)
mpf.plot(data_frame,type='candle',mav=(3,15,64))