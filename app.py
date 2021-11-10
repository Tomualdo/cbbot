import json
import numpy as np
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
import dateutil.parser
from matplotlib.widgets import Slider, Button, RadioButtons


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

def buy_procedure(i,data,buys,buy_signal,sell_signal,money,value):
    buy_signal.append(data['close'][i])
    sell_signal.append(np.nan)
    coins = (money/data['close'][i])
    fee = (money*0.005)
    value = value + money
    time = str(data.index[i])
    buys[time].append({'buy_time':time,
                        'buy_price':data['close'][i],
                        'spend_EUR':money,
                        'coins': coins,
                        'fee': fee,
                        'sell_flag' : False,
                        'sell_price': 0,
                        'sell_time' : 0,
                        'earn':0})

def strategy(data, strategy_data):
    buy_signal = []
    sell_signal = []
    buys = {}
    buys_not_empty_records = []
    sells_not_empty_record = []
    # money for one buy
    money = 50
    value = 0
    coins = 0
    fee = 0
    earn = 0
    # limits
    min_market_funds = strategy_data['min_market_funds']
    max_buys = strategy_data['max_buys']
    sell_ratio = strategy_data['sell_ratio']
    ############################################ CUSTOM FRAME ##########################################
    # CUSTOM
    max_buys = 50
    
    for i in range(len(data['close'])): # MAIN LOOP
        sell_out_of_bounds = False
        # check actual active buys
        buys_qty = 0
        if buys_not_empty_records != []:
            for idx in range(len(buys_not_empty_records)):
                if buys[buys_not_empty_records[idx]][0]['sell_flag'] == False:
                    buys_qty += 1

        #test:
        for idx in range(len(buys.keys())):
                #check if the buys time index is not empty and have some data
                    if buys[list(buys.keys())[idx]] != []:            
                        #prepare list of keys where are suitable sell prices
                        #also check if it is not already in the list
                        if list(buys.keys())[idx] not in sells_not_empty_record and buys[list(buys.keys())[idx]][0]['sell_flag']==False:
                            sells_not_empty_record.append(list(buys.keys())[idx])
        for idx in sells_not_empty_record:
            sell_price_ratio = 1.05
            actual_sell_price = data['close'][i]
            if not buys[idx][0]['sell_flag'] and actual_sell_price / buys[idx][0]['buy_price'] >= sell_price_ratio:
                sell_out_of_bounds = True

        #SELL-------------------------------------------------------------------------------------------------
        if data['close'][i] > data['upper'][i] or sell_out_of_bounds: 
            # if str(data.index[i]) not in buys:
            #   buys[str(data.index[i])] = []
            #look if there are some records in buys dict
            if len(buys.keys())>=1:
                #loop over buys to        
                for idx in range(len(buys.keys())):
                #check if the buys time index is not empty and have some data
                    if buys[list(buys.keys())[idx]] != []:            
                        #prepare list of keys where are suitable sell prices
                        #also check if it is not already in the list
                        if list(buys.keys())[idx] not in sells_not_empty_record and buys[list(buys.keys())[idx]][0]['sell_flag']==False:
                            sells_not_empty_record.append(list(buys.keys())[idx])

                #after filling sells_not_empty_record list
                #loop over sells_not_empty_record
                #check BUYS dict and change sell_price to actual_sell price and remove buy_price to 0
                sell_flag = False
                for idx in sells_not_empty_record:
                    sell_price_ratio = sell_ratio
                    actual_sell_price = data['close'][i]

                    #search for sell_flag False nad lowest buy price !!! minimum sell ratio (sell for 6 buy for 5: 6/5=1.2 ratio)    
                    if not buys[idx][0]['sell_flag'] and actual_sell_price / buys[idx][0]['buy_price'] >= 1.02:
                        # earn = ((coins * data['close'][i]) - fee) - value
                        earnValue = buys[idx][0]['earn']
                        earnValue = earnValue + buys[idx][0]['coins'] * data['close'][i] - buys[idx][0]['fee'] - buys[idx][0]['spend_EUR']
                        buys[idx][0]['sell_flag'] = True  
                        buys[idx][0]['sell_price'] = data['close'][i]
                        buys[idx][0]['sell_time'] = str(data.index[i])
                        buys[idx][0]['earn'] = earnValue
                        earn = earn + earnValue
                        # buys[idx][0]['buy_price'] = 0
                        # buys[idx][0]['sell_time'] = buys[idx]
                        #generate sell signlas if sells_not_empty_record is not empty
                        sell_flag = True

                if sell_flag:
                    buy_signal.append(np.nan)
                    sell_signal.append(data['close'][i])
                else:
                    buy_signal.append(np.nan)
                    sell_signal.append(np.nan)

            #modify 
            else:
                buy_signal.append(np.nan)
                sell_signal.append(np.nan)

        #BUY--------------------------------------------------------------------------------------------------
        elif data['close'][i] < data['lower'][i] and buys_qty < max_buys and data['close'][i] < data['AVG'][i]*1.005:
            # check if there is not at leas 1x buy keys --> else buy
            if len(buys.keys()) >= 1:
                # create new key
                buys[str(data.index[i])] = [] 
                # NOW lets decide if we need to buy again !!
                # loop over non empty buys       
                for idx in range(len(buys.keys())):
                    if buys[list(buys.keys())[idx]] != []: 
                        # lets track non empty buys time indexes
                        # check if there it is not already in the list !!!
                        if list(buys.keys())[idx] not in buys_not_empty_records:
                            buys_not_empty_records.append(list(buys.keys())[idx])

                # lets process our buys_not_empty_records LIST - decide if we have to buy again
                # check last buy time
                last_buy_time = dateutil.parser.parse(str(buys_not_empty_records[-1])).timestamp()
                # check now buy time
                now_buy_time = dateutil.parser.parse(str(data.index[i])).timestamp()
                diff = int(now_buy_time) - int(last_buy_time)
                set_minimum_buy_time = 60*60*2
                #if time differnce is too small ---> we will not buy
                if diff < set_minimum_buy_time:
                    #only if price is better then set ratio :)
                    buy_ratio = 1.008
                    last_buy_price = buys[buys_not_empty_records[-1]][0]['buy_price']
                    now_buy_price = data['close'][i]
                    if last_buy_price / now_buy_price > buy_ratio:                        
                        buy_procedure(i,data,buys,buy_signal,sell_signal,money,value)
                    else:      
                        buy_signal.append(np.nan)
                        sell_signal.append(np.nan)
                        # if time is bigger then set ---> we can buy
                else:
                    # if time is longer than minimum buy time -> consider before price and actual price
                    # if last buy price is higher then dont buy + set MAX time to not buy !
                    buy_ratio = 1.008
                    last_buy_price = buys[buys_not_empty_records[-1]][0]['buy_price']
                    now_buy_price = data['close'][i]
                    # during this time DONT buy if price is higher than last time
                    if last_buy_price / now_buy_price < 1.008 and diff < set_minimum_buy_time+(60*60*8):
                        buy_signal.append(np.nan)
                        sell_signal.append(np.nan)           
                    else:
                        buy_procedure(i,data,buys,buy_signal,sell_signal,money,value)

            # DONT BUY ANYMORE AFTER 1.ST BUY        
            else:
                #create FIRST buys time key
                buys[str(data.index[i])] = [] 
                coins = (money/data['close'][i])
                fee = (money*0.005)
                # value = value + money
                time = str(data.index[i])
                buys[time].append({'buy_time':time, 'buy_price':data['close'][i],'spend_EUR':money, 'coins': coins, 'fee': fee, 'sell_flag' : False, 'sell_price': 0,'sell_time' : 0,'earn':0})

                # buy signal to list for graph      
                buy_signal.append(data['close'][i])
                sell_signal.append(np.nan)

                # FINAL statement where non of the lower/upper limit match
        else:
            sell_signal.append(np.nan)
            buy_signal.append(np.nan)

    return(buy_signal,sell_signal,earn,buys,value,coins,fee)

