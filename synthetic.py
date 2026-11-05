"""Deterministic synthetic memory-update cases; no LLM-generated ground truth."""

from datetime import date, timedelta


TEMPLATES = [
    (
        "workplace",
        "{person} works at {value} as an analyst. {person} enjoys cycling.",
        "{person} left {old} and now works at {value} as an analyst. {person} still enjoys cycling.",
        "Which company does {person} work for now?",
        "Which company did {person} work for before the move?",
        "On what date did {person} start working at {new}?",
    ),
    (
        "residence",
        "{person} lives in {value}. {person} likes jazz.",
        "{person} moved away from {old} and now lives in {value}. {person} still likes jazz.",
        "Which city does {person} live in now?",
        "Which city did {person} live in before the move?",
        "On what date did {person} move to {new}?",
    ),
    (
        "project",
        "{person} is leading project {value}. {person} plays chess.",
        "{person} stopped leading project {old} and now leads project {value}. {person} still plays chess.",
        "Which project does {person} lead now?",
        "Which project did {person} lead before the change?",
        "On what date did {person} begin leading project {new}?",
    ),
    (
        "device",
        "{person} uses a {value} laptop for work. {person} enjoys hiking.",
        "{person} replaced the {old} laptop and now uses a {value} laptop for work. {person} still enjoys hiking.",
        "Which laptop does {person} use now?",
        "Which laptop did {person} use before the replacement?",
        "On what date did {person} switch to the {new} laptop?",
    ),
    (
        "membership",
        "{person} is a member of {value} gym. {person} likes photography.",
        "{person} cancelled the {old} gym membership and is now a member of {value} gym. {person} still likes photography.",
        "Which gym is {person} a member of now?",
        "Which gym did {person} belong to before switching?",
        "On what date did {person} join {new} gym?",
    ),
]

PEOPLE = [
    "Maya", "Noah", "Leah", "Owen", "Iris", "Ethan", "Nina", "Felix", "Sara", "Liam",
    "Ava", "Kai", "Emma", "Theo", "Zoe", "Adam", "Ruby", "Milo", "Lena", "Aria",
]
VALUES = [
    [("Atlas Labs", "Harbor Studio"), ("Northwind", "Bluebird"), ("Cedar Works", "Lumen"), ("Summit Data", "Orchid Tech")],
    [("Bristol", "Cardiff"), ("Seattle", "Portland"), ("Austin", "Denver"), ("Oslo", "Bergen")],
    [("Aster", "Beacon"), ("Nimbus", "Cobalt"), ("Delta", "Echo"), ("Quartz", "Willow")],
    [("ThinkPad X1", "MacBook Air"), ("Dell XPS", "ThinkPad T14"), ("MacBook Pro", "Framework 13"), ("HP EliteBook", "Dell Latitude")],
    [("Riverside", "Hilltop"), ("Oakwood", "Evergreen"), ("Eastside", "Brookfield"), ("Seaview", "Crosstown")],
]


def cases():
    result = []
    for category, template in enumerate(TEMPLATES):
        kind, first, second, current_q, past_q, when_q = template
        for variant, (old, new) in enumerate(VALUES[category]):
            index = category * 4 + variant
            person = PEOPLE[index]
            start = date(2024, 1, 3) + timedelta(days=index * 3)
            change = date(2024, 4, 3) + timedelta(days=index * 4)
            params = {"person": person, "old": old, "new": new}
            result.append(
                {
                    "id": f"synthetic-{index:02d}-{kind}",
                    "type": kind,
                    "episodes": [
                        {"date": start.isoformat(), "body": first.format(value=old, **params)},
                        {"date": change.isoformat(), "body": second.format(value=new, **params)},
                    ],
                    "questions": [
                        {"type": "current", "question": current_q.format(**params), "answer": new},
                        {"type": "historical", "question": past_q.format(**params), "answer": old},
                        {"type": "change-date", "question": when_q.format(**params), "answer": change.isoformat()},
                    ],
                }
            )
    return result

