"""UPSC micro-topic map based on the user's 2026 syllabus reference PDF.

The rule-based matches are study aids: an article can match several topics,
and a student should confirm the fit before using it in an answer.
"""

import re


PAPER_ORDER = ("Prelims", "GS Paper I", "GS Paper II", "GS Paper III", "GS Paper IV")

SYLLABUS = {
    "History": {
        "primary_paper": "GS Paper I",
        "papers": ("Prelims", "GS Paper I"),
        "topics": {
            "Ancient India": ("harappan", "indus valley", "vedic", "mahajanapada", "mauryan", "ashoka", "gupta empire", "sangam", "buddhism", "jainism"),
            "Medieval India": ("delhi sultanate", "mughal", "vijayanagara", "bhakti", "sufi", "maratha empire", "mughal architecture"),
            "Modern India and the freedom movement": ("1857 revolt", "freedom struggle", "quit india", "swadeshi movement", "indian national congress", "gandhian", "colonial rule", "independence movement", "partition of india"),
            "Post-independence consolidation": ("princely states", "integration of states", "states reorganisation", "linguistic states", "sardar patel", "post-independence india"),
            "World history": ("world war", "cold war", "decolonisation", "french revolution", "industrial revolution", "imperialism", "apartheid"),
        },
    },
    "Indian Culture": {
        "primary_paper": "GS Paper I",
        "papers": ("Prelims", "GS Paper I"),
        "topics": {
            "Architecture and heritage": ("temple architecture", "stupa", "monument", "heritage site", "world heritage", "archaeological survey", "unesco"),
            "Art forms, music and dance": ("classical dance", "folk dance", "classical music", "folk music", "painting tradition", "sculpture", "festival"),
            "Religions and philosophical traditions": ("buddhism", "jainism", "bhakti", "sufi", "religious site", "pilgrimage"),
            "Languages and literature": ("classical language", "literature", "manuscript", "language recognition", "sanskrit", "tamil literature"),
        },
    },
    "Geography": {
        "primary_paper": "GS Paper I",
        "papers": ("Prelims", "GS Paper I"),
        "topics": {
            "Physical geography and geomorphology": ("plate tectonics", "earthquake", "volcano", "tsunami", "glacier", "landform", "geomorphology"),
            "Climate and oceanography": ("monsoon", "el nino", "la nina", "cyclone", "ocean current", "sea level", "climate pattern"),
            "Physical geography of India": ("himalaya", "indo-gangetic", "river basin", "drainage system", "indian monsoon", "indian climate", "soil erosion"),
            "Human and economic geography": ("population density", "census", "migration", "urbanisation", "urbanization", "demographic", "transport corridor", "mineral resource", "industrial corridor"),
            "Contemporary geographical issues": ("landslide", "glacial lake", "coastal erosion", "heatwave", "drought", "floodplain", "island vulnerability"),
        },
    },
    "Polity and Governance": {
        "primary_paper": "GS Paper II",
        "papers": ("Prelims", "GS Paper II"),
        "topics": {
            "Constitution, rights and federalism": ("constitution", "fundamental rights", "directive principles", "basic structure", "federalism", "centre-state", "constitutional amendment", "citizenship act"),
            "Parliament, executive and judiciary": ("parliament", "supreme court", "high court", "judicial review", "ordinance", "cabinet", "council of ministers", "legislative committee"),
            "Local government and constitutional bodies": ("panchayat", "municipal", "local government", "election commission", "finance commission", "comptroller and auditor general", "cag", "upsc"),
            "Elections and political dynamics": ("election", "electoral reform", "anti-defection", "representation of the people act", "delimitation", "political party"),
            "Governance, transparency and accountability": ("governance", "right to information", "rti", "social audit", "citizen charter", "public service delivery", "lokpal", "e-governance"),
            "Social justice and welfare": ("welfare scheme", "social justice", "vulnerable section", "gender equality", "poverty", "hunger", "public health", "education access", "reservation policy"),
        },
    },
    "Economy and Agriculture": {
        "primary_paper": "GS Paper III",
        "papers": ("Prelims", "GS Paper III"),
        "topics": {
            "Planning, growth and development": ("gdp", "economic growth", "inclusive growth", "national income", "employment", "human development index", "economic planning"),
            "Fiscal policy, monetary policy and banking": ("union budget", "fiscal deficit", "fiscal policy", "monetary policy", "reserve bank", "rbi", "repo rate", "inflation targeting", "non-performing asset", "banking"),
            "Taxation and public finance": ("gst", "income tax", "tax reform", "public expenditure", "government revenue", "subsidy reform"),
            "Agriculture, land and food security": ("minimum support price", "msp", "crop insurance", "public distribution system", "pds", "agriculture", "irrigation", "land reform", "food security", "e-nam"),
            "Industry, infrastructure and investment": ("infrastructure", "public-private partnership", "ppp", "foreign direct investment", "fdi", "manufacturing", "food processing", "logistics"),
            "Foreign trade and international institutions": ("balance of payments", "trade agreement", "world trade organization", "wto", "international monetary fund", "imf", "world bank", "exchange rate", "tariff"),
            "Contemporary economic issues": ("unemployment", "inequality", "economic survey", "economic slowdown", "financial inclusion", "digital payment", "rupee"),
        },
    },
    "Science and Technology": {
        "primary_paper": "GS Paper III",
        "papers": ("Prelims", "GS Paper III"),
        "topics": {
            "Biology, biotechnology and human health": ("biotechnology", "genetic engineering", "gene editing", "crispr", "vaccine", "antimicrobial resistance", "public health technology", "genome"),
            "Space technology and ISRO missions": ("isro", "chandrayaan", "gaganyaan", "aditya-l1", "satellite launch", "space mission", "launch vehicle", "navic"),
            "Defence technology and nuclear energy": ("missile", "defence technology", "drone technology", "nuclear energy", "nuclear reactor", "nuclear policy", "brahmos"),
            "Information technology, AI and intellectual property": ("artificial intelligence", "machine learning", "deepfake", "cybersecurity", "quantum technology", "nanotechnology", "patent", "intellectual property", "5g", "semiconductor"),
            "Emerging science and technology": ("scientific research", "technology innovation", "robotics", "internet of things", "biometric", "digital infrastructure"),
        },
    },
    "Environment and Ecology": {
        "primary_paper": "GS Paper III",
        "papers": ("Prelims", "GS Paper III"),
        "topics": {
            "Ecology, ecosystems and biodiversity": ("ecosystem", "biodiversity", "wildlife", "wetland", "mangrove", "coral reef", "iucn", "species conservation"),
            "Conservation and protected areas": ("national park", "wildlife sanctuary", "tiger reserve", "biosphere reserve", "project tiger", "project elephant", "protected area"),
            "Pollution and waste management": ("air pollution", "water pollution", "plastic waste", "e-waste", "solid waste", "hazardous waste", "pollution control"),
            "Environmental laws and governance": ("environment protection act", "forest conservation act", "wildlife protection act", "environmental clearance", "environment impact assessment", "ngt", "national green tribunal"),
            "Climate change and international governance": ("climate change", "global warming", "greenhouse gas", "paris agreement", "cop summit", "carbon emissions", "net zero", "carbon credit", "unfccc"),
        },
    },
    "International Relations": {
        "primary_paper": "GS Paper II",
        "papers": ("Prelims", "GS Paper II"),
        "topics": {
            "Foreign policy and bilateral relations": ("foreign policy", "bilateral relations", "india-us", "india-russia", "india-france", "india-japan", "india-israel", "strategic partnership"),
            "India and its neighbours": ("india-nepal", "india-bangladesh", "india-maldives", "india-sri lanka", "india-pakistan", "india-china", "neighbourhood first"),
            "Global institutions": ("united nations", "un security council", "imf", "world bank", "international court of justice", "global institution"),
            "Indo-Pacific and security": ("indo-pacific", "quad", "south china sea", "maritime security", "indian ocean region", "sea lanes"),
            "Multilateral groupings": ("brics", "saarc", "bimstec", "asean", "g20", "sco", "wto", "multilateral summit"),
        },
    },
    "Internal Security and Disaster Management": {
        "primary_paper": "GS Paper III",
        "papers": ("Prelims", "GS Paper III"),
        "topics": {
            "Terrorism, extremism and insurgency": ("terrorism", "naxalism", "left wing extremism", "insurgency", "terror network", "radicalisation"),
            "Cybersecurity and information security": ("cybersecurity", "cyber attack", "ransomware", "cyber warfare", "data breach", "online fraud"),
            "Border security and financial crime": ("border security", "line of control", "lac", "money laundering", "drug trafficking", "human trafficking", "coastal security"),
            "Police reforms and security forces": ("police reform", "central armed police", "bsf", "crpf", "nsg", "security force", "intelligence agency"),
            "Disaster management and resilience": ("disaster management", "ndma", "ndrf", "flood response", "earthquake response", "disaster preparedness", "sendai framework", "early warning system"),
        },
    },
    "Ethics, Integrity and Aptitude": {
        "primary_paper": "GS Paper IV",
        "papers": ("GS Paper IV",),
        "topics": {
            "Ethics, human values and emotional intelligence": ("public service ethics", "human values", "emotional intelligence", "integrity in public life", "civil service values"),
            "Aptitude for civil services": ("impartiality", "objectivity", "non-partisanship", "empathy", "compassion", "civil servant"),
            "Probity, accountability and applied ethics": ("probity", "conflict of interest", "whistleblower", "corruption", "code of ethics", "ethical dilemma", "public accountability"),
            "Case studies and ethical decision-making": ("ethical dilemma", "case study", "public interest", "misuse of public funds", "administrative discretion"),
        },
    },
}


def _contains(text, phrase):
    return bool(re.search(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", text))


def match_syllabus(title, description=""):
    """Return up to five best syllabus matches, with title matches weighted higher."""
    title_text = (title or "").casefold()
    description_text = (description or "").casefold()
    matches = []
    for subject, section in SYLLABUS.items():
        for topic, keywords in section["topics"].items():
            score = 0
            for keyword in keywords:
                if _contains(title_text, keyword):
                    score += 4
                elif _contains(description_text, keyword):
                    score += 1
            if score:
                matches.append({
                    "subject": subject,
                    "topic": topic,
                    "paper": section["primary_paper"],
                    "papers": section["papers"],
                    "score": score,
                })
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:5]
