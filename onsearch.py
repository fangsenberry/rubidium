'''
Functions for searching the web and other online sources
'''

import threading
import os
import requests
from time import sleep
from datetime import datetime, timedelta
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from tqdm.auto import tqdm
import json

from newsapi import NewsApiClient

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup
from urllib.parse import quote

import concurrent
import threading
from collections import deque
import time
import sys

import sys
from pathlib import Path

import random

import re

# Path to the directory containing yggdrasil
parent_dir = Path(__file__).resolve().parent
sys.path.append(str(parent_dir))

# Now you can import from yggdrasil
from yggdrasil import midgard


class SearchManager():
    '''
    This is the class that handles all of the
    '''
    def __init__(self) -> None:
        self.max_ujeebu_requests_concurrent = 50
        self.ujeebu_requests_per_second = 5
        self.search_calltimes = deque(maxlen=self.ujeebu_requests_per_second)
        self.search_calltimes_lock = threading.Lock()
        self.search_semaphore = threading.BoundedSemaphore(self.max_ujeebu_requests_concurrent)

        self.search_website_links_semaphore = threading.BoundedSemaphore(35)
        
        self.timeout_lock = threading.Lock()
        self.timeout_check = False
        
        self.metadata_lock = threading.Lock()
        self.metadata = {} #we initialize one to track all of the things we are doing here. its up to the calling classes to retrieve this and do something with it
        
    def clear_metadata(self): #careful about using this, usually i feel like best practises would be to create a new SearchManager but that might be expensive
        self.metadata = {}
    
    def get_metadata(self):
        '''
        This returns a DEEP COPY of the current state of metadata
        '''
        #TODO: check if i can just do return self.metadata if that is whatevre
        return self.metadata.copy()

    def get_used_resources(self):
        used_resources = self.max_ujeebu_requests_concurrent - self.search_semaphore._value
        return used_resources
    
    def get_remaining_resources(self):
        remaining_resources = self.search_semaphore._value
        return remaining_resources


    def search_list(self, query_list: list, initial_question: str = None):
        '''
        This is the function that handles the search list. We want to multithread this so that we can get the results faster.
        '''
        results = ""

        threads = []
        result_container = {}

        for i, query in enumerate(query_list):
            result_container[i] = "NRC"
            curr_thread = threading.Thread(target=self.search_indiv, args=(query, i, result_container, initial_question), daemon=True)
            curr_thread.start()

            threads.append(curr_thread)

        for thread in tqdm(threads, desc="search_list thread joining"):
            thread.join()
            
        with self.timeout_lock:
            self.timeout_check = True

        for i in range(len(query_list)):
            if result_container[i] != "NRC":
                results += f"{result_container[i]}\n\n"

        results = results.strip("\n\n")

        return results

    def search_indiv(self, query: str, list_index: int, list_results: dict, initial_question: str = None):
        '''
        Here we handle searches for one query, but it goes through all of our search functions on different sources.
        '''
        
        #initialize the metadata entry (this is per query)
        with self.metadata_lock:
            self.metadata[query] = {}
        
        results = ""

        threads = []
        result_container = {}

        result_container[0] = "NRC"
        othernews_search_thread = threading.Thread(target=self.whitelist_site_search, args=(query, 0, result_container, initial_question), daemon=True)
        othernews_search_thread.start()

        threads.append(othernews_search_thread)

        for thread in threads:
            thread.join()

        for i in range(len(threads)):
            if result_container[i] != "NRC":
                results += f"{result_container[i]}\n\n"

        results = results.strip("\n\n")
        list_results[list_index] = results

    def whitelist_site_search(self, query: str, indiv_index: int, indiv_results: dict, initial_question: str = None):
        '''
        Searches whitelisted sites for the query and returns the relevant information (if there is an initial question), otherwise, just returns the articles trawled from the search.
        '''
        sources = ["Financial Times", "SCMP", "Reuters", "Channel News Asia", "Economist"]

        website_threads =[]
        website_results = {}

        #prepare the metadata for all websites field
        with self.metadata_lock:
            self.metadata[query]["websites"] = {}

        for i, source in enumerate(sources):
            website_results[i] = "NRC" #tombstoning just in nothing is returned and all are errors for all sub funcs called
            
            curr_thread = threading.Thread(target=self.search_and_trawl_website, args=(source, query, i, website_results, initial_question), daemon=True)
            curr_thread.start()
            
            website_threads.append(curr_thread)
            
        for thread in website_threads:
            thread.join(timeout=240) #this is aggregate between retrieving the links and getting the trawled information

        total_indiv_results = ""

        #retrieve the results for each website
        for i, source in enumerate(sources):
            if website_results[i] != "NRC":
                total_indiv_results += f"Source:{source}\nContent:{website_results[i]}\n\n"
        
        if total_indiv_results != "":
            indiv_results[indiv_index] = total_indiv_results.strip("\n")
        
    def search_and_trawl_website(self, website_name: str, query: str, website_index: int, website_results: dict, initial_question: str = None):
        '''
        combines the below two helper functions. each thread is operating on this func
        '''
        search_website_starttime = time.time()
        retrieved_links = self.search_website(website_name, query)
        self.metadata[query]["websites"][website_name]["link retrieval time taken"] = time.time() - search_website_starttime
        
        
        trawl_results = {}
        trawl_threads = []
        
        for i, link in enumerate(retrieved_links):
            trawl_results[i] = "NRC"
            curr_thread = threading.Thread(target=self.search_helper, args=(query, link, trawl_results, i, website_name, initial_question), daemon=True)
            curr_thread.start()

            trawl_threads.append(curr_thread)

        # for thread in tqdm(threads, desc="othernews_search thread joining"):
        for thread in trawl_threads:
            thread.join()
            
        total_whitelist_news = ""

        for i in range(len(retrieved_links)):
            if trawl_results[i] != "NRC":
                total_whitelist_news += f"{trawl_results[i]}\n\n"

        total_whitelist_news = total_whitelist_news.strip("\n\n")

        website_results[website_index] = total_whitelist_news
        
        return

    def search_website(self, website_name: str, query: str, top_k: int = 3):
        '''
        TODO: is AFP legit for searching or not?
        TODO: maybe UJEEBU can replace the searching as well in some capacity. right now its a little buggy
        https://www.reuters.com/site-search/?query=test+tests (In this example, the query that I put into the search bar was "test tests")
        https://www.afp.com/en/search/results/world%20religions%20today (In this example, the query that I put into the search bar was "world religions today"
        https://www.economist.com/search?q=test+tests (In this example, the query that I put into the search bar was "test tests")
        https://www.bloomberg.com/search?query=test%20tests (In this example, the query that I put into the search bar was "test tests")
        https://www.scmp.com/search/test%20tests (In this example, the query that I put into the search bar was "test tests")
        https://www.ft.com/search?q=test+tests (In this example, the query that I put into the search bar was "test tests")
        '''
        with self.search_website_links_semaphore:
            
            website_searchurls = {
                "Reuters": "https://www.reuters.com/site-search/?query={query}",
                "AFP": "https://www.afp.com/en/search/results/{query}",
                "Economist": "https://www.economist.com/search?q={query}",
                "Bloomberg": "https://www.bloomberg.com/search?query={query}",
                "SCMP": "https://www.scmp.com/search/{query}",
                "Financial Times": "https://www.ft.com/search?q={query}",
                "Nikkei" : "https://asia.nikkei.com/search?query={query}",
                "Channel News Asia": "https://www.channelnewsasia.com/search?q={query}"
            }

            base_urls = {
                "Reuters": "https://www.reuters.com",
                "AFP": "https://www.afp.com",
                "Economist": "https://www.economist.com",
                "Bloomberg": "https://www.bloomberg.com",
                "SCMP": "https://www.scmp.com",
                "Financial Times": "https://www.ft.com",
                "Nikkei": "https://asia.nikkei.com"
            }

            whitespace_encoding = {
                "Reuters": "+",
                "AFP": "%20",
                "Economist": "+",
                "Bloomberg": "%20",
                "SCMP": "%20",
                "Financial Times": "+",
                "Nikkei" : "+",
                "Channel News Asia": "%20"
            }

            if website_name not in website_searchurls.keys():
                print("Website not supported")
                return []

            space_char = whitespace_encoding.get(website_name, "+")
            encoded_query = quote(query).replace("%20", space_char)
            search_url = website_searchurls[website_name].format(query=encoded_query)
            
            try:
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--incognito")

                # print("trying to insatll chromedriver")
                # webdriver_service = Service(ChromeDriverManager().install())
                # print("installed chromdriver")
                # driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)
                driver = webdriver.Chrome(options=chrome_options)
                # print(f"doing driver get for {website_name}")
                driver.get(search_url)
                # print(f"done driver get for {website_name}")

                if website_name == "SCMP":
                    # print("Searching SCMP...")
                    top_links_raw = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.ebqqd5k0.css-1r4kaks.ef1hf1w0'))
                    )[:top_k]

                    # Using Selenium to extract the href directly, so no need for BeautifulSoup
                    ret = [elem.get_attribute('href') for elem in top_links_raw]

                    driver.quit()
                    
                elif website_name == "Financial Times":
                    top_links_raw = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.js-teaser-heading-link'))
                    )[:top_k]

                    # Using Selenium to extract the href directly, so no need for BeautifulSoup
                    ret = [elem.get_attribute('href') for elem in top_links_raw]

                    driver.quit()

                elif website_name == "Reuters":
                    # print("Searching Reuters...")
                    top_links_raw = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.media-story-card__heading__eqhp9'))
                    )[:top_k]
                    # top_links_raw = driver.find_elements(By.CSS_SELECTOR, 'a.media-story-card__heading__eqhp9')[:top_k]

                    # Using Selenium to extract the href directly, so no need for BeautifulSoup
                    ret = [elem.get_attribute('href') for elem in top_links_raw]

                    driver.quit()
                elif website_name == "Nikkei":
                    base_url = base_urls[website_name]  # Get the base URL for Nikkei Asia
                    top_links_raw = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.card-article__headline a'))
                    )[:top_k]

                    # Append the base URL to each relative URL
                    ret = [elem.get_attribute('href') for elem in top_links_raw]

                    driver.quit()
                    
                elif website_name == "Channel News Asia":
                    top_links_raw = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.hit-name a'))
                    )[:top_k]

                    ret = [elem.get_attribute('href') for elem in top_links_raw]

                    driver.quit()
                elif website_name == "Economist":
                    top_links_raw = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.css-1q84jwp.e1i33f220 ._search-result')))[:top_k]

                    ret = [elem.get_attribute('href') for elem in top_links_raw]

                    driver.quit()

                with self.metadata_lock:
                    self.metadata[query]["websites"][website_name] = {}
                    self.metadata[query]["websites"][website_name]["top_k"] = top_k
                    self.metadata[query]["websites"][website_name]["link retrieval status"] = "SUCCESS"
                    self.metadata[query]["websites"][website_name]["error"] = ""
                    self.metadata[query]["websites"][website_name]["links"] = ret.copy()
                    self.metadata[query]["websites"][website_name]["# links"] = len(ret)
                    
                return ret
                
            except Exception as e:
                with self.metadata_lock:
                    self.metadata[query]["websites"][website_name] = {}
                    self.metadata[query]["websites"][website_name]["top_k"] = top_k
                    self.metadata[query]["websites"][website_name]["link retrieval status"] = "FAIL"
                    self.metadata[query]["websites"][website_name]["error"] = str(e)
                    self.metadata[query]["websites"][website_name]["links"] = []
                    self.metadata[query]["websites"][website_name]["# links"] = 0

                if driver: driver.quit()
                return []

    def search_helper(self, query: str, article_url: str, result_container: dict, index: int, website_name: str, initial_question: str = None):
        '''
        This function does the extraction and then the relevance. We want to multithread the extraction part as well because it takes time and we don't have to do it sequentially
        '''
        try:    
            article_response = self.ujeebu_extract(query, article_url, website_name)

            if article_response == None: return "NRC"
            
            article_content = article_response['article']['text']
            article_content = self.clean_text(article_content) #just to remove the pesky weird unicode characters that might fuck with LLM quslity

            #we need to check and see if the article is too long, then we pass it to summarise
            article_tokens = midgard.get_num_tokens(article_content)
            while article_tokens > 15000:
                print(f"content for article {article_url} is too long at {article_tokens}, summarising...")
                article_content, summarisation_usage, summarisation_cost = midgard.summarise(article_content, chosen_model="gpt-4", to_print=False, return_usage=True, return_cost=True) #use a slightly cheaper model for this. we still want to retain the information, but we are working on a lot of information.
                
                #update the metadata for the cost
                with self.metadata_lock():
                    self.metadata[query]["websites"][website_name][article_url]["summarisation usage"] = summarisation_usage
                    self.metadata[query]["websites"][website_name][article_url]["summarisation cost"] = summarisation_cost
                
                article_tokens = midgard.get_num_tokens(article_content)
                print(f"new content length is {article_tokens} for article {article_url}")

            # res = self.get_relevant(initial_question, article_content)
            rel_check, explanation, usage, cost = self.relevance_check(query, article_content, return_usage=True, return_cost=True) #TODO: no todo, but note that this is using the query and not the complete question. i feel like gpt-3.5 responds better, but if we change to a better model maybe rethink.
            
            #update the metadata for the relevance check
            with self.metadata_lock:
                self.metadata[query]["websites"][website_name][article_url]["relevance usage"] = usage
                self.metadata[query]["websites"][website_name][article_url]["relevance cost"] = cost

            if rel_check == "Y":
                res = article_content
            else:
                res = "NRC"
                
            with self.metadata_lock:
                if res != "NRC":
                    #update the metadata
                    self.metadata[query]["websites"][website_name][article_url]["relevance status"] = "SUCCESS"
                    self.metadata[query]["websites"][website_name][article_url]["relevance explanation"] = explanation
                    self.metadata[query]["websites"][website_name][article_url]["relevant content"] = res

                else: #this means that its NRC, and there is no relevant content
                    self.metadata[query]["websites"][website_name][article_url]["relevance status"] = "FAIL"
                    self.metadata[query]["websites"][website_name][article_url]["relevance explanation"] = explanation

                result_container[index] = res
                
        except Exception as e: #TODO: update the metadata as well.
            print(f"search helper for query: {query} and article_url: {article_url} encountered error: {e}")
            result_container[index] = "NRC"

        return
    
    def ujeebu_extract(self, query: str, article_url: str, website_name):
        '''
        Our Ujeebu API Call, using the Extract endpoint
        
        @returns:
        response.json() if successful, None if not
        status code that was returned from ujeebu extract
        '''
        try:
            base_url = "https://api.ujeebu.com/extract"

            #request options
            params = {
                'js' : 'auto',
                'url' : article_url,
                'proxy_type' : 'premium',
                'response_type' : 'html',
                'timeout' : 80,
            }

            #request header
            headers = {
                'ApiKey' : os.getenv("UJEEBU_API_KEY")
            }

            with self.search_semaphore:
                with self.timeout_lock:
                    if self.timeout_check: #this means that the upper has already timed out, so we don't want to make any more requests
                        
                        #update the metadata
                        with self.metadata_lock:
                            self.metadata[query]["websites"][website_name][article_url] = {}
                            self.metadata[query]["websites"][website_name][article_url]["trawl status"] = "FAIL"
                            self.metadata[query]["websites"][website_name][article_url]["trawl status code"] = "TIMEOUT"
                        
                        return None
                try:
                    # print(f"{self.get_remaining_resources()} resources left")
                    with self.search_calltimes_lock:
                        if len(self.search_calltimes) >= 5:
                            # print(f"SEARCH CALLTIMES: {self.search_calltimes}")
                            time_diff = time.time() - self.search_calltimes[0]
                            if time_diff < 1.0:
                                sleep_time = 1.0 - time_diff
                                # print(f"SLEEPING FOR {sleep_time} SECONDS")
                                time.sleep(sleep_time)

                        self.search_calltimes.append(time.time())
                        #end of the mutex lock here. we are done with editing the search_calltimes deque
                    response = requests.get(base_url, params=params, headers=headers)
                
                except Exception as e:
                    with self.metadata_lock:
                        self.metadata[query]["websites"][website_name][article_url] = {}
                        self.metadata[query]["websites"][website_name][article_url]["trawl status"] = "FAIL"
                        self.metadata[query]["websites"][website_name][article_url]["trawl status code"] = f"EXCEPTION: {e}"
                    return None
                
            #we can make the metadata updates outside of the semaphore, since this does not affect active requests
            with self.metadata_lock:
                self.metadata[query]["websites"][website_name][article_url] = {}
                self.metadata[query]["websites"][website_name][article_url]["trawl status code"] = response.status_code
                
                if response.status_code == 200:
                    self.metadata[query]["websites"][website_name][article_url]["trawl status"] = "SUCCESS"
                    self.metadata[query]["websites"][website_name][article_url]["error"] = ""
                    self.metadata[query]["websites"][website_name][article_url]["trawl json response"] = response.json().copy()
                    
                    return response.json()
                else:
                    self.metadata[query]["websites"][website_name][article_url]["trawl status"] = "FAIL"
                    
                    return None

        except Exception as e:
            with self.metadata_lock:
                self.metadata[query]["websites"][website_name][article_url] = {}
                self.metadata[query]["websites"][website_name][article_url]["trawl status"] = "FAIL"
                self.metadata[query]["websites"][website_name][article_url]["trawl status code"] = f"EXCEPTION: {e}"
            return None

    def get_relevant(self, query: str, information: str):
        '''
        Checks for information relevance against the query.
        '''

        system_init = f"You are RelatedGPT. You are an AGI that takes in a query and a block of information and returns the relevant information from the block of information. You are extremely good and extremely detailed when reviewing text, and you do not miss out anything.\n\n"

        prompt = f"You are given a query and the content of an article sourced from a news site. Your job is to determine if the content is related to the question, and if so, extract it. If there is relevant content, you must extract the relevant content EXACTLY AS IT IS REPRESENTED IN THE TEXT, including any pieces of context that are associated with that piece of content even in the slightest. If there is no relevant content in the ENTIRE article, you must return the acronym NRC. To clarify, IF there is no relevant content in the ENTIRE article, you MUST only return the acronym NRC and NOTHING ELSE. This acronym must be returned as its raw text as this will be parsed programmatically. Otherwise, return all of the relevant content AND context EXACTLY as they appear in the text. These articles have already been vetted for relevance, and are results from a search using the query, therefore, it is far more likely that the content is related/relevant than not. There might be small portions like advertisements within the article that are irrelevant, and if there are, you should just discard these small parts. Additionally, You should be extremely lenient with your determination of whether something is related or not, which is to say that even if something is remotely related you MUST include it. If it could be slightly potentially useful in answering the question, return the relevant information. The query and content are given below.\n\nQuery:\n{query}\n\nInformation:\n{information}"
        
        return midgard.call_gpt_single(system_init, prompt, function_name="get_relevant", chosen_model="gpt-3.5-turbo-1106", to_print=False, try_limit=2)
    
    def relevance_check(self, query: str, information: str, return_usage: bool = False, return_cost: bool = False):
        '''
        This func does not ask for NRC to be returned, and just asks for the relevant content to be returend.
        '''
        
        system_init = f"You are RelatedGPT. You are an AGI that takes in a query and a block of information and returns the relevant information from the block of information. You are extremely good and extremely detailed when reviewing text, and you do not miss out anything.\n\n" 
        
        prompt = f"You are part of a multi-step research process that will culminate in answering a complex question for a user. You are given a user's query and the content of an article sourced from a news site. Content from the article will be used to build the research that will eventually answer the user's question. Your role in this process is to determine if this article contains information related to the topics concerning the question from the user. If the article contains relevant content, you must a short and succint explanation of why this is relevant and the single letter Y. Your explanation and the letter Y must be seperated by the delimiter |||. Otherwise, you must return return an explanation of why the article has no relevant content, and the letter N, also seperated by the delimeter |||. You MUST STRICTLY follow the requested format, which is <explanation>|||<Y or N>. Your output will be parsed programmatically and any deviance will cause the algorithm to break. Here is the question that the user has asked:\n\nQuery:\n{query}\n\nHere is the content from the news article:\n{information}"
        
        # Additionally, You should be extremely lenient with your determination of whether something is related or not, which is to say that even if some small part of the article is remotely related you MUST return Y. You are not checking if the entire article is relevant, you are checking if there exists a portion (or more) of the article that is relevant. The ONLY case in which you will return N is if there is absolutely no relevant content at all within the text.
        
        
        #handling the trycount here because we need to check the output to see if it works
        try_count = 3
        while try_count > 0:
            try:
                res = midgard.call_gpt_single(system_init, prompt, function_name="relevance_check", chosen_model="gpt-3.5-turbo-1106", to_print=False, try_limit=1, return_usage=return_usage, return_cost=return_cost)
                
                chat_completion = res[0]
                
                chat_completion = chat_completion.strip("\n").strip("'").strip('"').strip(" ")
                
                chat_completion = chat_completion.split("|||")
                check = chat_completion[1]
                explanation = chat_completion[0]
                
                if check == "Y" or check == "N":
                    #format the return object based on flags
                    ret = [check, explanation]
                    
                    if return_usage:
                        ret.append(res[1])
                        
                    if return_cost:
                        ret.append(res[2])
                    
                    return ret
                else:
                    try_count -= 1
                    continue
            except Exception as e:
                print(f"error in relevance check: {e}")
                try_count -= 1
                pass
            
        #if we reach here is means that it has failed
        ret = ["N", "FAILED TRY COUNT LIMIT"]
        
        if return_usage:
            fail_usage_dict = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
            ret.append(fail_usage_dict) #TODO: need to check, but if fail, then no bill? im not sure but need to check...
            
        if return_cost:
            ret.append(0)
            
        return ret

    def clean_text(self, text):
        '''
        Simple function to clean all the weird unicode characters we are getting from trawling.
        '''
        # Replace specific Unicode characters
        replacements = {
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u00a0': ' ',  # Non-breaking space
            '\u200a': ' ',  # Hair space
            # Add more replacements as needed
        }

        for unicode_char, replacement in replacements.items():
            text = text.replace(unicode_char, replacement)

        # Remove any remaining non-ASCII characters
        text = re.sub(r'[^\x00-\x7F]+', '', text)

        return text
    
    def rephrase_query(self, query: str, source: str):
        system_init = f"You are SearchGPT. You are a genius at understanding how searching news websites work, and how to build and adjust queries in order to get the result that you want."

        prompt = f"This search query gave no results when being searched on {source}. I need you to adjust it so I actually get the results I want. The query is given below. Your output will be used programmatically to search the website, so you MUST only return the raw text of the search query that will be put into the search bar of the news site. You must only return ONE query, with no quotes around the text.\n\nQuery: {query}"

        return midgard.call_gpt_single(system_init, prompt, function_name="rephrase_query", chosen_model="gpt-4")



    '''
    TODO: expand this to include all that we want. all the sources now since we are using ujeebu
    Uses NewsAPI to get the relevant news articles.

    Currently using the following sources:
    1. CNN
    2. Reuters
    3. Business Insider
    4. BBC News
    5. Ars Technica
    6. TechCrunch
    7. Time

    The search process follows the following steps:
    1. Transform the query into a list of keywords grouped by boolean logic using GPT-4
    2. Use the list of keywords to search for relevant articles using NewsAPI
    3. For each article, use GPT-4 to determine whether the article is relevant or not (Multi-threaded)
    4. If the article is relevant, use BeautifulSoup to get the full content of the article
    5. Return the relevant articles and their full content

    Needs to use selenium because search results take time to load
    '''
    def newsapi_search(self, query: str):
        newsapi_sources = "cnn,reuters,business-insider,bbc-news,ars-technica,techcrunch,time"

        newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_KEY"))

        query_kw = create_keywords(query)

        # print(f"NewsAPI search:{query_kw}")

        #get the current date and go 3 weeks back
        today = datetime.today()
        three_weeks_ago = today - timedelta(weeks=3)
        formatted_date = three_weeks_ago.strftime("%Y-%m-%d")

        # print(formatted_date)

        try:
            response = newsapi.get_everything(
                                        q=query_kw,
                                        sources=newsapi_sources,
                                        from_param=formatted_date,
                                        language='en',
                                        sort_by='relevancy',
                                        page_size=10
                                        )
        except Exception as e:
            print(f"Error in newsapi search {e}")
            return ""
        


        relevant_information = ""

        print(f"for query: {query}, got {len(response['articles'])} articles from NewsAPI.")
        relevant_count = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.get_relevant_helper, query, article['content']) for article in response['articles']]

            for future in concurrent.futures.as_completed(futures, timeout=30):
                if future.result != "NRC":
                    relevant_count += 1
                relevant_information += f"{future.result()}\n\n" if future.result != "NRC" else ""

        # print(f"Got {relevant_count} relevant articles out of {len(response['articles'])} articles for query {query}")

        return relevant_information


