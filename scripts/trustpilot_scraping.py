import requests, json
from bs4 import BeautifulSoup
from assistant.db import models, crud
from assistant.llm import embed
from time import sleep


def scrape_companies(max_pages_to_scrape=100):
	i = 0
	url = "https://www.trustpilot.com/categories/real_estate_agents"
	while url:
		soup = get_soup(url)

		url = get_next_page_url(url)
		js_data = soup.find_all(attrs={"type": "application/json"})[0]
		js_json = json.loads(js_data.decode_contents())

		for company in js_json["props"]["pageProps"]["newestBusinessUnits"]:
			company = models.Company(
			 name=company["displayName"],
			 homepage=company["identifyingName"],
			 stars=company["stars"],
			 trust_score=company["trustScore"],
			 n_reviews=company["numberOfReviews"],
			 country=company["location"]["country"],
			 embedding=embed(company["displayName"])[0],
			)
			crud.company.upsert(company)
			print(f"Company scraped: {company.name}")

		i += 1
		if i > max_pages_to_scrape:
			break

		sleep(20)


def scrape_company_reviews(max_pages_to_scrape=40):
	df_companies = crud.company.get_table()
	for idx, company in df_companies.iterrows():
		try:
			scrape_homepage_reviews(company, max_pages_to_scrape)
			print(f"Homepage scraped: {company['homepage']}")
		except Exception as e:
			sleep(60)
			try:
				scrape_homepage_reviews(company, max_pages_to_scrape)
				print(f"Homepage scraped: {company['homepage']}")
			except:
				print(f"Error: {company['homepage']}")


def scrape_homepage_reviews(company, max_pages_to_scrape=40):
	review_page_url = f"https://trustpilot.com/review/{company['homepage']}"
	for i in range(1, max_pages_to_scrape):
		if review_page_url:
			soup = get_soup(review_page_url)
			reviews = get_reviews(soup)
			if reviews:
				dump_reviews2db(reviews, company)
			else:
				break
		else:
			break

		review_page_url = get_next_page_url(review_page_url)
		sleep(20)


def get_next_page_url(reviews_url):
	soup = get_soup(reviews_url)
	next_page = soup.select('[name="pagination-button-next"]')
	next_page_attr = next_page[0].attrs
	if "href" in next_page_attr:
		next_page_url = f"https://trustpilot.com" + next_page_attr["href"]
	else:
		next_page_url = None
	return next_page_url


def get_soup(url):
	html = requests.get(url)
	return BeautifulSoup(html.content, "html.parser")


def get_reviews(soup):
	data = soup.find_all(attrs={"type": "application/json"})
	if data:
		js_data = soup.find_all(attrs={"type": "application/json"})[0]
		js_json = json.loads(js_data.decode_contents())
		return js_json["props"]["pageProps"]["reviews"]
	else:
		return []


def dump_reviews2db(reviews, company):
	for review in reviews:
		review_obj = models.Review(
		 id=review["id"],
		 company_id=company["id"],
		 company_name=company["name"],
		 rating=review["rating"],
		 timestamp=review["dates"]["publishedDate"],
		 content=review["text"],
		 source="scraped",
		 likes=review["likes"],
		)
		review_db = crud.review.get(review_obj.id)
		if review_db is not None and (review_db.timestamp
		                              == review_obj.timestamp.replace(tzinfo=None)):
			continue
		else:
			review_obj.embedding = embed(review_obj.content)[0]
			crud.review.upsert(review_obj)


if __name__ == "__main__":
	scrape_companies()
	scrape_company_reviews()
