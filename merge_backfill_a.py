import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
MS_PATH = os.path.join(ROOT, "milestones.json")
DOC_COPY = (r"C:\Users\milan\Documents\1_Desktop\RADIANT"
            r"\MILESTONES WORK\MILESTONES DATASETS\milestones.json")

NB = "\u2011"  # non-breaking hyphen used in existing titles
FIXES = {
    f"Mass{NB}produced sodium{NB}ion batteries for commercial vehicles and grid storage":
        ("culture", "China"),
    f"High{NB}mobility bismuth{NB}based 2D semiconductors as next{NB}generation channel materials":
        ("culture", "China", "originators", ["Peking University (Peng group)"]),
    f"Youth{NB}led murals and street art as public health messaging and social change tools.":
        ("culture", None),
}

data = json.load(open(MS_PATH, encoding="utf-8"))
ms = data["milestones"]
done = 0
for m in ms:
    fix = FIXES.get(m["title"])
    if not fix:
        continue
    done += 1
    old = m.get(fix[0])
    m[fix[0]] = fix[1]
    print(f"[A] {fix[0]}: {m['title'][:45]}: {old!r} -> {fix[1]!r}")
    if len(fix) == 4:
        m[fix[2]] = fix[3]
        print(f"[A] {fix[2]}: -> {fix[3]}")
assert done == 3, f"only {done}/3 fixes applied"
json.dump(data, open(MS_PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump(data, open(DOC_COPY, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("saved both copies")
