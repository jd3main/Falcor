from matplotlib import pyplot as plt


# resolution, time(u), time(t)
times = {
    "1280x720": [1280*720, 1.336, 2.528],
    "1600x900": [1600*900, 2.088, 4.153],
    # "1600x1200": [1600*1200, 2.861, 5.233],
    "1920x1080": [1920*1080, 3.038, 5.572],
}

n = [v[0] for k, v in times.items()]
t1 = [v[1] for k, v in times.items()]
t2 = [v[2] for k, v in times.items()]

print(n)
print(t1)
print(t2)

plt.plot(n, t1)
plt.plot(n, t2)

plt.xlabel("Number of pixels")
plt.ylabel("Time (ms)")

plt.show()
