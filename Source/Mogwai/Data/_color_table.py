from pathlib import Path

PRECISION = 4

def is_float(s: str):
    try:
        float(s)
        return True
    except ValueError:
        print(f'not a float: {s}')
        return False

def escape(s: str) -> str:
    return s.replace('_', '\\_').replace('%', '\\%')

def formatRelErr(s: str) -> str:
    s = escape(s)
    if s[0] == '+' or s[0].isnumeric():
        s = f'{{\\color{{red}}{s}}}'
    elif s[0] == '-':
        s = f'{{\\color{{Green}}{s}}}'
    return s

def formatRelSsim(s: str) -> str:
    s = escape(s)
    if s[0] == '-':
        s = f'{{\\color{{red}}{s}}}'
    elif s[0] == '+' or s[0].isnumeric():
        s = f'{{\\color{{Green}}{s}}}'
    return s



rows = []
while True:
    try:
        row = input()
    except EOFError:
        break
    rows.append(row)

output_path = Path(f'_formated_table.txt')

with open(output_path, 'w') as f:
    for row in rows:
        fields = row.split()
        if len(fields) == 0:
            continue
        for i, field in enumerate(fields):

            if 1 <= i <= 2:
                formated = formatRelErr(field)
            elif 3 <= i <= 4:
                formated = formatRelSsim(field)
            else:
                formated = escape(field)

            f.write(formated)
            if i < len(fields) - 1:
                f.write(' & ')

        f.write('\\\\\n')

print(f'write to {output_path}')
