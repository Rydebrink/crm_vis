# To solve your task you might (or might not) need to import additional libraries
from flask import Flask, render_template, flash, redirect, url_for, request, logging
import requests as api_request
import json
import functools
import collections
import operator
import datetime
import calendar
from dateutil.parser import parse
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('PROJECT_API_KEY')

STATUS_CUSTOMER = 3
STATUS_INACTIVE = 2
STATUS_PROSPECT = 1
STATUS_IRRELEVANT = 0

app = Flask(__name__, static_url_path='/static')

# Headers for REST API call.
# Paste the API-key you have been provided as the value for "x-api-key"
headers = {
    "Content-Type": "application/json",
    "Accept": "application/hal+json",
    "x-api-key": API_KEY
}


# Example of function for REST API call to get data from Lime
def get_api_data(headers, url):
    # First call to get first data page from the API
    response = api_request.get(
        url=url, headers=headers, data=None, verify=False)

    # Convert the response string into json data and get embedded limeobjects
    json_data = json.loads(response.text)

    limeobjects = json_data.get("_embedded").get("limeobjects")

    # Check for more data pages and get thoose too
    nextpage = json_data.get("_links").get("next")
    # while nextpage is not None:
    #     url = nextpage["href"]
    #     print("hello")
    #     response = api_request.get(
    #         url=url, headers=headers, data=None, verify=False)
    #     json_data = json.loads(response.text)
    #     limeobjects += json_data.get("_embedded").get("limeobjects")
    #     nextpage = json_data.get("_links").get("next")

    return limeobjects


# Index page
@ app.route('/')
def index():
    return render_template('home.html')


def filter_deals(data):
    deals = []
    for entry in data:
        deal = {
            "value": entry.get("value"),
            "status": entry.get("dealstatus").get("key"),
            "id": entry.get("_id"),
            "Closing date": parse(entry.get("closeddate")),
            "Description": entry.get("_descriptive")
        }
        if (entry.get("_embedded") is not None):
            deal["Customer"] = entry.get("_embedded").get(
                "relation_company").get("name")
            deal["Customer-id"] = entry.get("_embedded").get(
                "relation_company").get("_id")
            deal["company_status"] = entry.get("_embedded").get(
                "relation_company").get("buyingstatus").get("key")
        deals.append(deal)
    return deals

# Example page


@ app.route('/example')
def example():

    # Example of API call to get deals
    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
    params = "?_limit=50&_embed=company"
    url = base_url + params
    response_deals = get_api_data(headers=headers, url=url)

    # YOUR CODE HERE
    # In this exmaple, this is where you can do something with the data
    # in 'response_deals' before you return it.

    if len(response_deals) > 0:
        dream_team_deals = filter_deals(response_deals)
        return render_template('example.html', deals=dream_team_deals)
    else:
        msg = 'No deals found'
        return render_template('example.html', msg=msg)


def get_average_per_year(data):
    collected_data = collections.defaultdict(list)
    return_data = []
    for deal in data:
        year = deal.get("Closing date").year
        status = deal.get("status")
        if status == "agreement":
            value = deal.get("value")
            collected_data[year].append(value)
    for year in collected_data:
        count = 0
        total = 0
        for value in collected_data[year]:
            total += value
            count += 1
        collected_data[year] = round((total / count), 2)
        return_data.append(
            {"year": year, "avg_value": collected_data[year], "total_deals": count})
    return return_data


@app.route('/average_year')
def average_year():

    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
    params = "?_limit=50&_embed=company"
    url = base_url + params
    response_deals = get_api_data(headers=headers, url=url)

    if len(response_deals) > 0:
        data = filter_deals(response_deals)
        average_per_year = get_average_per_year(data)
        return render_template('average_year.html', deals=average_per_year)
    else:
        msg = 'No deals found'
        return render_template('average_year.html', msg=msg)


def get_average_per_month(data, year):
    collected_data = collections.defaultdict(list)
    return_data = []
    for deal in data:
        deal_year = deal.get("Closing date").year
        status = deal.get("status")
        if deal_year == year and status == "agreement":
            month = deal.get("Closing date").month
            collected_data[month].append(1)
    for month in collected_data:
        count = 0
        for value in collected_data[month]:
            count += 1
        collected_data[month] = count
        return_data.append(
            {"month": month, "name": calendar.month_name[month], "total_deals": collected_data[month]})
    return sorted(return_data, key=operator.itemgetter("month"))


@app.route('/average_month/<pick_year>')
def average_month(pick_year):
    year = datetime.datetime(int(pick_year), 1, 1).year

    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
    params = "?_limit=50&_embed=company"
    url = base_url + params
    response_deals = get_api_data(headers=headers, url=url)

    if len(response_deals) > 0:
        data = filter_deals(response_deals)
        average_per_month = get_average_per_month(
            data, year)
        return render_template('average_month.html', deals=average_per_month, display_year=year)
    else:
        msg = 'No deals found'
        return render_template('average_month.html', msg=msg)