end = datetime.datetime.now(tz = tz.tzlocal())
start = datetime.datetime.fromisoformat('2021-03-25 00:45:00')
start = start.replace(tzinfo=tz.tzlocal())
data = get_candles('6hour',start,end)

print(data[0])

plt.style.use('ggplot')

data_frame = pd.DataFrame(data,columns=['time','low', 'high', 'open', 'close', 'volume'],)
data_frame['time'] = pd.to_datetime(data_frame['time'],unit='s', origin='unix')
data_frame.index = pd.DatetimeIndex(data_frame['time'])
data_frame = data_frame[::-1]
print(data_frame)

with open('data.json','w') as file:
    data_frame.to_json(file,indent=4,orient='records')

strategy_data = {
    "strategy_lower_bolling_lvl": 2.5,
    "strategy_upper_bolling_lvl": 2.0,
    "strategy_STD": 23,
    "strategy_SMA": 41,
    "min_market_funds": 1.0,
    "max_buys": 0,
    "base_min_size": 1,
    "sell_ratio": 1.015,
    "out_of_bound_sell_ratio": 1.016,
    "min_buy_time_minutes": 360,
    "max_time_better_price": 700,
    "min_buy_time_buy_ratio": 1.09,
    "min_ballance_buy": 60,
    "EUR_to_buy_size": 40,
    "forced_buy": False,
    "forced_sell": False,
    "ooa_buy_size_ratio": 0.6,
    "ooa_max_buys": 0,
    "ooa_sell_ratio": 1.014,
    "ooa_out_of_bound_sell_ratio": 1.015,
    "ooa_min_buy_time_minutes": 760,
    "ooa_max_time_better_price": 600,
    "ooa_min_buy_time_buy_ratio": 1.09
}

