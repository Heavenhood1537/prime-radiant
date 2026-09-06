"""Merge BACKFILL_REVIEW.md parts A/B/C/D into milestones.json (canonical promotion).

A: culture-label fixes (verified)
B: 16 space backfills
C: 7 quantum backfills (C7 Tianyan-504 verified as December 2024)
D: 7 cross-cutting global-balance additions

Also syncs the Documents master copy. XLSX regen + seldon.db rebuild run separately.
"""
import json
import os

CURRENT_YEAR = 2026
ROOT = os.path.dirname(os.path.abspath(__file__))
MS_PATH = os.path.join(ROOT, "milestones.json")
DOC_COPY = (r"C:\Users\milan\Documents\1_Desktop\RADIANT"
            r"\MILESTONES WORK\MILESTONES DATASETS\milestones.json")


def M(year, title, cat, lat, lon, culture, originators, desc, url):
    return {
        "category": cat,
        "title": title,
        "description": desc,
        "year": year,
        "yearsAgo": CURRENT_YEAR - year,
        "location": {"lat": lat, "lon": lon},
        "humanType": "Homo sapiens",
        "culture": culture,
        "originators": originators,
        "ideas": [title],
        "url": url,
    }


A_FIXES = {  # title -> (field, new_value)
    "Chang'e 4 (First Far Side Moon Landing)": ("culture", "China"),
    "Mass-produced sodium-ion batteries for commercial vehicles and grid storage": ("culture", "China"),
    "High-mobility bismuth-based 2D semiconductors as next-generation transistor channels": ("culture", "China"),
    "Youth-led murals and street art as public health messaging and social change": ("culture", None),
}

A_ORIGINATORS = {
    "High-mobility bismuth-based 2D semiconductors as next-generation transistor channels":
        ["Peking University (Peng group)"],
}

A5_TITLE_OLD = "Hayabusa2 (Asteroid Ryugu Sample Return)"  # year 2014 -> 2020 (return year), culture -> Japan

SPACE = "space"

