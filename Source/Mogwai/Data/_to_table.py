import re
import numpy as np


RE_STRING = r"\w+"
RE_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"   # (?:...) non-capturing group
RE_WHITESPACES = r"\s*"

SELECTION_FUNCTIONS = ['Logistic', 'Linear', 'Step']

def parse_error_string(error_string: str) -> dict:
    kv_pattern = fr"(?:({RE_STRING})\(({RE_FLOAT})\))"
    results = re.findall(kv_pattern, error_string)
    print(results)
    data = dict()
    for k, v in results:
        print(f'{k}: {v}')
        data[k] = float(v)

    selection_func_pattern = fr"({RE_STRING})\(({RE_FLOAT}),({RE_FLOAT})\)"
    results = re.findall(selection_func_pattern, error_string)
    print(results)
    if len(results) > 0:
        for result in results:
            print(result)
            selection_func, midpoint, steepness = result
            if selection_func in SELECTION_FUNCTIONS:
                data['selection_func'] = selection_func
                data['midpoint'] = float(midpoint)
                if selection_func == 'Step':
                    steepness = 0
                else:
                    data['steepness'] = float(steepness)
                print(f'selection_func: {selection_func}')
                print(f'midpoint: {midpoint}')
                print(f'steepness: {steepness}')

    return data


def read_inputs():
    lines = []
    while True:
        try:
            line = input()
            lines.append(line)
        except EOFError:
            break
    return lines

if __name__ == '__main__':
    lines = read_inputs()
    # lines = [
    #     "mean(3.0392604e-03), max(1.6975157e+02), median(4.6274781e-05)  Logistic(0.1,0.5)",
    #     "mean(3.3394173e-03), max(1.6983264e+02), median(4.6474099e-05)  Logistic(0.1,5.0)",
    #     "mean(5.9027513e-03), max(1.7283679e+02), median(5.3928470e-05)  Logistic(0.1,50.0)",
    # ]


    table = dict()
    for line in lines:
        data = parse_error_string(line)
        steepness = data['steepness']
        if 'midpoint' in data:
            midpoint = data['midpoint']
        if steepness not in table:
            table[steepness] = dict()
        table[steepness][midpoint] = data

    data_keys = ['mean', 'max', 'median']

    with open('_table.txt', 'w') as f:
        for key in data_keys:
            f.write(f'# {key}\n')
            f.write('\t')
            for midpoint in sorted(list(table.values())[0].keys()):
                f.write(f'{midpoint:7e}\t')
            f.write('\n')
            for steepness in sorted(table.keys()):
                f.write(f'{steepness:7e}\t')
                for midpoint in sorted(table[steepness].keys()):
                    f.write(f'{table[steepness][midpoint][key]:.7e}\t')
                f.write('\n')
            f.write('\n')

        for key in data_keys:
            print(f'# {key}')
            print('\t', end='')
            for midpoint in sorted(list(table.values())[0].keys()):
                print(f'{midpoint:.7e}', end='\t')
            print()
            for steepness in sorted(table.keys()):
                print(f'{steepness:.7e}', end='\t')
                for midpoint in sorted(table[steepness].keys()):
                    print(f'{table[steepness][midpoint][key]:.7e}', end='\t')
                print()
            print()