strategy_SMA = strategy_data['strategy_SMA']
strategy_STD = strategy_data['strategy_STD']
strategy_upper_bolling_lvl = strategy_data['strategy_upper_bolling_lvl']
strategy_lower_bolling_lvl = strategy_data['strategy_lower_bolling_lvl']
min_market_funds = strategy_data['min_market_funds']
max_buys = strategy_data['max_buys']
current_product= 'BTC-EUR'

f = data_frame
f['SMA'] = f['close'].rolling(window=strategy_SMA).mean()
f['STD'] = f['close'].rolling(window=strategy_STD).std()
# f['AVG'] = [np.mean(f['close'])]*len(f['close']) # all data average
f['AVG'] = f['close'].expanding(min_periods=4).mean() # cumulative AVERAGE
# f['AVG'] = f['close'].rolling(window=len(f['close'])).mean()
# f['EMA'] = f['close'].ewm(halflife=20, adjust=True).mean()
# f['EMA'] = f.iloc[:,0].ewm(span=140, adjust=False).mean()
#calculate upper bollinger band
f['upper'] = f['SMA'] + (f['STD'] *strategy_upper_bolling_lvl)
#calculate lower bollinger band
f['lower'] = f['SMA'] - (f['STD'] *strategy_lower_bolling_lvl)
# period = max(strategy_SMA,strategy_STD)
# new_df = f[period-1:]
new_df = f

#create new df wit buy sell signals
strategy_return = strategy(new_df,strategy_data)
new_df['buy'] = strategy_return[0]
new_df['sell'] = strategy_return[1]
earn = strategy_return[2]

#analyze buys - clean empty records
clean_buys = {}
buys = strategy_return[3]
for record in buys:
      if not buys[record]==[]:
            clean_buys[record]=buys[record]
# check remained buys 
remain_spend_EUR = 0
for rec in clean_buys:
      if not clean_buys[rec][0]['sell_flag']:
            remain_spend_EUR = remain_spend_EUR + clean_buys[rec][0]['spend_EUR']

#adding shade to gpraph
fig = plt.figure(figsize=(18,9))
#add the sub plot
ax = fig.add_subplot(111)

