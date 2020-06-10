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
        try:
            deal = {
                "closing_date": parse(entry.get("closeddate")),
                "value": entry.get("value"),
                "status": entry.get("dealstatus").get("key"),
                "id": entry.get("_id"),
                "description": entry.get("_descriptive")
            }
            if (entry.get("_embedded") is not None):
                deal["Customer"] = entry.get("_embedded").get(
                    "relation_company").get("name")
                deal["Customer-id"] = entry.get("_embedded").get(
                    "relation_company").get("_id")
                deal["company_status"] = entry.get("_embedded").get(
                    "relation_company").get("buyingstatus").get("key")
            deals.append(deal)
        except TypeError:
            print("No date available")
        except:
            print("Something went wrong")
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
        print("WOHOOOO", deal.get("closing_date"))
        year = deal.get("closing_date").year
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
        collected_data[year] = round((total / count))
        return_data.append(
            {"label": year, "data": collected_data[year],  "year": year, "avg_value": collected_data[year], "total_deals": count})
    return return_data


def get_graph_labels(data):
    return_data = []
    for entry in data:
        return_data.append(entry.get("label"))
    return return_data


def get_graph_data(data):
    return_data = []
    for entry in data:
        return_data.append(entry.get("data"))
    return return_data


def get_total_deals(data):
    return_data = []
    for entry in data:
        return_data.append(entry.get("total_deals"))
    return return_data


def get_background_color(colors):
    if colors <= 0:
        return []
    delta = 360/colors
    hue = delta/2
    background_color = []
    for x in range(colors):
        background_color.append("hsla("+str(int(hue))+", 69%, 58%, 0.3)")
        hue += delta
    return background_color


def get_graph_colors(colors):
    if colors <= 0:
        return []
    delta = 360/colors
    hue = delta/2
    background_color = []
    border_color = []
    for x in range(colors):
        background_color.append("hsla("+str(int(hue))+", 69%, 58%, 0.3)")
        border_color.append("hsla("+str(int(hue))+", 69%, 58%, 1)")
        hue += delta
    return [background_color, border_color]


@app.route('/average_year')
def average_year():

    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
    params = "?_limit=50&_embed=company"
    url = base_url + params
    response_deals = get_api_data(headers=headers, url=url)

    if len(response_deals) > 0:
        data = filter_deals(response_deals)
        average_per_year = get_average_per_year(data)
        graph_labels = get_graph_labels(average_per_year)
        graph_data = get_graph_data(average_per_year)
        graph_total_deals = get_total_deals(average_per_year)
        graph_colors = get_graph_colors(len(graph_labels))
        return render_template('average_year.html', deals=average_per_year, labels=graph_labels, data=graph_data, totalDeals=graph_total_deals, backgroundColor=graph_colors[0], borderColor=graph_colors[1])
    else:
        msg = 'No deals found'
        return render_template('average_year.html', msg=msg)


def get_average_per_month(data, year):
    collected_data = collections.defaultdict(list)
    return_data = []
    for deal in data:
        deal_year = deal.get("closing_date").year
        status = deal.get("status")
        if deal_year == year and status == "agreement":
            month = deal.get("closing_date").month
            collected_data[month].append(1)
    for month in collected_data:
        count = 0
        for value in collected_data[month]:
            count += 1
        collected_data[month] = count
        return_data.append(
            {"label": calendar.month_name[month], "data": collected_data[month], "month": month, "name": calendar.month_name[month], "total_deals": collected_data[month]})
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
        graph_labels = get_graph_labels(average_per_month)
        graph_data = get_graph_data(average_per_month)
        graph_colors = get_graph_colors(len(graph_labels))
        return render_template('average_month.html', deals=average_per_month, display_year=year, labels=graph_labels, data=graph_data, backgroundColor=graph_colors[0], borderColor=graph_colors[1])
    else:
        msg = 'No deals found'
        return render_template('average_month.html', msg=msg)


