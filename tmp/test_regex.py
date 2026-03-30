import re

regex = r'(\+?\d{1,4}[\s-]?)?\(?\d{2,5}\)?[\s-]?\d{3,5}[\s-]?\d{3,5}'

test_cases = [
    "+91 99216 01234",
    "020 2636 1234",
    "917-262-3879",
    "91726 23789",
    "099216 01234",
    "+1 (123) 456-7890",
]

for tc in test_cases:
    m = re.search(regex, tc)
    if m:
        print(f"CASE: {tc} -> MATCH: {m.group(0)}")
    else:
        print(f"CASE: {tc} -> NO MATCH")