def ujeebu_search_scrape(url):
    base_url = "https://api.ujeebu.com/scrape"

    #request options
    params = {
        'js' : 'auto',
        'url' : url,
        'proxy_type' : 'premium',
        'response_type' : 'html',
        'json' : 'true'
    }

    for key, value in params.items():
        print(key, value)

    #request header
    headers = {
        'ApiKey' : os.getenv("UJEEBU_API_KEY")
    }

    #send request
    
    response = requests.get(base_url, params=params, headers=headers)
    print(f"Ujeebu extract response was: {response}")
    #TODO: need some formatting here for what we want, the title, the text, the metadata if we are interested etc.

    return response.json()

def extract_search_links(website_name, query, top_k=5):
    url = "https://api.ujeebu.com/scrape"

    payload = json.dumps({
    "url": "https://www.reuters.com/site-search/?query=japan+AI",
    # "js": True,
    "response_type": "json",
    "extract_rules": {
        "links": {
        "selector": "a.media-story-card__heading__eqhp9",
        "type": "link",
        "multiple" : True
        }
    },
    "auto-premium-proxy" : True
    })


    headers = {
    'ApiKey': os.getenv("UJEEBU_API_KEY"),
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)

'''
Identifies the topics that require more research, and then segments these topics into more search queries.

@params:
query: The question asked by the user

@returns:
search_query: A list of search queries that will best return results for resources that can best answer what the user is asking.
'''
def query_to_search(query):
    print("Transforming user query to search query...")

    system_init = "You are IdentifyGPT. You are an AGI that takes in a question and identifies seperate content topics in the question. If there are multiple topics that need to be searched seperately within the question, seperate them with a semicolon."

    prompt = f"I will give you a question. I want you to identify the topics that need research in this question and return the seperate topics formatted to be used in search queries. The search queries should be seperated by the seperate topics. If there are multiple topics that need to be searched seperately within the question, seperate them with a semicolon. The final string should be a search query encompassing all the topics. For example, if the question is 'Tell me about the protests in France and how they relate to the working class condition. Write a poem about this too.', you should return 'protests in France;working class;France protests and working class'. There must be no extra whitespace between search query terms. You MUST only extract the topics from the query. For example, 'Write a poem about this too' is being ignored as it is describes the task, but is not something that requires further research through a search. For example, if the query is 'Tell me all of the latest news in activism' you should return 'activism'. You should also remove all references to news, since this query is going to be used to search a news site. For example, given the query 'Tell me all of the latest LGBTQ+ news', you should return 'LGBTQ+;LGBTQ' \n\nQuestion: {query}"

    retry_count = 5
    while retry_count:
        try:
            response = client.chat.completions.create(model="gpt-4",
            messages=[
                {"role": "system", "content": system_init},
                {"role": "user", "content": prompt}
            ])
            break
        except Exception as e:
            print(f"Error encountered: {e}. Retrying in 10 seconds...")
            sleep(10)
            print("Retrying...")
            retry_count -= 1


    return response.choices[0].message.content.split(';')

