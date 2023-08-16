import plotly.express as px

CATEGORY_STR2INT = {
    "app": {
        "other": 0,
        "functionality": 1,
        "ui": 2,
        "error": 3,
        "stability": 4,
        "response time": 5,
    },
    "bank": {
        "other": 0,
        "customer service": 1,
        "counseling": 2,
        "mobile/web bank": 3,
        "fees and interest rates": 4,
    },
}
CATEGORY_INT2STR = {
    "app": {
        -1: "other",
        0: "other",
        1: "functionality",
        2: "ui",
        3: "error",
        4: "stability",
        5: "response time",
    },
    "bank": {
        -1: "other",
        0: "other",
        1: "customer service",
        2: "counseling",
        3: "mobile/web bank",
        4: "fees and interest rates",
    },
}


APP_REVIEW_LABELS = [
    ("Andet", 0),
    ("Funktionalitet", 1),
    ("UI", 2),
    ("Fejl", 3),
    ("Stabilitet", 4),
    ("Svartider", 5),
]
BANK_REVIEW_LABELS = [
    ("Andet", 0),
    ("Kundeservice", 1),
    ("Rådgivning", 2),
    ("mobil/net bank", 3),
    ("Gebyrer/renter", 4),
]
COLORS = ["#ee6055", "#ff9b85", "#ffd97d", "#aaf683", "#60d394"]
RATING_LABELS = ["1", "2", "3", "4", "5"]
APP_LABEL_COLORS = ["#577590", "#43aa8b", "#90be6d", "#f94144", "#772E25", "#AB4E68"]
BANK_LABEL_COLORS = px.colors.qualitative.T10

APP_LABEL2CATEGORY = {
    -1: "",
    0: "Andet",
    1: "Funktionalitet",
    2: "UI",
    3: "Fejl",
    4: "Stabilitet",
    5: "Svartider",
}
BANK_LABEL2CATEGORY = {
    -1: "",
    0: "Andet",
    1: "Kundeservice",
    2: "Rådgivning",
    3: "mobil/net bank",
    4: "Gebyrer/renter",
}

CUSTOMER_LABEL2CATEGORY = {-1: "", 0: "", 1: "Ny kunde", 2: "Mistet kunde"}