B = [
    M(2012, "Curiosity Rover Landing (Mars Science Laboratory)", SPACE, 28.39, -80.61, "United States",
      ["NASA", "Jet Propulsion Laboratory"],
      "Curiosity is lowered onto Gale Crater by the daring sky-crane maneuver, delivering a nuclear-powered mobile geology laboratory to Mars. It confirms ancient habitable freshwater environments and organic molecules, reshaping the search for life on Mars.",
      "https://en.wikipedia.org/wiki/Curiosity_(rover)"),
    M(2015, "First Orbital Booster Landing and Reuse (Falcon 9)", SPACE, 28.39, -80.61, "United States",
      ["SpaceX", "Elon Musk"],
      "A Falcon 9 first stage flies back from the edge of space and lands vertically on Landing Zone 1, proving orbital rocket boosters can be recovered and reflown. Reusability begins to collapse the cost of reaching orbit, reordering the global launch industry.",
      "https://en.wikipedia.org/wiki/Falcon_9"),
    M(2015, "New Horizons Pluto Flyby", SPACE, 28.39, -80.61, "United States",
      ["NASA", "Alan Stern", "Applied Physics Laboratory"],
      "After a nine-and-a-half-year journey, New Horizons sweeps past Pluto at 14 km/s, returning the first close-up images of nitrogen glaciers, water-ice mountains and its heart-shaped Sputnik Planitia. Humanity completes the initial reconnaissance of the classical planets.",
      "https://en.wikipedia.org/wiki/New_Horizons"),
    M(2016, "FAST Five-hundred-meter Radio Telescope", "science", 25.65, 106.86, "China",
      ["National Astronomical Observatories of China", "Nan Rendong"],
      "FAST, the largest single-dish radio telescope ever built, is completed in Guizhou province. Its 500-meter active surface discovers hundreds of new pulsars and rapidly becomes a leading instrument for fast radio burst science.",
      "https://en.wikipedia.org/wiki/Five-hundred-meter_Aperture_Spherical_Telescope"),
    M(2017, "SESAME Synchrotron First Light", "science", 32.02, 35.95, "Jordan (Middle East)",
      ["SESAME member states", "UNESCO", "Khaled Toukan"],
      "Under the hills of Allan, Jordan, the first beams circulate in SESAME, the Middle East's first major international research facility. Founded on the CERN model, its members include Egypt, Iran, Israel, Jordan, Pakistan, Palestine, Turkey and Bahrain - scientists from politically divided nations working on one accelerator.",
      "https://en.wikipedia.org/wiki/SESAME"),
    M(2020, "Chang'e 5 Lunar Sample Return", SPACE, 19.61, 110.95, "China",
      ["China National Space Administration"],
      "Chang'e 5 lands in Oceanus Procellarum, drills and scoops 1,731 grams of young lunar basalt, and returns them to Earth - the first lunar samples delivered by any nation since the Soviet Luna 24 mission of 1976.",
      "https://en.wikipedia.org/wiki/Chang%27e_5"),
    M(2021, "Tianwen-1 / Zhurong Mars Rover", SPACE, 19.61, 110.95, "China",
      ["China National Space Administration"],
      "In a single mission China orbits, lands and drives on Mars: the Zhurong rover rolls off its lander in Utopia Planitia, making China the second nation to operate a rover on Mars and completing an interplanetary hat-trick on the first attempt.",
      "https://en.wikipedia.org/wiki/Tianwen-1"),
    M(2021, "Emirates Mars Mission (Hope) Orbit Insertion", SPACE, 25.06, 55.21, "United Arab Emirates",
      ["Mohammed bin Rashid Space Centre", "Omran Sharaf", "UAE Space Agency"],
      "The Hope probe enters Mars orbit, making the United Arab Emirates the fifth nation to reach the Red Planet and the first Arab country to fly an interplanetary mission. Its global imaging of the Martian atmosphere rewards the world with new dust and aurora science.",
      "https://en.wikipedia.org/wiki/Emirates_Mars_Mission"),
    M(2021, "Ingenuity: First Powered Flight on Another Planet", SPACE, 18.44, 77.45, "United States",
      ["NASA", "Jet Propulsion Laboratory"],
      "A 1.8-kg helicopter rises three meters above Jezero Crater into air one-hundredth as dense as Earth's, achieving the first powered, controlled flight on another world. Designed for five flights, Ingenuity completes seventy-two over three years.",
      "https://en.wikipedia.org/wiki/Ingenuity_(helicopter)"),
    M(2022, "DART: First Planetary Defense Test", SPACE, 28.39, -80.61, "United States",
      ["NASA", "Johns Hopkins Applied Physics Laboratory"],
      "The DART spacecraft deliberately rams the asteroid moonlet Dimorphos at 6.6 km/s, shortening its orbit by 32 minutes - far more than expected. For the first time in history, humanity measurably moves a celestial body, validating asteroid deflection as a real capability.",
      "https://en.wikipedia.org/wiki/Double_Asteroid_Redirection_Test"),
    M(2022, "Danuri Lunar Orbiter", SPACE, 36.39, 127.36, "South Korea",
      ["Korea Aerospace Research Institute"],
      "South Korea's first lunar mission enters polar orbit around the Moon, carrying the shadow camera that will image permanently darkened craters at the poles where water ice may persist, and testing interplanetary internet-like DTN communications.",
      "https://en.wikipedia.org/wiki/Danuri"),
    M(2023, "Chandrayaan-3 South Pole Landing", SPACE, 13.72, 80.23, "India",
      ["Indian Space Research Organisation"],
      "Vikram lander touches down near the lunar south pole at 69 degrees south - the closest landing to the pole ever achieved - making India the fourth nation to soft-land on the Moon and the first to reach its polar region, the promised land of water ice.",
      "https://en.wikipedia.org/wiki/Chandrayaan-3"),
    M(2023, "OSIRIS-REx Asteroid Sample Return (Bennu)", SPACE, 28.39, -80.61, "United States",
      ["NASA", "Dante Lauretta", "University of Arizona"],
      "The OSIRIS-REx capsule lands in Utah with 121.6 grams of rock and dust from asteroid Bennu. Analysis reveals clays, phosphates and abundant carbon - the kind of primitive material that may have seeded water and prebiotic chemistry on Earth.",
      "https://en.wikipedia.org/wiki/OSIRIS-REx"),
    M(2024, "SLIM Precision Lunar Landing", SPACE, 30.40, 130.97, "Japan",
      ["JAXA"],
      "Japan's Smart Lander for Investigating Moon touches down within 55 meters of its target crater rim - sniper-grade accuracy - making Japan the fifth nation to soft-land on the Moon and demonstrating vision-based autonomous pinpoint landing.",
      "https://en.wikipedia.org/wiki/SLIM_(lunar_lander)"),
    M(2024, "Chang'e 6 Far-Side Sample Return", SPACE, 19.61, 110.95, "China",
      ["China National Space Administration"],
      "Chang'e 6 lands in the South Pole-Aitken basin on the far side of the Moon - hidden from Earth - collects 1,935 grams of the oldest lunar crust, and relays the samples home through the Queqiao satellite. The first far-side samples in history.",
      "https://en.wikipedia.org/wiki/Chang%27e_6"),
    M(2024, "Odysseus IM-1: First Commercial Moon Landing", SPACE, 28.39, -80.61, "United States",
      ["Intuitive Machines"],
      "The privately built Nova-C lander Odysseus stands upright near the lunar south pole - the first commercial spacecraft to reach the lunar surface and the first US soft landing since Apollo 17 in 1972, opening the CLPS era of commercial Moon logistics.",
      "https://en.wikipedia.org/wiki/Odysseus_(spacecraft)"),
]