plt.subplots_adjust(left=0.07, bottom=0.4, top=0.96)
#get values from data frame
x_axis = new_df.index
#plot shade area between low and up
l = ax.fill_between(x_axis,new_df['upper'],new_df['lower'],color='silver')
ax.plot(x_axis,new_df['close'],color='magenta',lw=2.5,label='close value')
ax.plot(x_axis,new_df['SMA'],color='blue',lw=1.5,label='SMA')
# Calculate the simple average of the data
y_mean = [np.mean(new_df['close'])]*len(new_df['close'])
# ax.plot(x_axis,y_mean,color='red',lw=1.5,label='AVG',linestyle='--')
ax.plot(x_axis,new_df['AVG'],color='red',lw=1.5,label='CUM-AVG')
# ax.plot(x_axis,new_df['EMA'],color='gold',lw=1.5,label='EMA')
if len(new_df[new_df['buy'].notnull()])>0: #dont draw if there is no buy values - also rises error
    ax.scatter(x_axis,new_df['buy'],color='green',lw=3,label='buy',marker='^',zorder=5)
    # marker label at data point
    for i, txt in enumerate(new_df['buy']):
        ax.annotate(txt, (x_axis[i], new_df['buy'][i]),textcoords="offset points",xytext=(0,10),ha='left',alpha=0.75)
        ax.annotate(str(new_df.index[i]), (x_axis[i], new_df['buy'][i]),alpha=0.75) #time annotate
if len(new_df[new_df['sell'].notnull()])>0:#dont draw if there is no sell values - also rises error
    ax.scatter(x_axis,new_df['sell'],color='red',lw=3,label='sell',marker='v',zorder=5)
    # marker label at data point
    for i, txt in enumerate(new_df['sell']):
        ax.annotate(txt, (x_axis[i], new_df['sell'][i]),textcoords="offset points",xytext=(0,10),ha='left',alpha=0.75)
        ax.annotate(str(new_df.index[i]), (x_axis[i], new_df['sell'][i]),alpha=0.75) #time annotate
# plt.xticks(rotation = 45)
ax.set_title(current_product+" "+str(earn)+" "+str(remain_spend_EUR))
# ax.set_xlabel('time')
ax.set_ylabel('value')
ax.legend()
# anim = animation.FuncAnimation(fig, update, interval=10)

#test sliders
axsl1 = plt.axes([0.25, 0.0, 0.65, 0.03], facecolor='lightgoldenrodyellow')
axsl2 = plt.axes([0.25, 0.05, 0.65, 0.03], facecolor='lightgoldenrodyellow')
axsl3 = plt.axes([0.25, 0.10, 0.65, 0.03], facecolor='lightgoldenrodyellow')
#upper / lower
axsl4 = plt.axes([0.25, 0.15, 0.65, 0.03], facecolor='lightgoldenrodyellow')
axsl5 = plt.axes([0.25, 0.20, 0.65, 0.03], facecolor='lightgoldenrodyellow')

#slider values
sl1 = Slider(axsl1, 'sl1', 0.1, 1,) #, valstep=delta_f)
sl2 = Slider(axsl2, 'SMA', 1, 80,valstep=1, valinit=strategy_SMA)
sl3 = Slider(axsl3, 'STD', 1, 80,valstep=1, valinit=strategy_STD)
sl4 = Slider(axsl4, 'upper bollinger', 0.1, 5, valinit=strategy_upper_bolling_lvl)
sl5 = Slider(axsl5, 'lower bollinger', 0.1, 5, valinit=strategy_lower_bolling_lvl)

def get_sl1_val(val):
    # return math.exp(val)       # replace with a meaningful transformation of your parameters
    return val

def get_sl2_val(val):
    # return math.log(val)
    return val