def get_customer_value(data, year):
    collected_data = collections.defaultdict(list)
    return_data = []
    for deal in data:
        customer = deal.get("Customer")
        if customer is not None:
            deal_year = deal.get("Closing date").year
            status = deal.get("status")
            if deal_year == year and status == "agreement":
                value = deal.get("value")
                collected_data[customer].append(value)
    for cust in collected_data:
        total = 0
        count = 0
        for value in collected_data[cust]:
            total += value
            count += 1
        collected_data[cust] = total
        return_data.append(
            {"Customer": cust, "Value": collected_data[cust], "total_deals": count})

    return sorted(return_data, key=operator.itemgetter("Value"), reverse=True)


@app.route('/customer_value/<pick_year>')
def customer_value(pick_year):
    year = datetime.datetime(int(pick_year), 1, 1).year

    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
    params = "?_limit=50&_embed=company"
    url = base_url + params
    response_deals = get_api_data(headers=headers, url=url)

    if len(response_deals) > 0:
        data = filter_deals(response_deals)
        customers = get_customer_value(
            data, year)
        return render_template('customer_value.html', customers=customers, display_year=year)
    else:
        msg = 'No deals found'
        return render_template('average_month.html', msg=msg)


def filter_customers(data):
    customers = []
    for entry in data:
        customer = {
            "id": entry.get("_id"),
            "name": entry.get("name"),
        }
        customers.append(customer)
    print(customers)
    return customers


def subtract_years(dt, years):
    try:
        dt = dt.replace(year=dt.year-years)
    except ValueError:
        dt = dt.replace(year=dt.year-years, day=dt.day-1)
    return dt


def set_customer_status(data):
    status = max(data)

    if status == STATUS_CUSTOMER:
        return "Customer"
    elif status == STATUS_INACTIVE:
        return "Inactive"
    elif status == STATUS_IRRELEVANT:
        return "Irrelevant"
    elif status == STATUS_PROSPECT:
        return "Prospect"
    else:
        return "Unknown status"


def get_customer_status(deals):
    collected_data = collections.defaultdict(list)
    return_data = []
    last_year = subtract_years(datetime.datetime.now(datetime.timezone.utc), 1)
    for data in deals:
        if data.get("Customer-id") is not None:
            customer = data.get("Customer")
            customer_id = data.get("Customer-id")
            deal_id = data.get("id")
            deal_status = data.get("status")
            deal_date = data.get("Closing date")
            customer_status = data.get("company_status")
            if deal_status == "agreement":
                if deal_date > last_year:
                    deal_value = STATUS_CUSTOMER
                else:
                    deal_value = STATUS_INACTIVE
            elif customer_status == "irrelevant":
                deal_value = STATUS_IRRELEVANT
            else:
                deal_value = STATUS_PROSPECT
            print(customer, customer_id, deal_id,
                  deal_status, deal_date, deal_value)
            collected_data[customer].append(deal_value)
    for comp in collected_data:
        print("Customer", comp, "Deals", collected_data[comp], "Status", set_customer_status(
            collected_data[comp]))
        return_data.append(
            {"Customer": comp, "Status": set_customer_status(collected_data[comp])})
    return return_data


@ app.route('/customer_status')
def customer_status():
    deal_api = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
    deal_params = "?_limit=50&_embed=company"
    deal_url = deal_api + deal_params

    # company_api = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/company/"
    # company_params = "?_limit=50"
    # company_url = company_api + company_params

    response_deals = get_api_data(headers=headers, url=deal_url)
    # response_company = get_api_data(headers=headers, url=company_url)

    if len(response_deals) > 0:
        deals = filter_deals(response_deals)
        # customer_info = filter_customers(response_company)
        customers_status = get_customer_status(
            deals)
        return render_template('customer_status.html', customers=customers_status)
    else:
        msg = 'No deals found'
        return render_template('customer_status.html', msg=msg)

# You can add more pages to your app, like this:
#
# @app.route('/myroute')
# def myroute():
# 	mydata = [{'name': 'apple'}, {'name': 'mango'}, {'name': 'banana'}]
# 	return render_template('mytemplate.html', items=mydata)
#
# You also have to create the mytemplate.html page inside the 'templates'-folder to be rendered
# And then add a link to your page in the _navbar.html-file, located in templates/includes/


# DEBUGGING
# If you want to debug your app, one of the ways you can do that is to use:
# import pdb; pdb.set_trace()
# Add that line of code anywhere, and it will act as a breakpoint and halt your application


if __name__ == '__main__':
    app.secret_key = 'somethingsecret'
    app.run(debug=True)