C = [
    M(2017, "Beijing-Shanghai Quantum Key Distribution Backbone", "science", 39.90, 116.40, "China",
      ["University of Science and Technology of China", "Jian-Wei Pan", "Chinese Academy of Sciences"],
      "A 2,000-kilometer fiber link carries quantum keys between Beijing and Shanghai, and is integrated with the Micius satellite into the first space-ground quantum communication network - quantum-secured video conferences between real offices become routine.",
      "https://en.wikipedia.org/wiki/Quantum_key_distribution"),
    M(2018, "EU Quantum Flagship (EUR 1 Billion, 10 Years)", "science", 50.85, 4.35, "European Union",
      ["European Commission", "EU member states"],
      "Europe unites behind a ten-year, one-billion-euro flagship program coordinating quantum research across the continent - the largest coordinated quantum initiative to date, elevating quantum technology from scattered laboratories to continental strategic infrastructure.",
      "https://en.wikipedia.org/wiki/Quantum_Flagship"),
    M(2021, "D-Wave Advantage 5000-Qubit Annealer", "science", 49.25, -122.98, "Canada",
      ["D-Wave Systems"],
      "D-Wave's Advantage system reaches 5,000+ qubits with 15-way connectivity, the first quantum computer of this scale offered in the cloud. Annealing optimization runs for logistics, manufacturing and finance move from experiments to regular production use.",
      "https://en.wikipedia.org/wiki/D-Wave_Systems"),
    M(2023, "IBM Condor 1,121-Qubit Processor", "science", 41.27, -73.77, "United States",
      ["IBM"],
      "IBM unveils Condor, the first superconducting quantum processor to cross the four-digit qubit threshold, packing 1,121 qubits onto a chip the size of a coin using flexible superconducting cabling - and in the same year shifts its roadmap toward quality over raw count.",
      "https://en.wikipedia.org/wiki/IBM_Condor"),
    M(2023, "48 Logical Qubits on Neutral Atoms", "science", 42.38, -71.12, "United States",
      ["Harvard University", "MIT", "QuEra", "Mikhail Lukin"],
      "A reconfigurable array of rubidium atoms runs quantum algorithms on 48 logical qubits - error-corrected qubits built from hundreds of physical ones - executing algorithmic circuits beyond the reach of uncorrected machines and crossing from quantity to quality.",
      "https://arxiv.org/abs/2312.03982"),
    M(2024, "Google Willow: Error Correction Below Threshold", "science", 34.42, -119.70, "United States",
      ["Google Quantum AI"],
      "The Willow processor demonstrates quantum error correction below threshold: as the code grows from distance 3 to 5 to 7, the logical error rate falls by half each step. Fifty years after the idea was proposed, scaling up now means becoming more reliable, not less.",
      "https://en.wikipedia.org/wiki/Willow_(quantum_computer)"),
    M(2024, "Tianyan-504 Superconducting Quantum Computer (Xiaohong Chip)", "science", 31.84, 117.27, "China",
      ["China Telecom Quantum Group", "Chinese Academy of Sciences", "QuantumCTek"],
      "China's largest single-machine superconducting quantum computer, built around the 504-qubit Xiaohong chip, enters service on the Tianyan quantum cloud - a state telecom operator running quantum computing as public infrastructure, with millions of user visits from over fifty countries.",
      "http://en.sasac.gov.cn/2024/12/30/c_18552.htm"),
]