def update(val):
    current_product = 'BTC-EUR'
    ax.cla() #clear axes
    s1 = get_sl1_val(sl1.val)      # call a transform on the slider value
    s2 = get_sl2_val(sl2.val)
    s3 = get_sl2_val(sl3.val)
    s4 = get_sl2_val(sl4.val)
    s5 = get_sl2_val(sl5.val)

    l.set_alpha(s1)
    
    new_df['SMA'] = f['close'].rolling(window=int(s2)).mean()
    new_df['STD'] = f['close'].rolling(window=int(s3)).std()
    # new_df['AVG'] = f['close'].rolling(window=len(f['close'])).mean()

    #calculate upper bollinger band
    new_df['upper'] = new_df['SMA'] + (new_df['STD'] *s4)
    #calculate lower bollinger band
    new_df['lower'] = new_df['SMA'] - (new_df['STD'] *s5)


    ax.plot(x_axis,new_df['SMA'],color='red',lw=1.5,label='SMA',zorder=0)
    ax.fill_between(x_axis,new_df['upper'],new_df['lower'],color='green')

    #create new df wit buy sell signals
    strategy_return = strategy(new_df,strategy_data)
    new_df['buy'] = strategy_return[0]
    new_df['sell'] = strategy_return[1]
    earn = strategy_return[2]
    #analyze buys
    clean_buys = {}
    buys = strategy_return[3]
    for record in buys:
          if not buys[record]==[]:
                clean_buys[record]=buys[record]

    remain_spend_EUR = 0
    for rec in clean_buys:
      if not clean_buys[rec][0]['sell_flag']:
            remain_spend_EUR = remain_spend_EUR + clean_buys[rec][0]['spend_EUR']

    #dump to file
    # with open('buys.json','w') as json_dump_file: 
    #   json.dump(clean_buys, json_dump_file, indent=4)

    #REGEN ALL AXES:------------------------------------------------------------
    ax.fill_between(x_axis,new_df['upper'],new_df['lower'],color='silver')
    ax.plot(x_axis,new_df['close'],color='magenta',lw=2.5,label='close value')
    ax.plot(x_axis,new_df['SMA'],color='blue',lw=1.5,label='SMA')
    # ax.plot(x_axis,y_mean,color='red',lw=1.5,label='AVG',linestyle='--')
    ax.plot(x_axis,new_df['AVG'],color='red',lw=1.5,label='CUM-AVG')
    if len(new_df[new_df['buy'].notnull()])>0: #dont draw if there is no buy values - also rises error
        ax.scatter(x_axis,new_df['buy'],color='green',lw=3,label='buy',marker='^',zorder=5)
        # marker label at data point
        for i, txt in enumerate(new_df['buy']):
            ax.annotate(txt, (x_axis[i], new_df['buy'][i]),textcoords="offset points",xytext=(0,10),ha='left',alpha=0.75)
            ax.annotate(str(new_df.index[i]), (x_axis[i], new_df['buy'][i]),alpha=0.75) #time annotate
    if len(new_df[new_df['sell'].notnull()])>0:#dont draw if there is no sell values - also rises error
        ax.scatter(x_axis,new_df['sell'],color='red',lw=3,label='sell',marker='v',zorder=5)
        # marker label at data point
        for i, txt in enumerate(new_df['sell']):
            ax.annotate(txt, (x_axis[i], new_df['sell'][i]),textcoords="offset points",xytext=(0,10),ha='left',alpha=0.75)
            ax.annotate(str(new_df.index[i]), (x_axis[i], new_df['sell'][i]),alpha=0.75) #time annotate
    # plt.xticks(rotation = 45)
    ax.set_title(current_product+" "+str(earn)+" "+str(remain_spend_EUR))
    # ax.set_xlabel('time')
    ax.set_ylabel('value')
    ax.legend()
    # anim = animation.FuncAnimation(fig, update, interval=10)

    #test sliders
    axsl1 = plt.axes([0.25, 0.0, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    axsl2 = plt.axes([0.25, 0.05, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    axsl3 = plt.axes([0.25, 0.10, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    #upper / lower
    axsl4 = plt.axes([0.25, 0.15, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    axsl5 = plt.axes([0.25, 0.20, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    #------------------------------------------------------------------------------

    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    

sl1.on_changed(update)
sl2.on_changed(update)
sl3.on_changed(update)
sl4.on_changed(update)
sl5.on_changed(update)

# plt.ion()

### SAVE FIG PIC ***
# picture_file = datetime.now().strftime("%Y%m%d%H%M%S")
# check if folder exist
# product_folder = ROOT_DIR+'/'+current_product
# if not os.path.isdir(product_folder):
#     os.makedirs(product_folder)
# plt.savefig(product_folder+'/'+current_product+picture_file+'.png')

plt.show()

# mpf.plot(data_frame,type='candle',mav=(3,15,64),)
