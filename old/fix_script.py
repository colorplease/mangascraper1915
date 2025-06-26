with open('webtoon_scraper.py', 'r') as f:
    lines = f.readlines()

filtered_lines = []
seen_no_selenium = False
for line in lines:
    if '--no-selenium' in line and 'parser.add_argument' in line:
        if not seen_no_selenium:
            filtered_lines.append(line)
            seen_no_selenium = True
    else:
        filtered_lines.append(line)

with open('webtoon_scraper.py', 'w') as f:
    f.writelines(filtered_lines)

print('Duplicate argument line removed.') 