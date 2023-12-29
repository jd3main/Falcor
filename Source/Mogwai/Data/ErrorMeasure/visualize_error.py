import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

if __name__ == '__main__':

    # path = Path('Weighted')
    path = Path('.')
    filenames = []
    filenames.append('Unweighted.csv')
    filenames.append('DWeighted.csv')
    filenames.append('UnweightedIllumination.csv')
    filenames.append('SampleCount.csv')
    filenames.append('Gamma.csv')

    # load CSV files
    data  = []
    for filename in filenames:
        data.append(np.loadtxt(path/filename, delimiter=',', skiprows=1))

    # check shape
    shape = data[0].shape
    print(shape)
    for i in range(len(data)):
        assert data[i].shape == shape

    # check timestamps of all files are the same
    for i in range(len(data)):
        assert np.all(data[i][:,0] == data[0][:,0])

    # select timestamp column
    timestamps = data[0][:,0:1]

    # select column 1 of each file
    for i in range(len(data)):
        data[i] = data[i][:,1:2]

    # strip zero rows
    # selection = ~np.all(data[0] == 0, axis=1)
    # for i in range(len(data)):
    #     data[i] = data[i][selection]

    # plot
    nrows = 3
    ncols = 1

    ax1 = plt.subplot(nrows, ncols, 1)
    for i in range(2):
        name = filenames[i].split('.')[0]
        plt.plot(data[i], label=name)
    ax1.legend(loc='upper left')
    ax1.set_ylabel("MSE")
    ax1.set_xlabel("Frame")
    ax1.set_ylim(0, 0.01)


    ax = plt.subplot(nrows, ncols, 2, sharex=ax1)
    ax.plot(data[3], color='green', label='Sample Count')
    ax.set_ylabel('Sample Count')
    ax.legend(loc='upper left')

    ax = ax1.twinx()
    ax.plot(data[4], color='purple', label='Gamma')
    ax.set_ylabel('Gamma')
    ax.legend(loc='upper right')

    ax = plt.subplot(nrows, ncols, 3, sharex=ax1)
    ax.plot(data[2], color='red', label='Illumination')
    ax.set_ylim(-5, 100)
    ax.set_ylabel('Illumination')
    ax.legend(loc='upper left')
    ax.set_ylim(min(data[2][len(data[2])//2:]), max(data[2]))


    plt.show()

