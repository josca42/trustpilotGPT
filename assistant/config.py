import os
from dotenv import load_dotenv
import plotly.express as px

load_dotenv()

config = os.environ


CATEGORY_STR2INT = {
    "other": 0,
    "customer service": 1,
    "counseling": 2,
    "mobile/web bank": 3,
    "fees and interest rates": 4,
}
CATEGORY_INT2STR = {
    -1: "other",
    0: "other",
    1: "customer service",
    2: "counseling",
    3: "mobile/web bank",
    4: "fees and interest rates",
}


LABELS = [
    ("Andet", 0),
    ("Kundeservice", 1),
    ("Rådgivning", 2),
    ("mobil/net bank", 3),
    ("Gebyrer/renter", 4),
]
COLORS = ["#ee6055", "#ff9b85", "#ffd97d", "#aaf683", "#60d394"]
RATING_LABELS = ["1", "2", "3", "4", "5"]
LABEL_COLORS = px.colors.qualitative.T10

LABEL2CATEGORY = {
    -1: "",
    0: "Andet",
    1: "Kundeservice",
    2: "Rådgivning",
    3: "mobil/net bank",
    4: "Gebyrer/renter",
}