'''
Creates keywords grouped by boolean logic according to a query using GPT-4. This is built for NewsAPI queries.
'''
def create_keywords(query):
    model = "gpt-4"

    querykw_init = "You are QueryGPT, an AGI that takes in a query and converts it to a list of query keywords that are grouped by boolean logic."

    prompt = f'''
    You are QueryGPT, an AGI that takes in a comma seperated list of keywords and groups it according to boolean logic. You will be given a query. First, identify the topics in the query that are found in the news. Then, reformat this into a query that will go into a NewsAPI API call. I want you to change the provided query into a set of query keywords grouped by boolean logic. The boolean operators that you have access to are "AND" and "OR". You can also use "(" and ")" to group keywords together with logical operators. You should minimize your use of "AND"s as much as possible in order to maintain a more lenient scope of the query. Entities should be seperate, for example, if the query is 'Can you give me the latest updates on US Finance?', you should return 'US AND (Finance OR economy OR economic)', not 'US Finance AND (economy or economic)'. For example, if you are given the query "Will the First Republic Bank collapse lead to a Global Financial Crisis?", you should return "First Republic Bank AND (collapse OR bankruptcy OR failure OR default OR crash OR crisis). There is no need to include the search term "Global Financial Crisis" because that is an analysis that will be provided seperately.

    For example, given the query: "What is currently happening with protests in France?", you should return "France AND (protests OR civil unrest OR demonstrations OR social issue)". Your response must be less than 500 characters. The query and list of keywords are given below.

    Query: {query}
    '''
    while 1:
        try:
            response = client.chat.completions.create(model=model,
            messages=[
                {"role": "system", "content": querykw_init},
                {"role": "user", "content": prompt}
            ])

            return response.choices[0].message.content
        except Exception as e:
            print(f"Encountered Error: {e}. Retrying in 10 seconds...")
            sleep(10)
            print(f"Retrying creating keywords...")