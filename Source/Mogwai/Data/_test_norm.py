import numpy as np
from matplotlib import pyplot as plt


T = 20
A = 0.2
B = 1.0 - A


def y(i:int, b, t):
    if i == t:
        return 1.0
    if i == 0:
        return -1/b
    return 1-(1/b)


def getW(b, t):
    return (1-b**t)/(1-b)

def getW0(b, t):
    return (1-b**(t+1))/(1-b)

def getGrad(x, b):
    t = len(x)-1
    return sum([(x[i]-x[i-1])*b**(t-i) for i in range(1, len(x))]) / getW(b, t)

def getVar(x, b):
    t = len(x)
    moments = [0.0, 0.0]
    for i in range(0, len(x)):
        moments[0] += x[i] * b**(t-i)
        moments[1] += x[i]**2 * b**(t-i)
    w = getW(b, t)
    print(f'getVar: w: {w}')
    moments = [m / w for m in moments]
    return max(moments[1] - moments[0]**2, 1e-6)

def getStd(x, b):
    return np.sqrt(getVar(x, b))

_w = sum([B**(T-i) for i in range(1, T+1)])
w = getW(B, T)
print(f'_w: {_w}')
print(f'w: {w}')
assert _w == w


mean_y = (1/w) * sum([y(i,B,T) * B**(T-i) for i in range(0, T+1)])
# mean_y_direct = (1/w) * (1 - B**(T-1) + (1-1/B)*sum([B**(T-i) for i in range(1,T)])) / w
# mean_y_direct = (1/w) * (1 - B**(T-1) + (1-1/B)*sum([B**(T-i) for i in range(1,T+1)]) - (1-1/B))
# mean_y_direct = (1/w) * (1 - B**(T-1) + (1-1/B)*w - (1-1/B))
# mean_y_direct = ((1-1/B)*w - (1-1/B) + (1 - B**(T-1))) / w
# mean_y_direct = ((1-1/B)*w + 1/B - B**(T-1)) / w
# mean_y_direct = ((1-1/B)*w + (1 - B**T)/B) / w
mean_y_direct = 0.0
print(f'mean_y: {mean_y}')
print(f'mean_y_direct: {mean_y_direct}')
assert abs(mean_y - mean_y_direct) < 1e-6


ys = [y(i,B,T) for i in range(0, T+1)]
print(f'ys: {ys}')
w0 = getW0(B, T)
assert w0 == sum([B**(T-i) for i in range(0, T+1)])
_var_y = 1/w0 * sum([ys[i]**2 * B**(T-i) for i in range(0, T+1)])
# varY = lambda b,t: 1/w0 * sum([y(i,b,t)**2 * b**(t-i) for i in range(0,t+1)])
# varY = lambda b,t: 1/w0 * (1 + b**(t-2) + (1-1/b)**2 * sum([b**(t-i) for i in range(1,t)]))
# varY = lambda b,t: 1/w0 * (1 + b**(t-2) - (1-1/b)**2 * (b**t+1) + (1-1/b)**2 * w0)
# varY = lambda b,t: (1-1/b)**2 + (1 + b**(t-2) - (1-2/b+b**(-2))*(b**t+1)) / w0
# varY = lambda b,t: (1-1/b)**2 + (-b**t + 2*b**(t-1) + 2/b - b**(-2)) / w0
# varY = lambda b,t: (1-1/b)**2 + (-b**t + 2*b**(t-1) + 2/b - b**(-2)) * (1-b) / (1-b**(t+1))
# varY = lambda b,t: (1-b) * ((1-b)/b**2 + (-b**t + 2*b**(t-1) + 2/b - b**(-2)) / (1-b**(t+1)))
# varY = lambda b,t: (1-b) * ((1-b)/b**2 + 1/b - b**(-2) + (1+b**t)/(b*(1-b**(t+1))))
varY = lambda b,t: (1-b) / b * ((1+b**t)/(1-b**(t+1)))
var_y = varY(B, T)
print(f'_var_y: {_var_y}')
print(f'var_y: {var_y}')
assert abs(_var_y - var_y) < 1e-6

# plt.plot([varY(B,t) for t in range(1, 100)])

stdY = lambda b,t: np.sqrt(varY(b,t))
std_y = stdY(B, T)
print(f'std_y: {std_y}')

# x = [2.35953919, 2.40007963, 6.29489035, 0.98687189, 0.92388824, 3.35557637,
#      4.20103365, 7.00147004, 3.70622972, 2.54446704, 9.89759788]
x = np.linspace(0, 10, T+1)
g = getGrad(x, B)
print(f'x: {x}')
print(f'g: {g}')
std_x = getStd(x, B)
print(f'std(x): {std_x}')

g_div_std = g/std_x
print(f'g_div_std: {g_div_std}')

# exit()

N = 1000
w0 = getW0(B, T)
g_div_std_list = []
for n in range(N):
    b = B
    t = T
    if n%10==0:
        x = np.random.normal(5, 2, t+1)
    elif n%10==1:
        x = np.linspace(0, n, t+1)
    elif n%10==2:
        x = np.exp(np.linspace(0, 10, t+1))
    else:
        x = np.random.uniform(0, 10, t+1)
    g = sum([(x[i]-x[i-1])*B**(T-i) for i in range(1, len(x))]) / w0
    moments = [
        sum([x[i] * b**(len(x)-i) for i in range(0, len(x))]) / w0,
        sum([x[i] * x[i] * b**(len(x)-i) for i in range(0, len(x))]) / w0,
    ]
    var_x = max(moments[1] - moments[0]**2, 1e-6)
    std_x = np.sqrt(var_x)
    g_div_std = g/std_x
    # print(f'std: {std}')
    # print(f'var: {var}')
    # print(f'g_div_std: {g_div_std}')

    if abs(g_div_std) > std_y:
        print(f'x = {x}')
        break

    g_div_std_list.append(g_div_std)

plt.scatter(range(N), g_div_std_list)


plt.plot(std_y*np.ones(N), color='tab:orange')
plt.plot(-std_y*np.ones(N), color='tab:orange')

# bs = np.linspace(0.01, 1.0, 100)
# plt.plot(bs, [varY(b,100) for b in bs])



plt.show()
