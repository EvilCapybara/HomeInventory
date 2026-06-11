import csv
import matplotlib.pyplot as pyplot

with open('test_logs.csv', newline='', encoding='utf-8') as csvlogs:
    reader = csv.DictReader(csvlogs, delimiter=';')

    over_security_enter = {'AA': [],
                           'BB': [],
                           'CC': []
                           }
    over_security_exit = {'AA': [],
                          'BB': [],
                          'CC': []}
    PnL_plot = []
    time_plot = []
    i = 0

    for row in reader:
        # не рассматривала случаи пустых tradePx и tradeAmt, т.к. filled
        if row['action'] == 'filled':
            if row['orderSide'] == 'buy':
                current_enter = row['tradePx'] * row['tradeAmt']
                over_security_enter[row['orderProduct']].append(current_enter)
                i -= current_enter
                PnL_plot.append(i)
            elif row['orderSide'] == 'sell':
                current_exit = row['tradePx'] * row['tradeAmt']
                over_security_exit[row['orderProduct']].append(current_exit)
                i += current_exit
                PnL_plot.append(i)
            time_plot.append(row['currentTime'])


AA_enter = sum(over_security_enter['AA'])
BB_enter = sum(over_security_enter['BB'])
CC_enter = sum(over_security_enter['CC'])

AA_exit = sum(over_security_exit['AA'])
BB_exit = sum(over_security_exit['BB'])
CC_exit = sum(over_security_exit['CC'])

total_enter = sum([AA_enter, BB_enter, CC_enter])
total_exit = sum([AA_exit, BB_exit, CC_exit])


# 1 задание
PnL_abs = total_exit - total_enter
PnL_rel = (total_exit / total_enter - 1) * 100

# 2 задание
AA_PnL_abs = AA_exit - AA_enter
AA_PnL_rel = (AA_exit / AA_enter - 1) * 100

BB_PnL_abs = BB_exit - BB_enter
BB_PnL_rel = (BB_exit / BB_enter - 1) * 100

CC_PnL_abs = CC_exit - CC_enter
CC_PnL_rel = (CC_exit / CC_enter - 1) * 100

# 3 задание
x_values = time_plot
y_values = PnL_plot
pyplot.plot(x_values, y_values, marker='o', linestyle='-', color='blue')
pyplot.title('Cumulative gross PnL')
pyplot.xlabel('time')
pyplot.ylabel('current gross PnL')

pyplot.grid(True)
pyplot.show()