D = [
    M(2015, "First Gravitational Waves Detected (GW150914)", "science", 46.46, -119.41, "United States",
      ["LIGO Scientific Collaboration", "Rainer Weiss", "Kip Thorne", "Barry Barish"],
      "Twin interferometers in Washington and Louisiana feel spacetime itself ripple as two black holes, 1.3 billion light-years away, spiral together. A thousand scientists from twenty countries confirm a prediction made a century earlier - humanity gains a new sense.",
      "https://en.wikipedia.org/wiki/First_observation_of_gravitational_waves"),
    M(2016, "National Drone Medical Delivery Network (Zipline)", "technology", -1.94, 30.06, "Rwanda",
      ["Zipline", "Rwanda Ministry of Health"],
      "Rwanda launches the world's first national-scale drone delivery network, flying blood units to remote hospitals in minutes instead of hours - proving that the most advanced logistics technology can debut not in rich nations but in Africa, on Africa's own terms.",
      "https://en.wikipedia.org/wiki/Zipline_(drone_delivery)"),
    M(2019, "First Image of a Black Hole (M87*)", "science", -23.03, -67.75, "International",
      ["Event Horizon Telescope Collaboration"],
      "Eight radio observatories on four continents - from Chile to Hawaii, Mexico to Spain to the South Pole - synchronize by atomic clocks to form one Earth-sized virtual eye. The image of glowing plasma around M87*'s event horizon makes the invisible visible.",
      "https://en.wikipedia.org/wiki/Event_Horizon_Telescope"),
    M(2022, "ITER Tokamak Assembly Milestone", "science", 43.71, 5.77, "France (35 nations)",
      ["ITER Organization", "European Union", "China", "India", "Japan", "South Korea", "Russia", "United States"],
      "In Provence, the half-million-tonne tokamak begins to take shape as the first vacuum vessel sections are installed - the largest scientific collaboration in history, building a device meant to release ten times the fusion power it consumes, financed by half of humanity.",
      "https://en.wikipedia.org/wiki/ITER"),
    M(2023, "Casgevy: First Approved CRISPR Medicine", "medicine", 51.50, -0.12, "United Kingdom",
      ["MHRA", "Vertex Pharmaceuticals", "CRISPR Therapeutics"],
      "Britain's regulator authorizes Casgevy (exa-cel), the first licensed therapy built on CRISPR gene editing, effectively curing sickle-cell disease by rewriting patients' blood stem cells. Gene editing leaves the laboratory and becomes medicine.",
      "https://en.wikipedia.org/wiki/Exa-cel"),
    M(2023, "Square Kilometre Array Construction Start", "science", -30.72, 21.44, "South Africa + Australia",
      ["SKA Organisation"],
      "Construction begins on the largest radio telescope ever conceived: nearly 200 dishes across South Africa's Karoo and 130,000 antennas across Western Australia, coordinated by an intergovernmental organization and built on agreements honoring Aboriginal heritage.",
      "https://en.wikipedia.org/wiki/Square_Kilometre_Array"),
    M(2024, "RTS,S Malaria Vaccine Rollout Across Africa", "medicine", 3.87, 11.52, "African nations",
      ["World Health Organization", "GSK", "PATH", "Gavi", "Cameroon Ministry of Health"],
      "Cameroon administers the first routine doses of RTS,S - the first vaccine ever created against a parasite, forty years in the making. Burkina Faso, Ghana, Kenya, Malawi and others follow, protecting children across the continent where malaria claims most of its victims.",
      "https://en.wikipedia.org/wiki/RTS,S"),
]

data = json.load(open(MS_PATH, encoding="utf-8"))
ms = data["milestones"]
by_title = {m["title"]: m for m in ms}

# ---- Part A fixes ----
for title, (field, val) in A_FIXES.items():
    m = by_title.get(title)
    if m is None:
        # whitespace variants: find by normalized compare
        m = next((x for x in ms if " ".join(x["title"].split()) == title), None)
    if m is None:
        print(f"[A] WARNING not found: {title[:60]}")
        continue
    old = m.get(field)
    m[field] = val
    print(f"[A] {field}: {title[:50]}: {old!r} -> {val!r}")

m5 = by_title.get(A5_TITLE_OLD)
if m5 is not None:
    if m5["year"] == 2014:
        m5["year"] = 2020
        m5["yearsAgo"] = CURRENT_YEAR - 2020
        m5["culture"] = "Japan"
        print("[A] Hayabusa2 entry: year 2014 -> 2020 (sample return), culture -> Japan")
    else:
        print(f"[A] Hayabusa2 entry already at year {m5['year']}, left unchanged")

# ---- dedupe check ----
existing_norm = {" ".join(m["title"].split()).lower() for m in ms}
dupes = [m["title"] for m in B + C + D
         if " ".join(m["title"].split()).lower() in existing_norm]
if dupes:
    raise SystemExit(f"DUPLICATE TITLES, aborting: {dupes}")

# ---- merge ----
ms.extend(B + C + D)
ms.sort(key=lambda m: (m["year"] is None, m["year"] or 0))
data["milestones"] = ms
json.dump(data, open(MS_PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump(data, open(DOC_COPY, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

from collections import Counter
print(f"\nmerged: B={len(B)}, C={len(C)}, D={len(D)} | total milestones now {len(ms)}")
print("new culture labels:", dict(Counter(m["culture"] for m in B + C + D)))
print("synced:", DOC_COPY)
