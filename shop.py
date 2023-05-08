import random
import locale
import simpy
from termcolor import cprint
from time import sleep


SHOP_OPEN_TIME = 21*3600 
SHOP_CLOSE_TIME = 23*3600 
ANNOUNCE_CLOSE = 10*60 
CLOSE_ENTER = 60 
AVG_ENTER_TIME = 30 
AVG_BUYS_NUBMER = 5 
NUM_TERMINAL = 5 

DRAW = True # Shows graph

num_clients = 0 
clients = [] 
timestat_c = [] 
len_queue = 0
queues = []
timestat_q = [] 
goods = [] 
timestat_g = [] 
len_all_queues = 0
all_queues = []
timestat_aq = [] 

additional_time = 0 
slow_flag = False 

def enter_time():
    return random.randint(0, AVG_ENTER_TIME*2)

def buys_num(): 
    left = int(AVG_BUYS_NUBMER - AVG_BUYS_NUBMER/2)
    right = int(AVG_BUYS_NUBMER + AVG_BUYS_NUBMER/2)
    return random.randint(left, right)

def buy_time(): 
    time_per_one_buy = random.randint(3, 6) * 60 # ~3-6 minutes
    return time_per_one_buy


def pay_time():
    time_per_one_buy = random.randint(2, 8)
    return time_per_one_buy

# Get current time hh::mm::ss
def format_time(stime):
    if stime == 0:
        return "00:00:00"
    hours = int(stime / 3600) % 24
    minutes = int(stime % 3600 / 60)
    seconds = int(stime % 3600 % 60)
    if hours < 10:
        hours = "0" + str(hours)
    if minutes < 10:
        minutes = "0" + str(minutes)
    if seconds < 10:
        seconds = "0" + str(seconds)
    return str(hours) + ":" + str(minutes) + ":" + str(seconds)


# The shop
class Shop(object):
    def __init__(self, env, num_terminals):
        self.env = env
        self.num_terminals = num_terminals
        self.terminals = []
        self.queue = [] 
        self.cashier_speed = []
        for i in range(num_terminals):
            self.terminals.append(simpy.Resource(env, capacity=1))
            self.queue.append(simpy.Container(env,capacity=5000, init=0))
            self.cashier_speed.append(pay_time())

    def service(self, name, i, buys):
        global additional_time, len_all_queues
        print('%s paying his buys at %s.' % (name, format_time(self.env.now)))
        
        service_time = self.cashier_speed[i]*buys + self.cashier_speed[i]*4
        if SHOP_CLOSE_TIME - self.env.now < service_time: 
            additional_time = int(service_time*len_all_queues/NUM_TERMINAL)
        yield self.env.timeout(service_time)
        self.queue[i].get(1)
        print('%s payed his buys at %s.' % (name, format_time(self.env.now)))

    def choose_cashbox(self, name):
        min_queue = self.queue[0].level
        max_queue = self.queue[0].level
        min_index = 0
        for i in range(self.num_terminals):
            if self.queue[i].level < min_queue:
                min_queue = self.queue[i].level
                min_index = i
            if self.queue[i].level > max_queue:
                max_queue = self.queue[i].level
        self.queue[min_index].put(1)
        global timestat_q, queues
        queues.append(max_queue)
        timestat_q.append(self.env.now)
        print('%s goes to terminal %d at %s.' % (name, min_index, format_time(self.env.now)))
        return min_index


# Customer shopping
class Customer(object):
    def __init__(self, env, name, shop):
        self.env = env
        self.name = name
        self.shop = shop
        self.buys = buys_num() 
        self.time_per_buy = buy_time() 
        self.time_buy = self.buys * self.time_per_buy 
    def shopping(self):
        global clients, len_queue, queues, num_clients, goods, len_all_queues, slow_flag
        global timestat_c, timestat_g, timestat_q, timestat_aq
       
        time_before = SHOP_CLOSE_TIME - ANNOUNCE_CLOSE - self.env.now 
        if time_before < 0:
            yield self.env.timeout(SHOP_CLOSE_TIME - self.env.now)
        if time_before < self.time_per_buy*self.buys:
           
            self.time_buy = -1   
            for i in range(self.buys-1):
                if time_before > self.time_per_buy*(self.buys-i):
                    self.buys = self.buys-i
            yield self.env.timeout(SHOP_CLOSE_TIME - self.env.now)       
      
        cprint('%s enters shop at %s.' % (self.name, format_time(self.env.now)), 'green')
        num_clients += 1
        clients.append(num_clients)
        timestat_c.append(self.env.now)
        goods.append(self.buys)  
        timestat_g.append(self.env.now)
        yield self.env.timeout(self.time_buy)
        print('%s gets %d buys at %s.' % (self.name, self.buys, format_time(self.env.now)))

           
        yield self.env.timeout(10)
        choosen = self.shop.choose_cashbox(self.name)
        len_all_queues += 1
        with self.shop.terminals[choosen].request() as request:
            yield request
            yield self.env.process(self.shop.service(self.name, choosen, self.buys))
            len_all_queues -= 1
            all_queues.append(len_all_queues) 
            timestat_aq.append(self.env.now)
            cprint('%s exit the shop at %s.' % (self.name, format_time(self.env.now)),'red')
            num_clients -= 1
            clients.append(num_clients)
            timestat_c.append(self.env.now)
            if slow_flag:
                sleep(0.002)


def simmulate(env):
    shop = Shop(env, NUM_TERMINAL)
    yield env.timeout(SHOP_OPEN_TIME) 
    cprint('Shop openning at %s.' % format_time(env.now),'yellow')
    sleep(1)
    num = 0 
    time_before_close = SHOP_CLOSE_TIME - env.now
    while time_before_close > CLOSE_ENTER*60: 
        num += 1
        if env.now - SHOP_OPEN_TIME < 5*60:
            sleep(0.1)
        yield env.timeout(enter_time())
        customer = Customer(env, 'Customer %d' % num, shop)
        shopping = env.process(customer.shopping())
        time_before_close = SHOP_CLOSE_TIME - env.now

    cprint('\nThe shop enter closed!\n', 'yellow')
    sleep(2)
    global slow_flag
    slow_flag =  True
    if time_before_close - ANNOUNCE_CLOSE > 0:     
        yield env.timeout(time_before_close - ANNOUNCE_CLOSE)
    cprint('\nAnnounce: The shop closing soon!\n', 'red')
    sleep(2)

def main(): 
    cprint('Shop simulation starts:\n', 'green')
    random.seed()
  
    env = simpy.Environment()
    inside = env.process(simmulate(env))
    sleep(1)
    env.run(until=SHOP_CLOSE_TIME)
    cprint('\nNumber of clients inside after shop close: %d. Shop worked %s above the normal' % 
    (num_clients,format_time(additional_time)),'cyan')
    close_time = env.now + additional_time
    clients.append(0)
    timestat_c.append(close_time)
    queues.append(0)
    timestat_q.append(close_time)
    all_queues.append(0)
    timestat_aq.append(close_time)
    sleep(0.5)
    cprint('Shop closes at %s.' % format_time(env.now+additional_time), 'yellow')
    sleep(0.5)    
    cprint('\nShop simulation stopped.', 'red')


if __name__ == "__main__":
    main()

from pylab import *


font = {'family' : 'Normal',
        'weight' : 'normal',
        'size'   : 22}

matplotlib.rc('font', **font)

figure('Timestat queue')
plot(timestat_q, queues)
title('Queue length')
xlabel(u'Simulation time, sec')
ylabel(u'Longest queue length')

if DRAW:
    cprint('\nBuilding graphs...', 'blue')
    sleep(2)
    show()