def get_customer_value(data, year):
    collected_data = collections.defaultdict(list)
    return_data = []
    for deal in data:
        customer = deal.get("Customer")
        if customer is not None:
            deal_year = deal.get("closing_date").year
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
            {"label": cust, "data": collected_data[cust], "Customer": cust, "Value": collected_data[cust], "total_deals": count})

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
        graph_labels = get_graph_labels(customers)
        graph_data = get_graph_data(customers)
        graph_colors = get_graph_colors(len(graph_labels))
        return render_template('customer_value.html', customers=customers, display_year=year, labels=graph_labels, data=graph_data, backgroundColor=graph_colors[0], borderColor=graph_colors[1])
    else:
        msg = 'No deals found'
        return render_template('average_month.html', msg=msg)


def filter_customer_data(data):
    return {
        "name": data.get("name") if data.get("name") else "N/A",
        "phone": data.get("phone") if data.get("phone") else "N/A",
        "www": data.get("www") if data.get("www") else "N/A",
        "postaladdress1": data.get("postaladdress1") if data.get("postaladdress1") else "N/A",
        "postalzipcode": data.get("postalzipcode") if data.get("postalzipcode") else "N/A",
        "postalcity": data.get("postalcity") if data.get("postalcity") else "N/A",
        "country": data.get("country") if data.get("country") else "N/A",
    }


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
    customer_deals = collections.defaultdict(
        lambda: collections.defaultdict(list))
    return_data = []
    last_year = subtract_years(datetime.datetime.now(datetime.timezone.utc), 1)
    for data in deals:
        cust_id = data.get("Customer-id")
        if cust_id is not None:
            cust_name = data.get("Customer")
            deal_status = data.get("status")
            deal_date = data.get("closing_date")
            deal_value = data.get("value")
            customer_deals[cust_id]["value"].append(deal_value)
            customer_deals[cust_id]["date"].append(deal_date)
            customer_deals[cust_id]["customer_name"].append(cust_name)
            customer_status = data.get("company_status")
            if deal_status == "agreement":
                if deal_date > last_year:
                    deal_status_value = STATUS_CUSTOMER
                else:
                    deal_status_value = STATUS_INACTIVE
            elif customer_status == "irrelevant":
                deal_status_value = STATUS_IRRELEVANT
            else:
                deal_status_value = STATUS_PROSPECT
            collected_data[cust_id].append(deal_status_value)

    for company in collected_data:
        total_value = sum(customer_deals[company]["value"])
        latest_deal = sorted(customer_deals[company]["date"], reverse=True)[0]
        status = set_customer_status(collected_data[company])
        name = customer_deals[company]["customer_name"][0]
        return_data.append(
            {"id": company, "customer_name": name, "customer_status": status, "total_value": total_value, "latest_deal": latest_deal.strftime("%Y/%m/%d")})

    return return_data


@ app.route('/customer_status')
def customer_status():
    deal_api = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
    deal_params = "?_limit=50&_embed=company"
    deal_url = deal_api + deal_params

    response_deals = get_api_data(headers=headers, url=deal_url)

    if len(response_deals) > 0:
        deals = filter_deals(response_deals)
        customers_status = get_customer_status(
            deals)
        return render_template('customer_status.html', customers=customers_status)
    else:
        msg = 'No deals found'
        return render_template('customer_status.html', msg=msg)


def format_deals(deals):
    return_data = []
    return ""


@ app.route('/customer/<id>')
def customer_info(id):
    base_url = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/company/"
    params = id+"/"
    url = base_url + params
    response = api_request.get(
        url=url, headers=headers, data=None, verify=False)

    response_customer = json.loads(response.text)
    print(response_customer)

    url += "deal/"
    response_deals = get_api_data(headers=headers, url=url)
    print(response_deals)

    if len(response_customer) > 0:
        customer_info = filter_customer_data(response_customer)
        deal_info = filter_deals(response_deals)
        deals_formatted = format_deals(deal_info)
        print("DEAL INFO: ", deal_info)
        return render_template('customer_info.html', customer=customer_info, deals=deal_info, total_value=10, total_orders=len(deal_info))
    else:
        msg = 'No deals found'
        return render_template('customer_info.html', msg=msg)

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
