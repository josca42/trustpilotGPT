from assistant.db import crud

import time

start = time.process_time()
companies = ["danse bank", "lunar", "Nordea", "Handelsbanken", "frøs"]
companies = [crud.company.most_similar_name(company) for company in companies]

print(time.process_time() - start)
